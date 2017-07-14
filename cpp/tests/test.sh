#!/bin/bash -eu

TEST_DATA_DIR=../../tests/data
OUTPUT=$(mktemp)

function cleanup {
    rm -f "$OUTPUT"
}

trap cleanup EXIT

../scorePlacement --rules "$TEST_DATA_DIR"/rules.xml --annotation "$TEST_DATA_DIR" --layers 1,2,3,4,5,6 \
        < "$TEST_DATA_DIR"/candidates.csv \
        > "$OUTPUT" \
        2>/dev/null

diff "$OUTPUT" "$TEST_DATA_DIR"/scores.csv
