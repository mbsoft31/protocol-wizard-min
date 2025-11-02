from __future__ import annotations
import os, json, hashlib, datetime, re, sys, typing as T
import typer
from pathlib import Path

app = typer.Typer(help="Protocol Wizard: draft → refine → freeze (HIL friendly)")

def sha256_text(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# --- Minimal LLM call shim (OpenAI or Gemini), with offline fallback ---
def call_llm(prompt: str, model: str = "openai:gpt-4o-mini") -> str:
    """
    Uses environment variables:
      OPENAI_API_KEY or GOOGLE_API_KEY
    model format:
      - 'openai:gpt-4o-mini' or 'openai:gpt-4.1-mini'
      - 'gemini:gemini-1.5-flash'
    If no keys found, returns a heuristic JSON draft.
    """
    try:
        vendor, name = model.split(":", 1)
    except ValueError:
        vendor, name = "openai", model

    # Offline heuristic fallback
    key_oa = os.getenv("OPENAI_API_KEY")
    key_g  = os.getenv("GOOGLE_API_KEY")

    if vendor == "openai" and key_oa:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key_oa)
            msg = client.chat.completions.create(
                model=name,
                messages=[{"role":"user","content":prompt}],
                temperature=0
            )
            return msg.choices[0].message.content
        except Exception as e:
            pass

    if vendor == "gemini" and key_g:
        try:
            import google.generativeai as genai
            genai.configure(api_key=key_g)
            model_g = genai.GenerativeModel(name)
            resp = model_g.generate_content(prompt)
            return resp.text
        except Exception as e:
            pass

    # Heuristic JSON fallback (very rough, ensures pipeline continuity)
    return json.dumps({
        "research_questions": ["How do deep models generalize from lab to field for plant disease detection?"],
        "picos": { "population": ["crop plants"], "intervention": ["deep learning detection"], "comparison": ["lab vs field"], "outcomes": ["accuracy drop"], "context": ["field conditions"] },
        "keywords": {
            "include": ["plant disease detection","domain shift","field images","lab-to-field","generalization"],
            "exclude": ["yield prediction","irrigation only"],
            "synonyms": {"domain shift": ["dataset shift","external validity"]}
        },
        "screening": {
            "inclusion_criteria": ["disease detection task","machine/deep learning method","includes field images or lab-to-field evaluation"],
            "exclusion_criteria": ["yield-only studies","pure irrigation optimization","simulation-only with no field data"],
            "years": [2015, 2025],
            "languages": ["en","fr","ar"],
            "doc_types": ["journal","conference","preprint"]
        },
        "sources": ["openalex","crossref","pubmed","arxiv"],
        "rationales": {"scope":"Focus on robustness and domain shift.","risks":"Non-English coverage might be thin; RS may drift scope."}
    }, ensure_ascii=False)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

@app.command("draft")
def draft(
    subject_file: str = typer.Option(..., help="Path to subject description .txt"),
    outdir: str = typer.Option("outputs", help="Directory to write drafts"),
    model: str = typer.Option("openai:gpt-4o-mini", help="Model spec (openai:..., gemini:...)")
):
    ensure_dir(Path(outdir))
    subject = Path(subject_file).read_text(encoding="utf-8")
    prompt = Path("prompts/01_extract_protocol.txt").read_text(encoding="utf-8").format(subject_text=subject)
    raw = call_llm(prompt, model=model)
    # Try parse
    try:
        obj = json.loads(raw)
    except Exception:
        typer.echo("[WARN] LLM returned non-JSON; using fallback heuristic.")
        obj = json.loads(call_llm("fallback", model="local"))
    Path(outdir, "protocol_draft.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    # Checklist for HIL
    checklist = f"""# HIL Checklist (Protocol Draft)

- [ ] Do research questions match the topic?
- [ ] Inclusion criteria testable? Any vague words to replace?
- [ ] Exclusion criteria complete? Add domain-specific negatives.
- [ ] Years/languages/doc types OK?
- [ ] Sources sufficient?
- [ ] Risks acknowledged?

Edit `outputs/protocol_draft.json` and re-run `refine`.
"""
    Path(outdir, "checklist.md").write_text(checklist, encoding="utf-8")
    typer.echo(f"[OK] Draft written -> {Path(outdir,'protocol_draft.json')}")

@app.command("refine")
def refine(
    protocol_draft: str = typer.Option("outputs/protocol_draft.json", help="Draft JSON to refine"),
    outdir: str = typer.Option("outputs", help="Directory for refinements"),
    model: str = typer.Option("openai:gpt-4o-mini", help="Model spec")
):
    ensure_dir(Path(outdir))
    proto = Path(protocol_draft).read_text(encoding="utf-8")
    prompt = Path("prompts/02_refine_criteria.txt").read_text(encoding="utf-8").format(protocol_json=proto)
    raw = call_llm(prompt, model=model)
    try:
        obj = json.loads(raw)
    except Exception:
        obj = {
            "inclusion_criteria_refined": ["ML vision for plant disease detection","has field images or lab-to-field eval"],
            "exclusion_criteria_refined": ["yield-only","irrigation-only","pure simulation"],
            "borderline_examples": [{"text":"Greenhouse + small field pilot","suggested":"MAYBE","why":"pilot may qualify"}],
            "risks_and_ambiguities": ["Remote sensing scope creep"]
        }
    Path(outdir, "refinements.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"[OK] Refinements written -> {Path(outdir,'refinements.json')}")

@app.command("queries")
def queries(
    protocol_json: str = typer.Option("outputs/protocol_draft.json", help="Protocol JSON"),
    out_path: str = typer.Option("outputs/queries_draft.jsonl", help="Native JSONL for fetch stage"),
    model: str = typer.Option("openai:gpt-4o-mini", help="Model spec")
):
    proto = Path(protocol_json).read_text(encoding="utf-8")
    prompt = Path("prompts/03_queries.txt").read_text(encoding="utf-8").format(protocol_json=proto)
    raw = call_llm(prompt, model=model)
    # If model returns multiple lines of JSONL or a single block, normalize
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    # basic cleanup: remove code fences if any
    lines = [l for l in lines if not l.startswith("```")]
    ensure_dir(Path(out_path).parent)
    with open(out_path, "w", encoding="utf-8") as f:
        for l in lines:
            try:
                json.loads(l)  # validate
                f.write(l + "\n")
            except Exception:
                # try single JSON array case
                try:
                    arr = json.loads("\n".join(lines))
                    for obj in arr:
                        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    break
                except Exception:
                    pass
    typer.echo(f"[OK] Query candidates -> {out_path}")

@app.command("freeze")
def freeze(
    protocol_json: str = typer.Option("outputs/protocol_draft.json"),
    refinements_json: str = typer.Option("outputs/refinements.json"),
    outdir: str = typer.Option("frozen"),
):
    ensure_dir(Path(outdir))
    proto = json.loads(Path(protocol_json).read_text(encoding="utf-8"))
    ref   = json.loads(Path(refinements_json).read_text(encoding="utf-8")) if os.path.exists(refinements_json) else {}

    final = {
        **proto,
        "screening": {
            **proto.get("screening", {}),
            "inclusion_criteria": ref.get("inclusion_criteria_refined", proto.get("screening", {}).get("inclusion_criteria", [])),
            "exclusion_criteria": ref.get("exclusion_criteria_refined", proto.get("screening", {}).get("exclusion_criteria", []))
        }
    }
    payload = json.dumps(final, ensure_ascii=False, separators=(",",":"))
    checksum = sha256_text(payload)
    manifest = {
        "frozen_at_utc": datetime.datetime.utcnow().isoformat()+"Z",
        "protocol_sha256": checksum,
        "source_files": [protocol_json, refinements_json] if os.path.exists(refinements_json) else [protocol_json],
        "notes": "Freeze before data harvesting; include this hash in PRISMA/methods."
    }
    Path(outdir,"protocol.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(outdir,"manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"[OK] Protocol frozen -> {Path(outdir,'protocol.json')} (sha256={checksum[:12]}...)")

if __name__ == "__main__":
    app()
