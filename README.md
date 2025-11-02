# Protocol Wizard (Step-by-step, HIL-first)

This tiny kit helps you go from a plain‑text topic description to a **frozen SLR protocol**:
research questions, keywords, inclusion/exclusion, and **provider‑native query candidates**.
It uses an LLM if available, with an offline fallback so the workflow always runs.

## 0) Setup
```bash
python -m pip install typer
# Optional for LLM:
# pip install openai google-generativeai
# export OPENAI_API_KEY=...
# export GOOGLE_API_KEY=...
```

## 1) Start from your subject text
Edit `subject.example.txt` or create your own, e.g. `subject.txt`.

## 2) Draft the protocol (LLM proposes, you review)
```bash
python protocol_wizard.py draft --subject-file subject.example.txt --outdir outputs
```
Outputs:
- `outputs/protocol_draft.json` — RQs, PICOS, keywords, screening, sources
- `outputs/checklist.md` — a short checklist for manual review

## 3) Refine the criteria (make bullets testable)
```bash
python protocol_wizard.py refine --protocol-draft outputs/protocol_draft.json --outdir outputs
```
Outputs:
- `outputs/refinements.json` — stricter bullets + borderline examples

## 4) Generate **provider-native** query candidates (ready for `slr fetch`)
```bash
python protocol_wizard.py queries --protocol-json outputs/protocol_draft.json --out-path outputs/queries_draft.jsonl
```
Outputs:
- `outputs/queries_draft.jsonl` — JSONL (each line is provider + native params)

## 5) Freeze the protocol (idempotent baseline for PRISMA)
```bash
python protocol_wizard.py freeze --protocol-json outputs/protocol_draft.json --refinements-json outputs/refinements.json --outdir frozen
```
Outputs:
- `frozen/protocol.json` — canonical protocol for the run
- `frozen/manifest.json` — includes SHA256 you can cite in Methods/PRISMA

> Next: feed `outputs/queries_draft.jsonl` to your `slr fetch` stage.
> Use `frozen/protocol.json` as the basis for screening configs and reporting.

## Notes
- If no API keys are configured, the wizard returns a **deterministic heuristic** draft so you can iterate manually.
- Keep human‑in‑the‑loop: edit `outputs/*.json` after each step as needed.
- You can re‑run steps; outputs are just files, not a database.
