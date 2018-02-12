#ifndef PLACEMENT_ALGORITHM_LIB_HPP
#define PLACEMENT_ALGORITHM_LIB_HPP

#include "contrib/rapidxml.hpp"
#include "contrib/rapidxml_utils.hpp"

#include <boost/format.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/optional.hpp>

#include <cmath>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>


typedef rapidxml::xml_node<> XmlNode;
typedef rapidxml::xml_attribute<> XmlAttr;

typedef std::pair<std::string, float> YRelative;
typedef std::unordered_map<std::string, std::pair<float, float>> LayerProfile;


const std::unordered_set<std::string> IGNORED_RULES {
    "ScaleBias"
};


float getAbsoluteY(const YRelative& yRel, const LayerProfile& yLayers)
{
    const auto& layer = yLayers.at(yRel.first);
    const auto fraction = yRel.second;
    return (1.0 - fraction) * layer.first + fraction * layer.second;
}

struct Candidate
{
    std::string morph;
    std::string mtype;
    std::string id;
    float y;
    LayerProfile yLayers;
};


struct Annotation
{
    std::string ruleId;
    float yMin;
    float yMax;
};

typedef std::vector<Annotation> Annotations;


class PlacementRule
{
public:
    PlacementRule(const std::string& id):
        id_(id)
    {}

    virtual ~PlacementRule() {}

    const std::string& id() const
    {
        return id_;
    }


    virtual float apply(const Candidate&, const Annotation&) const = 0;
    virtual bool strict() const = 0;

private:
    std::string id_;
};

typedef std::unordered_map<std::string, std::unique_ptr<PlacementRule>> PlacementRulesMap;

struct BoundPlacementRule
{
    const PlacementRule* rule;
    boost::optional<Annotation> annotation;
};

typedef std::vector<BoundPlacementRule> BoundPlacementRules;


class YBelowRule: public PlacementRule
{
public:
    YBelowRule(const std::string& id, const YRelative& yRel)
        : PlacementRule(id)
        , yRel_(yRel)
    {}

    virtual float apply(const Candidate& candidate, const Annotation& annotation) const override
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


class YRegionTargetRule: public PlacementRule
{
public:
    YRegionTargetRule(
        const std::string& id, const YRelative& yMinRel, const YRelative& yMaxRel, bool fill=false
    )
        : PlacementRule(id)
        , yMinRel_(yMinRel)
        , yMaxRel_(yMaxRel)
        , fill_(fill)
    {}

    virtual float apply(const Candidate& candidate, const Annotation& annotation) const override
    {
        const float y1 = getAbsoluteY(yMinRel_, candidate.yLayers);
        const float y2 = getAbsoluteY(yMaxRel_, candidate.yLayers);
        const float y1c = candidate.y + annotation.yMin;
        const float y2c = candidate.y + annotation.yMax;
        const float y1o = std::max(y1, y1c);
        const float y2o = std::min(y2, y2c);
        if (y1o > y2o) {
            return 0.0;
        } else
        if (fill_) {
            return (y2o - y1o) / std::max(y2 - y1, y2c - y1c);
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
    const bool fill_;
};


XmlNode* getFirstNode(const XmlNode* elem, const std::string& name, bool required=true)
{
    const auto node = elem->first_node(name.c_str());
    if (required && !node) {
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


PlacementRulesMap loadRuleSet(const XmlNode* groupNode)
{
    PlacementRulesMap result;

    auto node = getFirstNode(groupNode, "rule");
    while (node) {
        const auto id = getAttrValue<std::string>(node, "id");
        const auto type = getAttrValue<std::string>(node, "type");
        std::unique_ptr<PlacementRule> rule;
        if (type == "below") {
            rule.reset(new YBelowRule(
                id,
                {
                    getAttrValue<std::string>(node, "y_layer"),
                    getAttrValue<float>(node, "y_fraction")
                }
            ));
        } else
        if (type == "region_target" || type == "region_occupy") {
            const bool fill = (type == "region_occupy");
            rule.reset(new YRegionTargetRule(
                id,
                {
                    getAttrValue<std::string>(node, "y_min_layer"),
                    getAttrValue<float>(node, "y_min_fraction")
                },
                {
                    getAttrValue<std::string>(node, "y_max_layer"),
                    getAttrValue<float>(node, "y_max_fraction")
                },
                fill
            ));
        }
        else {
            std::cerr << "Unknown rule type: " << type << std::endl;
        }
        if (rule) {
            result.emplace(id, std::move(rule));
        }
        node = node->next_sibling("rule");
    }

    return result;
}


std::unordered_map<std::string, PlacementRulesMap> loadRules(const std::string& filename)
{
    rapidxml::file<> xmlFile(filename.c_str());
    rapidxml::xml_document<> doc;
    doc.parse<0>(xmlFile.data());

    const auto rootNode = getFirstNode(&doc, "placement_rules");

    std::unordered_map<std::string, PlacementRulesMap> result;

    auto node = getFirstNode(rootNode, "global_rule_set");
    while (node) {
        if (result.count("*")) {
            throw std::runtime_error("Duplicate <global_rule_set>");
        }
        result["*"] = loadRuleSet(node);
        node = node->next_sibling("global_rule_set");
    }

    node = getFirstNode(rootNode, "mtype_rule_set");
    while (node) {
        const auto mtype = getAttrValue<std::string>(node, "mtype");
        if (result.count(mtype)) {
            throw std::runtime_error("Duplicate <mtype_rule_set>");
        }
        result[mtype] = loadRuleSet(node);
        node = node->next_sibling("mtype_rule_set");
    }

    return result;
}




class PlacementRulesContext
{
public:
    PlacementRulesContext(const std::string& filePath);

    BoundPlacementRules bind(const Annotations& annotations, const std::string& mtype) const;

private:
    const PlacementRulesMap& getRuleSet(const std::string& mtype) const;

    const std::unordered_map<std::string, PlacementRulesMap> rules_;

    static const PlacementRulesMap EMPTY_RULES;
};

const PlacementRulesMap PlacementRulesContext::EMPTY_RULES;


PlacementRulesContext::PlacementRulesContext(const std::string& filePath):
    rules_(loadRules(filePath))
{
}


const PlacementRulesMap& PlacementRulesContext::getRuleSet(const std::string& mtype) const
{
    const auto it = rules_.find(mtype);
    return (it == rules_.end()) ? EMPTY_RULES : it->second;
}


BoundPlacementRules PlacementRulesContext::bind(const Annotations& annotations, const std::string& mtype) const
{
    const auto& commonRules = getRuleSet("*");
    const auto& mtypeRules = getRuleSet(mtype);

    BoundPlacementRules result;

    std::unordered_set<std::string> usedRules;
    for (const auto& annotation: annotations) {
        PlacementRule* rule = nullptr;

        const auto ruleId = annotation.ruleId;
        if (mtypeRules.count(ruleId)) {
            rule = mtypeRules.at(ruleId).get();
        } else
        if (commonRules.count(ruleId)) {
            rule = commonRules.at(ruleId).get();
        } else {
            std::cerr << "Unknown rule: " << ruleId << std::endl;
        }

        if (rule) {
            result.push_back({rule, annotation});
            usedRules.insert(ruleId);
        }
    }

    for (const auto& item: mtypeRules) {
        PlacementRule* rule = item.second.get();
        if (usedRules.find(rule->id()) == usedRules.end()) {
            std::cerr << "Missing rule annotation: " << rule->id() << std::endl;
            result.push_back({rule, boost::none});
        }
    }

    for (const auto& item: commonRules) {
        PlacementRule* rule = item.second.get();
        if (usedRules.find(rule->id()) == usedRules.end()) {
            std::cerr << "Missing rule annotation: " << rule->id() << std::endl;
            result.push_back({rule, boost::none});
        }
    }

    return result;
}


Annotations loadAnnotations(const std::string& filename)
{
    rapidxml::file<> xmlFile(filename.c_str());
    rapidxml::xml_document<> doc;
    doc.parse<0>(xmlFile.data());

    const auto rootNode = getFirstNode(&doc, "annotations");

    Annotations result;

    auto node = getFirstNode(rootNode, "placement", false);
    while (node) {
        const auto rule = getAttrValue<std::string>(node, "rule");
        if (!IGNORED_RULES.count(rule)) {
            result.push_back({
                rule,
                getAttrValue<float>(node, "y_min"),
                getAttrValue<float>(node, "y_max")
            });
        }
        node = node->next_sibling("placement");
    }

    return result;
}


LayerProfile parseLayerRatio(const std::string& value, const std::vector<std::string>& layerNames)
{
    LayerProfile result;

    std::stringstream ss(value);

    float y;
    float total = 0;
    for (const auto& layer: layerNames) {
        if (!(ss >> y)) {
            throw std::runtime_error("Invalid layer ratio profile");
        }
        result[layer] = std::make_pair(total, total + y);
        total += y;
        if (ss.peek() == ',') {
            ss.ignore();
        }
    }

    for (auto& item: result) {
        item.second.first /= total;
        item.second.second /= total;
    }

    return result;
}


float harmonicMean(const std::vector<float>& xs, float eps=1e-3)
{
    float sum = 0.0f;
    for (auto x: xs) {
        if (std::fabs(x) < eps) {
            return 0.0f;
        } else {
            sum += 1.0f / x;
        }
    }
    return xs.size() / sum;
}


float aggregateOptionalScores(const std::vector<float>& scores)
{
    if (scores.empty()) {
        return 1.0;
    }
    return harmonicMean(scores);
}


float aggregateStrictScores(const std::vector<float>& scores)
{
    if (scores.empty()) {
        return 1.0;
    }
    return *std::min_element(scores.begin(), scores.end());
}


float scoreCandidate(const Candidate& candidate, const BoundPlacementRules& morphRules)
{
    std::vector<float> strictScores;
    std::vector<float> optionalScores;

    for (const auto& morphRule: morphRules) {
        const PlacementRule& rule = *(morphRule.rule);
        float score;
        if (morphRule.annotation) {
            score = rule.apply(candidate, *morphRule.annotation);
        } else {
            continue;
        }
        //std::cerr << candidate.id << ": score=" << score << " (" << item.rule << ")" << std::endl;
        if (rule.strict()) {
            strictScores.push_back(score);
        } else {
            optionalScores.push_back(score);
        }
    }

    const float strictScore = aggregateStrictScores(strictScores);
    const float optionalScore = aggregateOptionalScores(optionalScores);

    return strictScore * optionalScore;
}


class CandidateReader
{
public:
    virtual ~CandidateReader() {};

    const Candidate& get() const
    {
        return candidate_;
    }

    virtual bool fetchNext() = 0;

protected:
    Candidate candidate_;
};


class FullCandidateReader: public CandidateReader
{
public:
    FullCandidateReader(std::istream& stream, const std::vector<std::string>& layerNames)
        : stream_(stream)
        , layerNames_(layerNames)
    {}

    virtual bool fetchNext() override
    {
        stream_ >> candidate_.morph >> candidate_.mtype >> candidate_.id >> candidate_.y;
        for (const auto& layer: layerNames_) {
            auto& ys = candidate_.yLayers[layer];
            stream_ >> ys.first >> ys.second;
        }
        return bool(stream_);
    }

private:
    std::istream& stream_;
    const std::vector<std::string> layerNames_;
};


class ShortCandidateReader: public CandidateReader
{
public:
    ShortCandidateReader(std::istream& stream, const LayerProfile& layerRatio)
        : stream_(stream)
        , layerRatio_(layerRatio)
    {
    }

    virtual bool fetchNext() override
    {
        float height;
        stream_ >> candidate_.morph >> candidate_.mtype >> candidate_.id >> candidate_.y >> height;
        candidate_.yLayers = layerRatio_;
        for (auto& item: candidate_.yLayers) {
            item.second.first *= height;
            item.second.second *= height;
        }
        return bool(stream_);
    }

private:
    std::istream& stream_;
    const LayerProfile layerRatio_;
};

#endif  // PLACEMENT_ALGORITHM_LIB_HPP
