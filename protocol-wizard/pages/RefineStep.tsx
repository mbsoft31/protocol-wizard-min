
import React, { useContext, useState, useEffect } from 'react';
import { AppContext } from '../state/AppContext';
import { Step, Refinements } from '../types';
import JsonEditor from '../components/JsonEditor';
import { generateRefinements } from '../services/gemini';
import { useToast } from '../hooks/useToast';
import { downloadFile } from '../utils/download';
import { prettyJSONStringify } from '../utils/json';

const RefineStep: React.FC = () => {
  const { state, dispatch } = useContext(AppContext);
  const [isLoading, setIsLoading] = useState(false);
  const [jsonString, setJsonString] = useState('');
  const { addToast } = useToast();

  useEffect(() => {
    if (state.refinements) {
      setJsonString(prettyJSONStringify(state.refinements));
    } else if (state.protocolDraft) {
      handleGenerateRefinements();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
      if(state.refinements) {
        setJsonString(prettyJSONStringify(state.refinements));
      }
  }, [state.refinements]);


  const handleGenerateRefinements = async () => {
    if (!state.protocolDraft) return;
    setIsLoading(true);
    try {
      const result = await generateRefinements(state.protocolDraft, state.apiKey, state.modelName);
      dispatch({
        type: 'SET_REFINEMENTS',
        payload: { refinements: result.data, fromFallback: result.fromFallback },
      });
      addToast(`Refinements generated ${result.fromFallback ? 'from fallback' : 'by AI'}.`, result.fromFallback ? 'info' : 'success');
    } catch (error) {
      addToast('Failed to generate refinements.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleJsonChange = (newJsonString: string) => {
    setJsonString(newJsonString);
    try {
      const parsed = JSON.parse(newJsonString) as Refinements;
       dispatch({
        type: 'SET_REFINEMENTS',
        payload: { refinements: parsed, fromFallback: state.wasRefinementsFromFallback },
      });
    } catch (e) {
      // Invalid JSON, don't update state
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-semibold text-sky-300">3. Refine Criteria</h2>
      
      {isLoading && <p className="text-sky-300">Generating refinements...</p>}
      
      {state.wasRefinementsFromFallback && (
        <div className="p-3 bg-yellow-900/50 border border-yellow-700 rounded-md text-yellow-300 text-sm">
          <strong>Offline Mode:</strong> Refinements were generated using the built-in fallback data.
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold mb-2">Draft Protocol (Read-only)</h3>
          <JsonEditor
            jsonString={state.protocolDraft ? prettyJSONStringify(state.protocolDraft) : '{}'}
            onJsonChange={() => {}}
            validationErrors={[]}
            readOnly={true}
          />
        </div>
        <div>
          <h3 className="text-lg font-semibold mb-2">Refined Criteria</h3>
          <JsonEditor
            jsonString={jsonString}
            onJsonChange={handleJsonChange}
            validationErrors={[]}
          />
        </div>
      </div>
      
       <div className="flex items-center gap-4">
          <button
            onClick={() => downloadFile(jsonString, 'refinements.json', 'application/json')}
            className="bg-slate-600 hover:bg-slate-500 text-white font-semibold px-4 py-2 rounded-md text-sm"
            disabled={!state.refinements}
          >
            Download refinements.json
          </button>
           <button
            onClick={handleGenerateRefinements}
            disabled={isLoading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded-md text-sm"
          >
            {isLoading ? 'Re-generating...' : 'Re-generate'}
          </button>
       </div>

      <div className="flex justify-end mt-4">
        <button
          onClick={() => dispatch({ type: 'SET_CURRENT_STEP', payload: Step.Queries })}
          disabled={!state.refinements}
          className="bg-sky-600 hover:bg-sky-500 disabled:bg-slate-600 text-white font-bold px-6 py-3 rounded-md transition-colors"
        >
          Generate Queries →
        </button>
      </div>
    </div>
  );
};

export default RefineStep;
