
import React, { useContext, useState } from 'react';
import { AppContext } from '../state/AppContext';
import { Step } from '../types';
import { generateDraftProtocol } from '../services/gemini';
import { validateProtocol } from '../utils/schema';
import { useToast } from '../hooks/useToast';
import { SAMPLE_SUBJECT_TEXT } from '../constants';

const SubjectStep: React.FC = () => {
  const { state, dispatch } = useContext(AppContext);
  const [isLoading, setIsLoading] = useState(false);
  const { addToast } = useToast();

  const handleDraft = async () => {
    if (!state.subjectText.trim()) {
      addToast('Please provide a subject text.', 'error');
      return;
    }
    setIsLoading(true);
    try {
      const result = await generateDraftProtocol(state.subjectText, state.apiKey, state.modelName);
      const { isValid, errors } = validateProtocol(result.data);
      dispatch({ type: 'SET_DRAFT_PROTOCOL', payload: { protocol: result.data, errors, fromFallback: result.fromFallback } });
      
      const checklist = `### Human-in-the-Loop Checklist\n\n- [ ] **Research Questions**: Are they clear, focused, and answerable?\n- [ ] **Keywords**: Do they cover synonyms and exclude irrelevant topics?\n- [ ] **Inclusion/Exclusion Criteria**: Are they unambiguous and testable?\n- [ ] **Sources**: Are the selected databases appropriate for the topic?`;
      dispatch({ type: 'SET_CHECKLIST', payload: checklist });

      dispatch({ type: 'SET_CURRENT_STEP', payload: Step.Draft });
      addToast(`Protocol draft generated ${result.fromFallback ? 'from fallback' : 'by AI'}.`, result.fromFallback ? 'info' : 'success');
      if (!isValid) {
        addToast('The generated protocol has validation issues. Please review.', 'error');
      }
    } catch (error) {
      addToast('Failed to generate protocol draft.', 'error');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        dispatch({ type: 'SET_SUBJECT', payload: { text, fileName: file.name } });
      };
      reader.readAsText(file);
    }
  };
  
  const handleReset = () => {
      dispatch({ type: 'RESET_STATE' });
      addToast('State has been reset.', 'info');
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-2xl font-semibold text-sky-300">1. Subject</h2>
      <p className="text-slate-400">
        Start by describing your research topic. This text will be used to generate the initial draft of your protocol.
      </p>
      
      <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => dispatch({ type: 'SET_SUBJECT', payload: { text: SAMPLE_SUBJECT_TEXT, fileName: 'inline' } })}
            className="bg-slate-600 hover:bg-slate-500 text-white font-semibold px-4 py-2 rounded-md text-sm"
          >
            Load Sample
          </button>
          <label className="bg-slate-600 hover:bg-slate-500 text-white font-semibold px-4 py-2 rounded-md text-sm cursor-pointer">
            Upload File
            <input type="file" className="hidden" accept=".txt,.md" onChange={handleFileChange} />
          </label>
           <button
            onClick={handleReset}
            className="bg-red-700 hover:bg-red-600 text-white font-semibold px-4 py-2 rounded-md text-sm"
          >
            Reset All
          </button>
      </div>

      <textarea
        value={state.subjectText}
        onChange={(e) => dispatch({ type: 'SET_SUBJECT', payload: { text: e.target.value, fileName: 'inline' } })}
        placeholder="Describe your research topic here..."
        className="w-full h-48 p-3 bg-slate-700 border border-slate-600 rounded-md focus:ring-2 focus:ring-sky-500 focus:outline-none transition-colors"
      />
      
      <div className="flex justify-end mt-4">
        <button
          onClick={handleDraft}
          disabled={isLoading || !state.subjectText.trim()}
          className="bg-sky-600 hover:bg-sky-500 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-bold px-6 py-3 rounded-md transition-colors"
        >
          {isLoading ? 'Generating...' : 'Draft Protocol →'}
        </button>
      </div>
    </div>
  );
};

export default SubjectStep;
