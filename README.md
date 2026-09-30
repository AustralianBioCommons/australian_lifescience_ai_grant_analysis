# Analysis of Australian AI and molecular life-science funding from NHMRC, MRFF and ARC grants


This package contains the complete reproducible analysis used to classify ARC, NHMRC and MRFF grants and analyses how Australian AI and molecular life-science have been funding in the past decade or so.

## Getting Started

Install into a virtual environment with:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then run the analysis
```
python src/analyse_grants.py  \
   --arc inputs/ARC_Grants_2015_2026_merged.csv  \
   --nhmrc inputs/NHMRC_Grants_2013_2025_merged.csv \
   --mrff inputs/medical-research-future-fund-mrff-grant-recipients.xlsx \
   --outdir outputs
```

The graph, summary data and classification of grants will appear under the new directory `./outputs`

# Methodology

## Data

Grant records were obtained from the official published datasets of the **[Australian Research Council (ARC)](https://www.arc.gov.au/funding-research/funding-outcomes/grants-dataset)**, **[National Health and Medical Research Council (NHMRC)](https://www.nhmrc.gov.au/funding/data-research/outcomes-funding-rounds)** and **[Medical Research Future Fund (MRFF)](https://www.health.gov.au/resources/publications/medical-research-future-fund-mrff-grant-recipients)**. The source collections cover ARC grants from 2015–2026, NHMRC grants from 2013–2025 and MRFF grants from 2017–2026; the current analysis uses grants from **2022–2025**. Published funding values are retained as nominal award values: ARC announced funding amount, NHMRC total amount awarded and MRFF total grant value.

The source files were first consolidated within each funder.

* **ARC** was supplied as 15 CSV partitions with the same schema; these were concatenated row-wise after checking that the headers matched and that no exact duplicate rows or duplicate grant codes were introduced. 
* **NHMRC** was supplied as 13 annual workbooks with substantial schema changes over time. Equivalent fields such as application ID, title, description, research keywords, FoR, scheme, institution and total award were mapped to a common set of columns and then concatenated. Eight aggregate or supplementary rows were retained in the merged file but marked as excluded from analysis, while repeated application IDs representing later fellowship extensions were retained as separate award records.
* **MRFF** is already distributed as a single grant-recipient workbook, so it is read directly after removing non-grant note/footer rows.

 The resulting ARC and NHMRC merged files, together with the MRFF workbook, are then normalised and combined by `grants.py` for classification and aggregation.

## Harmonisation

The three funder datasets were converted to a common grant-level schema in `grants.py`. Source-specific fields were mapped onto common columns such as `title`, `summary`, `keywords`, `for_text`, `broad_area`, `award_value` and `analysis_year`. Records not representing ordinary grants were excluded where this was identified in the source data, while the original grant identifiers and source-specific metadata required for tracing records were retained.

The main funder-specific mappings are:

- **ARC:** the grant summary supplies the project text, primary FoR supplies the research classification, and funding commencement year is used as the analysis year.
- **NHMRC:** title, description, research keywords, FoR and broad research area are combined from the harmonised annual NHMRC files; the published source/funding-round year is used as the analysis year. The annual files have changed structure over time, so these common fields are constructed from the corresponding columns in each schema. :chatgpt-content-reference{index="2"}
- **MRFF:** project name and project summary supply the text, FoR and broad research area supply the research classification, and contract start year is used as the analysis year.

## Classification

Classification is implemented in `grants.py`, with the term sets defined separately in `search_terms.py`. Each grant receives two independent Boolean labels: `ai` and `molecular_life_science`. The combined `ai_mls` label is true when both classifications are true. Text is normalised before matching so that differences in case and punctuation do not affect classification.

### Fields of Research

FoR information is treated as a separate classification signal from the project text. Molecular life-science FoR terms include areas such as genetics, genomics, biochemistry, microbiology, molecular biology, cell biology and related biological disciplines. AI-related FoR terms include areas such as artificial intelligence, machine learning, computer vision and natural language processing. FoR matching is performed against the harmonised `for_text` field, with `broad_area` also available for molecular life-science classification. :chatgpt-content-reference{index="3"}

### Title, keywords and description

The available free-text fields are combined for lexical classification. For **NHMRC**, this includes the grant title, description and research keywords. For **MRFF**, it includes project title and project summary. For **ARC**, the grant summary provides the main project text because the source export does not provide an equivalent keyword field and the title is derived from the beginning of the summary.

AI classification searches these fields for explicit AI/ML terminology and named methods, including terms such as artificial intelligence, machine learning, deep learning, neural networks, computer vision, random forests and related methods. Molecular life-science classification searches for molecular and biological terminology including genomics, genetics, transcriptomics, proteomics, DNA/RNA, sequencing, proteins, biomarkers, microbiology and related terms. A small number of explicit ambiguity rules are retained in the code, for example to avoid interpreting a biological use of *neural network* as evidence of AI. The same rule sets are applied to all three funders; differences between funders arise only from the source fields available for each record. :chatgpt-content-reference{index="4"}

## Aggregation

`analyse_grants.py` combines the classified grant records by funder and year. For each group it calculates the number of molecular life-science grants, the number also classified as AI, the corresponding proportion, and the summed nominal award value of AI + molecular life-science grants. The same calculations are also performed after pooling funders and across the full 2022–2025 period. These aggregated values form the summary CSV and the plotted annual proportions.
