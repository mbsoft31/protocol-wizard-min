
import React, { createContext, useReducer, useEffect, ReactNode, Dispatch } from 'react';
import { AppState, Step } from '../types';
import { SAMPLE_SUBJECT_TEXT } from '../constants';

type Action =
  | { type: 'SET_API_KEY'; payload: string }
  | { type: 'SET_MODEL_NAME'; payload: string }
  | { type: 'SET_CURRENT_STEP'; payload: Step }
  | { type: 'SET_SUBJECT'; payload: { text: string; fileName: string } }
  | { type: 'SET_DRAFT_PROTOCOL'; payload: { protocol: AppState['protocolDraft'], errors: any[], fromFallback: boolean } }
  | { type: 'SET_CHECKLIST'; payload: string }
  | { type: 'SET_REFINEMENTS'; payload: { refinements: AppState['refinements'], fromFallback: boolean } }
  | { type: 'SET_QUERIES'; payload: { queries: AppState['queries'], fromFallback: boolean } }
  | { type: 'SET_FROZEN_DATA'; payload: { protocol: AppState['frozenProtocol'], manifest: AppState['frozenManifest'] } }
  | { type: 'RESET_STATE' }
  | { type: 'HYDRATE_STATE'; payload: AppState };

const initialState: AppState = {
  apiKey: '',
  modelName: 'gemini-2.5-flash',
  currentStep: Step.Subject,
  subjectText: SAMPLE_SUBJECT_TEXT,
  subjectFileName: 'inline',
  protocolDraft: null,
  protocolDraftValidationErrors: [],
  wasProtocolDraftFromFallback: false,
  checklist: '',
  refinements: null,
  wasRefinementsFromFallback: false,
  queries: [],
  wasQueriesFromFallback: false,
  frozenProtocol: null,
  frozenManifest: null,
};

const appReducer = (state: AppState, action: Action): AppState => {
  switch (action.type) {
    case 'SET_API_KEY':
      return { ...state, apiKey: action.payload };
    case 'SET_MODEL_NAME':
      return { ...state, modelName: action.payload };
    case 'SET_CURRENT_STEP':
      return { ...state, currentStep: action.payload };
    case 'SET_SUBJECT':
      return { ...state, subjectText: action.payload.text, subjectFileName: action.payload.fileName, currentStep: Step.Subject };
    case 'SET_DRAFT_PROTOCOL':
      return { ...state, protocolDraft: action.payload.protocol, protocolDraftValidationErrors: action.payload.errors, wasProtocolDraftFromFallback: action.payload.fromFallback };
    case 'SET_CHECKLIST':
        return { ...state, checklist: action.payload };
    case 'SET_REFINEMENTS':
      return { ...state, refinements: action.payload.refinements, wasRefinementsFromFallback: action.payload.fromFallback };
    case 'SET_QUERIES':
      return { ...state, queries: action.payload.queries, wasQueriesFromFallback: action.payload.fromFallback };
    case 'SET_FROZEN_DATA':
      return { ...state, frozenProtocol: action.payload.protocol, frozenManifest: action.payload.manifest };
    case 'RESET_STATE':
        const apiKey = state.apiKey;
        const modelName = state.modelName;
        return { ...initialState, apiKey, modelName, subjectText: '' };
    case 'HYDRATE_STATE':
        return { ...state, ...action.payload };
    default:
      return state;
  }
};

export const AppContext = createContext<{
  state: AppState;
  dispatch: Dispatch<Action>;
}>({
  state: initialState,
  dispatch: () => null,
});

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  useEffect(() => {
    try {
      const storedState = localStorage.getItem('protocolWizardState');
      if (storedState) {
        dispatch({ type: 'HYDRATE_STATE', payload: JSON.parse(storedState) });
      }
    } catch (error) {
      console.error("Failed to parse state from localStorage", error);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('protocolWizardState', JSON.stringify(state));
  }, [state]);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
};
