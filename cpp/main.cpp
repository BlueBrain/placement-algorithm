#include "contrib/rapidxml.hpp"
#include "contrib/rapidxml_utils.hpp"

#include <boost/algorithm/string.hpp>
#include <boost/filesystem.hpp>
#include <boost/format.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/program_options.hpp>

#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>


namespace po = boost::program_options;

typedef rapidxml::xml_node<> XmlNode;
typedef rapidxml::xml_attribute<> XmlAttr;

typedef std::pair<std::string, float> YRelative;
typedef std::unordered_map<std::string, std::pair<float, float>> LayerProfile;


float getAbsoluteY(const YRelative& yRel, const LayerProfile& yLayers)
{
    const auto& layer = yLayers.at(yRel.first);
    const auto fraction = yRel.second;
    return (1.0 - fraction) * layer.first + fraction * layer.second;
}

struct Candidate
{
    std::string morph;
    std::string id;
    float y;
    LayerProfile yLayers;
};


struct AnnotationRule
{
    std::string rule;
    float yMin;
    float yMax;
};

typedef std::vector<AnnotationRule> AnnotationRules;


class PlacementRule
{
public:
    virtual ~PlacementRule() {}

    virtual float apply(const Candidate&, const AnnotationRule&) const = 0;
    virtual bool strict() const = 0;
};

typedef std::unordered_map<std::string, std::unique_ptr<PlacementRule>> PlacementRules;


class YBelowRule: public PlacementRule
{
public:
    YBelowRule(const YRelative& yRel)
        : yRel_(yRel)
    {}

    virtual float apply(const Candidate& candidate, const AnnotationRule& annotation) const override
    {
        const float yLimit = getAbsoluteY(yRel_, candidate.yLayers);
        const float delta = (candidate.y + annotation.yMax) - yLimit;
        if (delta < 0) {
            return 1.0;
        } else
        if (delta > TOLERANCE) {
            return 0.0;
        } else {
            return 1.0 - delta / TOLERANCE;
        }
    }

    virtual bool strict() const override
    {
        return true;
    }

private:
    const YRelative yRel_;

    static const float TOLERANCE;
};


const float YBelowRule::TOLERANCE = 30.0f;


class YRangeOverlapRule: public PlacementRule
{
public:
    YRangeOverlapRule(const YRelative& yMinRel, const YRelative& yMaxRel)
        : yMinRel_(yMinRel)
        , yMaxRel_(yMaxRel)
    {}

    virtual float apply(const Candidate& candidate, const AnnotationRule& annotation) const override
    {
        const float y1 = getAbsoluteY(yMinRel_, candidate.yLayers);
        const float y2 = getAbsoluteY(yMaxRel_, candidate.yLayers);
        const float y1c = candidate.y + annotation.yMin;
        const float y2c = candidate.y + annotation.yMax;
        const float y1o = std::max(y1, y1c);
        const float y2o = std::min(y2, y2c);
        if (y1o > y2o) {
            return 0.0;
        } else {
            return (y2o - y1o) / std::min(y2 - y1, y2c - y1c);
        }
    }

    virtual bool strict() const override
    {
        return false;
    }

private:
    const YRelative yMinRel_;
    const YRelative yMaxRel_;
};


XmlNode* getFirstNode(const XmlNode* elem, const std::string& name)
{
    const auto node = elem->first_node(name.c_str());
    if (!node) {
        throw std::runtime_error((boost::format("<%1%> element not found") % name).str());
    }
    return node;
}


template <typename T>
T getAttrValue(const XmlNode* elem, const std::string& name)
{
    const auto attr = elem->first_attribute(name.c_str());
    if (!attr) {
        throw std::runtime_error((boost::format("<%1%> element not found") % name).str());
    }
    return boost::lexical_cast<T>(attr->value());
}


PlacementRules parsePlacementRules(const std::string& filename)
{
    rapidxml::file<> xmlFile(filename.c_str());
    rapidxml::xml_document<> doc;
    doc.parse<0>(xmlFile.data());

    const auto rootNode = getFirstNode(&doc, "placement_rules");

    PlacementRules result;

    auto ruleSetNode = rootNode->first_node();
    while (ruleSetNode) {
        auto node = getFirstNode(ruleSetNode, "rule");
        while (node) {
            const auto type = getAttrValue<std::string>(node, "type");
            std::unique_ptr<PlacementRule> rule;
            if (type == "below") {
                rule.reset(new YBelowRule({
                    getAttrValue<std::string>(node, "y_layer"),
                    getAttrValue<float>(node, "y_fraction")
                }));
            } else
            if (type == "region_target") {
                rule.reset(new YRangeOverlapRule({
                    getAttrValue<std::string>(node, "y_min_layer"),
                    getAttrValue<float>(node, "y_min_fraction")
                }, {
                    getAttrValue<std::string>(node, "y_max_layer"),
                    getAttrValue<float>(node, "y_max_fraction")
                }));
            } else {
                std::cerr << "Unknown rule type: " << type << std::endl;
            }
            if (rule) {
                const auto id = getAttrValue<std::string>(node, "id");
                result.emplace(id, std::move(rule));
            }
            node = node->next_sibling("rule");
        }
        ruleSetNode = ruleSetNode->next_sibling();
    }

    return result;
}


AnnotationRules parseAnnotation(const std::string& filename, const PlacementRules& rules)
{
    rapidxml::file<> xmlFile(filename.c_str());
    rapidxml::xml_document<> doc;
    doc.parse<0>(xmlFile.data());

    const auto rootNode = getFirstNode(&doc, "annotations");

    AnnotationRules result;

    auto node = getFirstNode(rootNode, "placement");
    while (node) {
        const auto rule = getAttrValue<std::string>(node, "rule");
        if (rules.count(rule)) {
            result.push_back({
                rule,
                getAttrValue<float>(node, "y_min"),
                getAttrValue<float>(node, "y_max")
            });
        } else {
            //std::cerr << "Unknown rule: " << rule << std::endl;
        }
        node = node->next_sibling("placement");
    }

    return result;
}


bool getCandidate(std::istream& is, const std::vector<std::string>& layerNames, Candidate& candidate)
{
    is >> candidate.morph >> candidate.id >> candidate.y;
    for (const auto& layer: layerNames) {
        auto& ys = candidate.yLayers[layer];
        is >> ys.first >> ys.second;
    }
    return bool(is);
}


float aggregateOptionalScores(const std::vector<float>& scores)
{
    if (scores.empty()) {
        return 1.0;
    }
    return std::accumulate(scores.begin(), scores.end(), 0.0) / scores.size();
}


float aggregateStrictScores(const std::vector<float>& scores)
{
    if (scores.empty()) {
        return 1.0;
    }
    return *std::min_element(scores.begin(), scores.end());
}


float scoreCandidate(const Candidate& candidate, const AnnotationRules& annotations, const PlacementRules& rules)
{
    std::vector<float> strictScores;
    std::vector<float> optionalScores;
    for (const auto& item: annotations) {
        const auto rule = rules.find(item.rule);
        if (rule == rules.end()) {
            std::cerr << "Unknown rule: " << item.rule << std::endl;
            continue;
        }
        const float score = rule->second->apply(candidate, item);
        //std::cerr << candidate.id << ": score=" << score << " (" << item.rule << ")" << std::endl;
        if (rule->second->strict()) {
            strictScores.push_back(score);
        } else {
            optionalScores.push_back(score);
        }
    }

    const float strictScore = aggregateStrictScores(strictScores);
    const float optionalScore = aggregateOptionalScores(optionalScores);

    return strictScore * (1. + optionalScore) / 2.;
}


int main(int argc, char* argv[])
{
    po::options_description desc("Score placement candidates");
    desc.add_options()
        ("help", "Print help message")
        ("annotations,a", po::value<std::string>(), "Path to annotations folder")
        ("rules,r", po::value<std::string>(), "Path to placement rules file")
        ("layers,l", po::value<std::string>(), "Layer names as they appear in layer profile")
    ;

    po::variables_map vm;
    po::store(po::parse_command_line(argc, argv, desc), vm);
    po::notify(vm);

    if (vm.count("help")) {
        std::cout << desc << "\n";
        return 1;
    }

    if (vm.count("rules") < 1) {
        std::cerr << "Please specify --rules" << "\n";
        return 2;
    }
    const auto rules = parsePlacementRules(vm["rules"].as<std::string>());

    if (vm.count("annotations") < 1) {
        std::cerr << "Please specify --annotations" << "\n";
        return 2;
    }
    const auto annotationDir = vm["annotations"].as<std::string>();

    if (vm.count("layers") < 1) {
        std::cerr << "Please specify --layers" << "\n";
        return 2;
    }
    std::vector<std::string> layerNames;
    boost::split(layerNames, vm["layers"].as<std::string>(), boost::is_any_of(","));

    Candidate candidate;
    std::string currentMorph;
    boost::optional<AnnotationRules> annotations;

    std::cout << std::fixed << std::setprecision(3);
    while (getCandidate(std::cin, layerNames, candidate)) {
        if (candidate.morph != currentMorph) {
            const auto annotationPath = annotationDir + "/" + candidate.morph + ".xml";
            if (boost::filesystem::exists(annotationPath)) {
                annotations = parseAnnotation(annotationPath, rules);
            } else {
                std::cerr << "No annotation found for " << candidate.morph << ", skipping its candidates" << std::endl;
                annotations = boost::none;
            }
            currentMorph = candidate.morph;
        }
        if (annotations) {
            const auto score = scoreCandidate(candidate, *annotations, rules);
            std::cout << candidate.morph << " " << candidate.id << " " << score << std::endl;
        }
    }
}