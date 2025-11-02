
export enum Step {
  Subject = 'Subject',
  Draft = 'Draft',
  Refine = 'Refine',
  Queries = 'Queries',
  Freeze = 'Freeze',
}

export interface Picos {
  population?: string[];
  intervention?: string[];
  comparison?: string[];
  outcomes?: string[];
  context?: string[];
}

export interface Keywords {
  include: string[];
  exclude: string[];
  synonyms?: Record<string, string[]>;
}

export interface Screening {
  inclusion_criteria: string[];
  exclusion_criteria: string[];
  years: [number, number];
  languages: string[];
  doc_types: string[];
}

export interface Protocol {
  research_questions: string[];
  picos?: Picos;
  keywords: Keywords;
  screening: Screening;
  sources: string[];
  rationales?: {
    scope?: string;
    risks?: string;
  };
}

export interface Refinements {
  inclusion_criteria_refined: string[];
  exclusion_criteria_refined: string[];
  borderline_examples: {
    text: string;
    suggested: 'INCLUDE' | 'EXCLUDE' | 'MAYBE';
    why: string;
  }[];
  risks_and_ambiguities: string[];
}

export interface Query {
  family: string;
  provider: string;
  native: Record<string, any>;
  budget: {
    max_results: number;
  };
  rationale: string;
}

export interface Manifest {
  timestamp_utc: string;
  sha256_hash: string;
  source_files: string[];
}

export interface AppState {
  apiKey: string;
  modelName: string;
  currentStep: Step;
  subjectText: string;
  subjectFileName: string;
  protocolDraft: Protocol | null;
  protocolDraftValidationErrors: any[];
  wasProtocolDraftFromFallback: boolean;
  checklist: string;
  refinements: Refinements | null;
  wasRefinementsFromFallback: boolean;
  queries: Query[];
  wasQueriesFromFallback: boolean;
  frozenProtocol: Protocol | null;
  frozenManifest: Manifest | null;
}
