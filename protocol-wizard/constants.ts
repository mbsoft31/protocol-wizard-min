
import { Protocol, Refinements } from './types';

export const SAMPLE_SUBJECT_TEXT = `I'm exploring how deep learning models for plant disease detection, which work well in controlled lab settings, perform when deployed in real-world field conditions. I want to understand the 'lab-to-field' generalization gap, the factors causing performance drops (like lighting, background complexity, different camera types), and methods to make these models more robust. This is for a systematic literature review.`;

// --- FALLBACK OBJECTS ---

export const DRAFT_FALLBACK: Protocol = {
  "research_questions": ["How do deep models generalize from lab to field for plant disease detection?"],
  "picos": { "population": ["crop plants"], "intervention": ["deep learning detection"], "comparison": ["lab vs field"], "outcomes": ["accuracy drop"], "context": ["field conditions"] },
  "keywords": {
    "include": ["plant disease detection", "domain shift", "field images", "lab-to-field", "generalization"],
    "exclude": ["yield prediction", "irrigation only"],
    "synonyms": { "domain shift": ["dataset shift", "external validity"] }
  },
  "screening": {
    "inclusion_criteria": ["disease detection task", "machine/deep learning method", "includes field images or lab-to-field evaluation"],
    "exclusion_criteria": ["yield-only studies", "pure irrigation optimization", "simulation-only with no field data"],
    "years": [2015, 2025],
    "languages": ["en", "fr", "ar"],
    "doc_types": ["journal", "conference", "preprint"]
  },
  "sources": ["openalex", "crossref", "pubmed", "arxiv"],
  "rationales": { "scope": "Focus on robustness and domain shift.", "risks": "Non-English coverage might be thin; RS may drift scope." }
};

export const REFINE_FALLBACK: Refinements = {
  "inclusion_criteria_refined": ["ML vision for plant disease detection", "has field images or lab-to-field eval"],
  "exclusion_criteria_refined": ["yield-only", "irrigation-only", "pure simulation"],
  "borderline_examples": [{ "text": "Greenhouse + small field pilot", "suggested": "MAYBE", "why": "pilot may qualify" }],
  "risks_and_ambiguities": ["Remote sensing scope creep"]
};

// --- PROMPT TEMPLATES ---

export const DRAFT_PROMPT_TEMPLATE = `
SYSTEM:
You are a meticulous SLR methods editor. Output JSON only, matching the schema below.
Be specific, avoid buzzwords, and justify choices briefly in rationales.

SCHEMA (JSON):
{
  "research_questions": ["..."],
  "picos": { "population": [], "intervention": [], "comparison": [], "outcomes": [], "context": [] },
  "keywords": { "include": [], "exclude": [], "synonyms": { "term": ["..."] } },
  "screening": {
    "inclusion_criteria": ["..."],
    "exclusion_criteria": ["..."],
    "years": [2015, 2025],
    "languages": ["en","fr","ar"],
    "doc_types": ["journal","conference","preprint"]
  },
  "sources": ["openalex","crossref","semanticscholar","pubmed","arxiv"],
  "rationales": { "scope": "", "risks": "" }
}

USER:
Topic description:
<<<
{subject_text}
>>>

Return JSON only.
`;

export const REFINE_PROMPT_TEMPLATE = `
SYSTEM: You are revising SLR screening rules for clarity and testability. Return JSON only.

INPUT PROTOCOL (JSON):
{protocol_json}

TASKS:

1. Tighten inclusion/exclusion into atomic, testable bullets (avoid subjective words).
2. Add 5 borderline examples (short sentences) with suggested decisions.
3. Flag any scope risks or ambiguities.

OUTPUT SCHEMA:
{
  "inclusion_criteria_refined": ["..."],
  "exclusion_criteria_refined": ["..."],
  "borderline_examples": [{"text":"...", "suggested":"INCLUDE|EXCLUDE|MAYBE", "why":"..."}],
  "risks_and_ambiguities": ["..."]
}
`;

export const QUERIES_PROMPT_TEMPLATE = `
SYSTEM: You are a research librarian. Create diverse query families and provider-native params. Return JSONL.

INPUT PROTOCOL (JSON):
{protocol_json}

OUTPUT (one JSON per line):
{"family":"generalization","provider":"openalex","native":{"search":"domain shift plant disease field","filter":"language:en,from_publication_date:2015-01-01"},"budget":{"max_results":800},"rationale":"core problem"}
{"family":"adversarial","provider":"crossref","native":{"query.bibliographic":"external validity crop -PlantVillage","filter":"from-pub-date:2015-01-01"},"budget":{"max_results":600},"rationale":"avoid dataset bias"}
{"family":"biomed","provider":"pubmed","native":{"term":"(domain shift) AND (field[Title/Abstract]) AND (crop OR plant)","mindate":"2015/01/01","maxdate":"3000/12/31"},"budget":{"max_results":800},"rationale":"biomed overlap"}
`;

// --- PROTOCOL SCHEMA ---

export const PROTOCOL_SCHEMA = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "research_questions",
    "keywords",
    "screening",
    "sources"
  ],
  "properties": {
    "research_questions": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1
    },
    "picos": { "type": "object" },
    "keywords": {
      "type": "object",
      "required": ["include", "exclude"],
      "properties": {
        "include": { "type": "array", "items": { "type": "string" } },
        "exclude": { "type": "array", "items": { "type": "string" } },
        "synonyms": { "type": "object" }
      }
    },
    "screening": {
      "type": "object",
      "required": ["inclusion_criteria", "exclusion_criteria", "years", "languages", "doc_types"]
    },
    "sources": {
      "type": "array",
      "items": { "type": "string" }
    },
    "rationales": { "type": "object" }
  }
};
