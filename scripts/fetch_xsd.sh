#!/bin/bash
# Fetch the two ISO 20022 schemas the benchmark validates against. They are
# published by ISO 20022 and mirrored in several public repositories; they are
# not redistributed here.
set -e
mkdir -p "$(dirname "$0")/../xsd"; cd "$(dirname "$0")/../xsd"
curl -sfL -o pain.001.001.09.xsd https://raw.githubusercontent.com/fortesp/xsd2xml/master/tests/resources/pain.001.001.09.xsd
curl -sfL -o pacs.008.001.08.xsd https://raw.githubusercontent.com/prog-nov/iso20022-messages-for-go/main/XSD/pacs.008.001.08.xsd
grep -q 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.09' pain.001.001.09.xsd
grep -q 'urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08' pacs.008.001.08.xsd
echo "schemas in $(pwd)"
