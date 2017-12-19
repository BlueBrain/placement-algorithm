#include "lib.hpp"

#include <boost/algorithm/string.hpp>
#include <boost/filesystem.hpp>
#include <boost/optional.hpp>
#include <boost/program_options.hpp>

#include <iomanip>
#include <iostream>
#include <memory>
#include <string>


namespace po = boost::program_options;


int main(int argc, char* argv[])
{
    std::ios_base::sync_with_stdio(false);

    po::options_description desc("Score placement candidates");
    desc.add_options()
        ("help", "Print help message")
        ("annotations,a", po::value<std::string>(), "Path to annotations folder")
        ("rules,r", po::value<std::string>(), "Path to placement rules file")
        ("layers,l", po::value<std::string>(), "Layer names as they appear in layer profile")
        ("profile,p", po::value<std::string>(), "Layer thickness ratio to use for 'short' candidate form (total thickness only)")
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
    const PlacementRulesContext rules(vm["rules"].as<std::string>());

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

    std::unique_ptr<CandidateReader> candidateReader;
    if (vm.count("profile") > 0) {
        const auto layerRatio = parseLayerRatio(vm["profile"].as<std::string>(), layerNames);
        candidateReader.reset(new ShortCandidateReader(std::cin, layerRatio));
    } else {
        candidateReader.reset(new FullCandidateReader(std::cin, layerNames));
    }

    std::string currentMorph;
    std::string currentMtype;
    boost::optional<Annotations> annotations;
    BoundPlacementRules morphRules;

    std::cout << std::fixed << std::setprecision(3);
    while (candidateReader->fetchNext()) {
        const auto& candidate = candidateReader->get();
        if (candidate.morph != currentMorph) {
            const auto annotationPath = annotationDir + "/" + candidate.morph + ".xml";
            if (boost::filesystem::exists(annotationPath)) {
                annotations = loadAnnotations(annotationPath);
            } else {
                std::cerr << "No annotation found for " << candidate.morph << ", skipping its candidates" << std::endl;
                annotations = boost::none;
            }
            currentMorph = candidate.morph;
            currentMtype = "";
        }
        if (annotations) {
            if (candidate.mtype != currentMtype) {
                morphRules = rules.bind(*annotations, candidate.mtype);
                currentMtype = candidate.mtype;
            }
            const auto score = scoreCandidate(candidate, morphRules);
            std::cout << candidate.morph << " " << candidate.id << " " << score << std::endl;
        }
    }
}
