# Evaluation Playbook for Protocol Wizard

This document captures two parts:
- Five example themes/domains for evaluating the pipeline academically.
- A practical guide for how to execute, measure, and evaluate runs.

## Part 1 — Evaluation Themes (Academic Examples)

### 1) Biomedical Imaging — Robustness Across Devices
- Focus: Deep learning detection of diabetic retinopathy across camera vendors and clinical settings.
- RQs: Does model accuracy degrade across devices and populations? Which mitigation methods reduce drift?
- Scope: Adults with fundus images; ML/DL classification; outcomes: sensitivity/specificity/AUC; clinical vs screening camps.
- Sources: PubMed, Crossref, OpenAlex, arXiv; use MeSH ("Diabetic Retinopathy/diagnosis") + lay synonyms.
- Stressors: MeSH vs free‑text synonyms, device keywords (Topcon, Zeiss), clinical vs community setting tags.
- Evaluation: Retrieval coverage vs seed set; title/abstract screening precision@k; κ agreement; time‑to‑draft; reproducibility (manifest hash); query diversity across providers.

### 2) Education — Spaced vs Massed Practice
- Focus: Effect of spaced repetition vs massed practice on long‑term retention in higher education.
- RQs: What is the effect size of spacing on delayed tests? Which moderators (discipline, interval length) matter?
- Scope: Undergraduate/graduate learners; interventions: spaced/massed; outcomes: delayed test performance; randomized or quasi‑experimental.
- Sources: ERIC, Crossref, PsycINFO (via Crossref proxies), OpenAlex.
- Stressors: Terminology variance ("distributed practice", "spaced learning", "lag effect"); study design filters; non‑randomized designs.
- Evaluation: Coverage vs curated meta‑analyses; inclusion/exclusion clarity; effect‑size extraction feasibility; κ agreement; hours saved vs manual.

### 3) Urban Climate — Heat Island Mitigation
- Focus: Effectiveness of urban heat mitigation (cool roofs, urban trees, reflective pavements) on near‑surface air temperature.
- RQs: Which interventions yield the largest temperature reductions? How do effects vary by climate zone and urban morphology?
- Scope: Urban populations; interventions: trees, albedo changes; outcomes: Δ air/LST temperature; observational/experimental/simulation with validation.
- Sources: Web of Science (via Crossref/OpenAlex), arXiv (atmospheric), PubMed (heat health overlap).
- Stressors: Remote sensing vs in‑situ measures, unit heterogeneity (°C vs K), simulation‑only exclusions.
- Evaluation: Query recall for GIS/RS terms; normalization success (units/metrics); dedup across RS + urban planning venues; κ on exclusions; freeze reproducibility.

### 4) Software Engineering — Code Review Automation
- Focus: Impact of automated review tools (static analyzers, linters, bots) on defect density and review latency.
- RQs: Do automated checks reduce post‑merge defects? Do they shorten time‑to‑approval?
- Scope: OSS/commercial projects; interventions: code review bots/static analysis; outcomes: defect metrics, PR latency; quasi‑experimental/observational.
- Sources: ACM DL/IEEE Xplore (via Crossref/OpenAlex), arXiv (SE), Zenodo (dataset papers).
- Stressors: Gray literature vs peer‑review; venue indexing variability; terminology drift ("linting", "code smells", "quality gates").
- Evaluation: Coverage vs known SE datasets; screening precision; extraction of standardized outcomes; cross‑database dedup; time‑to‑protocol; PRISMA manifest usage.

### 5) Public Health — School Mask Policies
- Focus: Effectiveness of school mask mandates on respiratory illness transmission (e.g., influenza, SARS‑CoV‑2).
- RQs: What is the relative risk reduction associated with masking policies? How do effects vary by community incidence?
- Scope: K‑12 schools; policy interventions; outcomes: incidence/attack rates; observational/quasi‑experimental.
- Sources: PubMed, Crossref, medRxiv/SSRN (policy), OpenAlex.
- Stressors: Policy terminology ("mandate", "requirement"), preprint vs peer‑review separation, confounding adjustments.
- Evaluation: Recall vs public health evidence maps; precision under policy synonyms; κ on modeling‑only exclusions; effect‑size extraction rate (RR/OR); freeze reproducibility and audit trail utility.

---

## Part 2 — How To Execute, Measure, and Evaluate

### Setup
- Start API: `uvicorn server.main:app --reload --port 8000`
- Read workflow: `docs/next-pipeline.md`, `docs/backend.md`
- Create a run folder per theme: `eval_runs/<theme>/<date>/`

### Execute Per Theme
- Draft: `POST /draft` with `{ "subject_text": "..." }` → save `protocol_draft.json`, `checklist.md`
- Refine: `POST /refine` with `protocol` → save `refinements.json`
- Queries: `POST /queries` with `protocol` → save `queries_draft.jsonl`
- Freeze: `POST /freeze` with `protocol` + `refinements` → save `frozen/protocol.json`, `frozen/manifest.json`
- Fetch (external step): run harvest scripts with `queries_draft.jsonl` → save `corpus_raw.jsonl`

### Instrumentation
- Log times per stage (start/end/duration) into `eval_runs/<theme>/run_log.csv`.
- At each stage, write a small `manifest.json` with:
  - inputs (file hashes), outputs (file hashes), counts (n_records), params (model, provider keys)
- Keep a curated “seed set” per theme to measure recall: `seeds/<theme>.json` (list of DOIs/IDs).

### Metrics To Collect
- Retrieval coverage (recall)
  - Seed recall = retrieved_seeds / total_seeds (compare DOIs/PMIDs in `corpus_raw.jsonl` vs `seeds/*.json`).
- Screening precision@k (title/abstract)
  - Sample K records from `corpus_candidates.jsonl`, manually label include/exclude; precision = true_includes / K.
- Inter‑rater agreement (screening)
  - Two reviewers label same sample → Cohen’s κ: `from sklearn.metrics import cohen_kappa_score`.
- Deduplication quality
  - Duplicate rate = (# merged pairs) / (# raw records); spot‑check clusters for false merges/missed dups.
- Query diversity and overlap
  - Per provider yield, unique hits, Jaccard overlap across providers/families.
- Extraction reliability (if extracting)
  - Numeric fields: ICC/Pearson between two extractors; categorical: κ; success rate = rows_extracted / included_fulltext.
- Risk of bias agreement (if applicable)
  - Domain‑level weighted κ or percent agreement.
- Reproducibility
  - Freeze twice → hashes equal; edit protocol → hash changes; cite SHA in Methods.
- Time and cost
  - Human time per stage (from `run_log.csv`); API usage (LLM tokens, query counts), estimate $ if needed.

### Quick Commands
- Draft:
  ```bash
  curl -sX POST localhost:8000/draft -H "Content-Type: application/json" \
    -d '{"subject_text":"..."}' > protocol_draft.json
  ```
- Refine:
  ```bash
  jq -n --argfile p protocol_draft.json '{protocol:$p}' | \
  curl -sX POST localhost:8000/refine -H "Content-Type: application/json" --data-binary @- | \
  jq .refinements > refinements.json
  ```
- Queries:
  ```bash
  jq -n --argfile p protocol_draft.json '{protocol:$p}' | \
  curl -sX POST localhost:8000/queries -H "Content-Type: application/json" --data-binary @- | \
  jq -r '.queries[]|@json' > queries_draft.jsonl
  ```
- Freeze:
  ```bash
  jq -n --argfile p protocol_draft.json --argfile r refinements.json '{protocol:$p,refinements:$r}' | \
  curl -sX POST localhost:8000/freeze -H "Content-Type: application/json" --data-binary @- > frozen.json
  ```

### Evaluation Folder Structure
```
eval_runs/
  <theme>/<date>/
    protocol_draft.json
    refinements.json
    queries_draft.jsonl
    corpus_raw.jsonl
    corpus_candidates.jsonl
    screened_abstract.jsonl
    screened_fulltext.jsonl
    extracted_data.jsonl
    risk_of_bias.jsonl
    meta_results.json
    frozen/manifest.json
    run_log.csv
    metrics.json
```

### Scoring Summary (per theme)
- Report: recall on seeds, precision@k, κ, dedup rate, extraction success, hash stability, total human hours, and brief notes on query/provider overlaps.

