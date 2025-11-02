
import React, { useContext, useState, useEffect } from 'react';
import { AppContext } from '../state/AppContext';
import { Step } from '../types';
import { generateQueries } from '../services/gemini';
import { useToast } from '../hooks/useToast';
import { downloadFile } from '../utils/download';
import { normalizeAndStringifyJsonl } from '../utils/json';

const QueriesStep: React.FC = () => {
  const { state, dispatch } = useContext(AppContext);
  const [isLoading, setIsLoading] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    if (state.queries.length === 0 && !state.wasQueriesFromFallback) {
      handleGenerateQueries();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGenerateQueries = async () => {
    if (!state.protocolDraft) return;
    setIsLoading(true);
    try {
      const result = await generateQueries(state.protocolDraft, state.apiKey, state.modelName);
      dispatch({
        type: 'SET_QUERIES',
        payload: { queries: result.data, fromFallback: result.fromFallback },
      });
      addToast(`Queries generated ${result.fromFallback ? 'from fallback' : 'by AI'}.`, result.fromFallback ? 'info' : 'success');
    } catch (error) {
      addToast('Failed to generate queries.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const jsonlString = normalizeAndStringifyJsonl(state.queries);

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-semibold text-sky-300">4. Generate Queries</h2>
      {isLoading && <p className="text-sky-300">Generating queries...</p>}

      {state.wasQueriesFromFallback && (
        <div className="p-3 bg-yellow-900/50 border border-yellow-700 rounded-md text-yellow-300 text-sm">
          <strong>Offline Mode:</strong> No queries were generated as this step requires an API key.
        </div>
      )}

      <div>
        <h3 className="text-lg font-semibold mb-2">Query Candidates (JSONL)</h3>
        <div className="bg-slate-900 p-4 rounded-md border border-slate-600 h-96 overflow-auto">
          {state.queries.length > 0 ? (
            state.queries.map((query, index) => (
              <pre key={index} className="text-xs font-mono p-2 border-b border-slate-700 whitespace-pre-wrap">
                {JSON.stringify(query)}
              </pre>
            ))
          ) : (
            <p className="text-slate-400">No queries generated.</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={() => downloadFile(jsonlString, 'queries_draft.jsonl', 'application/json-lines')}
          className="bg-slate-600 hover:bg-slate-500 text-white font-semibold px-4 py-2 rounded-md text-sm"
          disabled={state.queries.length === 0}
        >
          Download queries_draft.jsonl
        </button>
        <button
          onClick={handleGenerateQueries}
          disabled={isLoading}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded-md text-sm"
        >
          {isLoading ? 'Re-generating...' : 'Re-generate'}
        </button>
      </div>

      <div className="flex justify-end mt-4">
        <button
          onClick={() => dispatch({ type: 'SET_CURRENT_STEP', payload: Step.Freeze })}
          className="bg-sky-600 hover:bg-sky-500 text-white font-bold px-6 py-3 rounded-md transition-colors"
        >
          Freeze Protocol →
        </button>
      </div>
    </div>
  );
};

export default QueriesStep;
