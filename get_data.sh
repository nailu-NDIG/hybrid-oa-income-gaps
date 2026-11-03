#!/usr/bin/env bash
# Downloads the versioned public inputs into data/.
set -euo pipefail
cd "$(dirname "$0")/data"

HOADDATA_COMMIT=24391d48dc274292d810a4389b09ff9abf19ef8d
JCT_DATA_COMMIT=8f5caa751b88f9a06983f48e0db9e3676cb43642

[ -d hoaddata ] || git clone https://github.com/subugoe/hoaddata.git
git -C hoaddata checkout -q "$HOADDATA_COMMIT"

[ -d jct_data ] || git clone https://github.com/njahn82/jct_data.git
git -C jct_data checkout -q "$JCT_DATA_COMMIT"

curl -sL -o gdp.zip "https://api.worldbank.org/v2/en/indicator/NY.GDP.PCAP.CD?downloadformat=csv"
unzip -oq gdp.zip "API_NY.GDP.PCAP.CD_DS2_*.csv" && rm gdp.zip

# updated annually; the analysis uses columns FY21-FY26
curl -sL -o OGHIST.xlsx "https://ddh-openapi.worldbank.org/resources/DR0095333/download"

echo "Manual downloads still required: see README (SCImago, ScholCommLab, OpenAlex extraction)."
