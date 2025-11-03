# Next Pipeline After Protocol Freeze

This outlines a practical, reproducible pipeline to continue after producing:
- `outputs/protocol_draft.json`
- `outputs/refinements.json`
- `outputs/queries_draft.jsonl`
- `frozen/protocol.json` and `frozen/manifest.json`

## 1) Harvest Literature
- Use `queries_draft.jsonl` to fetch from OpenAlex, Crossref, PubMed, arXiv.
- Save per‑provider raw dumps and a merged `corpus_raw.jsonl`.
- Log provider, query family, timestamps, and query params for reproducibility.

## 2) Normalize + Enrich
- Map fields to a canonical schema (id, title, abstract, authors, year, venue, doi/pmid, urls).
- Enrich DOIs (Crossref/Unpaywall), normalize author names, parse affiliations.
- Optional: expand references/citations when available.

## 3) Deduplicate
- Deduplicate by DOI/PMID when present; fallback to title+year+first‑author with fuzzy matching.
- Emit `corpus_candidates.jsonl` with a stable `dedupe_key` and provenance (which sources matched).

## 4) Title/Abstract Screening
- Apply inclusion/exclusion from `frozen/protocol.json` as rules; capture reasons.
- Optional: ML‑assisted triage (e.g., ASReview‑style ranking) with manual validation.
- Output: `screened_abstract.jsonl` with decision, criterion hit, screener(s), κ agreement.

## 5) Full‑Text Retrieval
- Resolve OA PDFs (Unpaywall); otherwise follow publisher links (respect robots/rate limits).
- Store PDFs with content hash; maintain `fulltext_inventory.jsonl` (pdf_path/hash/obtained_via).

## 6) Full‑Text Screening
- Second‑pass inclusion on full text; log definitive reasons and conflicts.
- Output: `screened_fulltext.jsonl` (final include/exclude + rationale).

## 7) Data Extraction
- Define an extraction schema (study design, population, interventions, comparators, outcomes, metrics, sample sizes).
- Two‑pass (extractor A/B) + arbitration; emit `extracted_data.jsonl`.
- Precompute effect sizes where possible (Hedges g, log OR, RR) with confidence intervals.

## 8) Quality Appraisal
- Apply domain tool (RoB 2, ROBINS‑I, QUADAS‑2, etc.).
- Output: `risk_of_bias.jsonl` linked by study id and domain‑level judgments.

## 9) Synthesis
- Quantitative: random/fixed effects meta‑analysis, heterogeneity (τ², I²), subgroup/moderator analyses, sensitivity tests.
- Qualitative: thematic synthesis / vote‑counting where meta‑analysis isn’t viable.
- Outputs: `meta_results.json`, forest/funnel plots, summary tables.

## 10) Reporting + Audit
- Auto‑compose PRISMA flow from stage counts; include `frozen/manifest.json` hash in Methods.
- Freeze the synthesis bundle (tables, plots, results) with a new manifest; archive on OSF/Zenodo.

## Checkpoints & Artifacts
- Inputs: `queries_draft.jsonl`, `frozen/protocol.json`
- Stage outputs: `corpus_raw.jsonl` → `corpus_candidates.jsonl` → `screened_abstract.jsonl` → `screened_fulltext.jsonl`
- Final outputs: `fulltext_inventory.jsonl`, `extracted_data.jsonl`, `risk_of_bias.jsonl`, `meta_results.json`, PRISMA diagram

## Automation Hints
- Use Make/CI targets per stage; make each step idempotent.
- Emit per‑stage manifests (counts + SHA‑256 of inputs/outputs) to keep the PRISMA trail trustworthy.
- Add schema checks for records, screening decisions, and extraction rows to catch drift early.

