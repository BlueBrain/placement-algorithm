#include "../lib.hpp"

#include "../contrib/catch.hpp"


TEST_CASE( "getAbsoluteY", "")
{
    const YRelative yRel {"L2", 0.25};
    const LayerProfile yLayers {
        {"L1", { 100, 200 }},
        {"L2", { 200, 300 }},
    };
    REQUIRE( getAbsoluteY(yRel, yLayers) == 225 );
}


TEST_CASE( "YBelowRule", "[rules]")
{
    const YBelowRule rule{"test", {"L1", 0.5}};
    const LayerProfile yLayers{
        {"L1", { 100, 200 }}
    };
    const Candidate candidate{
        "morph-A",
        "mtype-A",
        "a42",
        110.0,
        yLayers
    };

    CHECK( rule.strict() );

    {
        const Annotation annotation{"foo1", NAN, 39.0};
        CHECK( rule.apply(candidate, annotation) == Approx(1.0) );
    }

    {
        const Annotation annotation{"foo2", NAN, 55.0};
        CHECK( rule.apply(candidate, annotation) == Approx(0.5) );
    }

    {
        const Annotation annotation{"foo3", NAN, 71.0};
        CHECK( rule.apply(candidate, annotation) == Approx(0.0) );
    }
}


TEST_CASE( "YRegionTargetRule", "[rules]")
{
    const YRegionTargetRule rule{"test", {"L1", 0.0}, {"L1", 0.5}};
    const YRegionTargetRule ruleFill{"test", {"L1", 0.0}, {"L1", 0.5}, true};
    const LayerProfile yLayers{
        {"L1", { 20, 30 }}
    };
    const Candidate candidate{
        "morph-A",
        "mtype-A",
        "a42",
        20.0,
        yLayers
    };

    CHECK( !rule.strict() );

    {
        const Annotation annotation{"foo1", -4.0, -2.0};
        CHECK( rule.apply(candidate, annotation) == Approx(0.0) );
        CHECK( ruleFill.apply(candidate, annotation) == Approx(0.0) );
    }

    {
        const Annotation annotation{"foo2", -2.0, 2.0};
        CHECK( rule.apply(candidate, annotation) == Approx(0.5) );
        CHECK( ruleFill.apply(candidate, annotation) == Approx(0.4) );
    }

    {
        const Annotation annotation{"foo3", 2.0, 3.0};
        CHECK( rule.apply(candidate, annotation) == Approx(1.0) );
        CHECK( ruleFill.apply(candidate, annotation) == Approx(0.2) );
    }
}


TEST_CASE( "Aggregate strict score", "[score]" )
{
    CHECK( aggregateStrictScores({}) == Approx(1.0) );
    CHECK( aggregateStrictScores({0.4, 0.2, 0.1, 0.3}) == Approx(0.1) );
}


TEST_CASE( "Aggregate optional score", "[score]" )
{
    CHECK( aggregateOptionalScores({}) == Approx(1.0) );
    CHECK( aggregateOptionalScores({0.5, 1.0}) == Approx(0.66667) );
    CHECK( aggregateOptionalScores({0.5, 1.0, 0.0}) == Approx(0.0) );
    CHECK( aggregateOptionalScores({0.5, 1.0, 1e-6}) == Approx(0.0) );
}


template<typename T, typename P>
bool isPointerOfType(const P* value)
{
    return value && (typeid(*value) == typeid(T));
}


TEST_CASE( "Parse rules XML", "[xml]" )
{
    const auto rules = loadRules("../../tests/data/rules.xml");
    REQUIRE( rules.size() == 3 );
    {
        const auto& ruleSet = rules.at("*");
        REQUIRE( ruleSet.size() == 2 );
        CHECK( isPointerOfType<YBelowRule>(ruleSet.at("L1_hard_limit").get()) );
        CHECK( isPointerOfType<YBelowRule>(ruleSet.at("L1_axon_hard_limit").get()) );
    }
    {
        const auto& ruleSet = rules.at("L1_HAC");
        REQUIRE( ruleSet.size() == 2 );
        CHECK( isPointerOfType<YRegionTargetRule>(ruleSet.at("axon, Layer_1").get()) );
        CHECK( isPointerOfType<YRegionTargetRule>(ruleSet.at("axon, Layer_1, fill").get()) );
    }
    {
        const auto& ruleSet = rules.at("L1_SAC");
        REQUIRE( ruleSet.size() == 2 );
        CHECK( isPointerOfType<YRegionTargetRule>(ruleSet.at("axon, Layer_1").get()) );
        CHECK( isPointerOfType<YRegionTargetRule>(ruleSet.at("axon, Layer_1, fill").get()) );
    }
}


TEST_CASE( "Duplicate mtype rules", "[xml]" )
{
    REQUIRE_THROWS(loadRules("../../tests/data/rules_duplicate.xml"));
}


TEST_CASE( "Parse annotation XML", "[xml]" )
{
    const auto annotations = loadAnnotations("../../tests/data/C060106F.xml");
    REQUIRE( annotations.size() == 3 );
    {
        CHECK( annotations[0].ruleId == "axon, Layer_1" );
        CHECK( annotations[0].yMin == Approx(-70.0) );
        CHECK( annotations[0].yMax == Approx(46.0) );
    }
    {
        CHECK( annotations[1].ruleId == "L1_hard_limit" );
        CHECK( annotations[1].yMin == Approx(-223.907318) );
        CHECK( annotations[1].yMax == Approx(33.701271) );
    }
    {
        CHECK( annotations[2].ruleId == "L1_axon_hard_limit" );
        CHECK( annotations[2].yMin == Approx(-217.924652) );
        CHECK( annotations[2].yMax == Approx(38.849353) );
    }
}


TEST_CASE( "Parse empty annotation XML", "[xml]" )
{
    const auto annotations = loadAnnotations("../../tests/data/empty.xml");
    REQUIRE( annotations.empty() );
}