
import React, { useContext, useState, useEffect } from 'react';
import { AppContext } from '../state/AppContext';
import { Step, Protocol } from '../types';
import JsonEditor from '../components/JsonEditor';
import { downloadFile } from '../utils/download';
import { validateProtocol } from '../utils/schema';
import { prettyJSONStringify } from '../utils/json';

const DraftStep: React.FC = () => {
  const { state, dispatch } = useContext(AppContext);
  const [jsonString, setJsonString] = useState('');

  useEffect(() => {
    if (state.protocolDraft) {
      setJsonString(prettyJSONStringify(state.protocolDraft));
    }
  }, [state.protocolDraft]);

  const handleJsonChange = (newJsonString: string) => {
    setJsonString(newJsonString);
    try {
      const parsed = JSON.parse(newJsonString) as Protocol;
      const { isValid, errors } = validateProtocol(parsed);
      dispatch({
        type: 'SET_DRAFT_PROTOCOL',
        payload: {
          protocol: parsed,
          errors,
          fromFallback: state.wasProtocolDraftFromFallback,
        },
      });
    } catch (e) {
      // Don't update state if JSON is invalid, but keep the string
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-semibold text-sky-300">2. Draft Protocol</h2>
      
      {state.wasProtocolDraftFromFallback && (
        <div className="p-3 bg-yellow-900/50 border border-yellow-700 rounded-md text-yellow-300 text-sm">
          <strong>Offline Mode:</strong> This protocol was generated using the built-in fallback data.
        </div>
      )}

      <div>
        <h3 className="text-lg font-semibold mb-2">Protocol JSON</h3>
        <p className="text-slate-400 mb-4 text-sm">Review and edit the generated protocol. Validation errors will be shown below.</p>
        <JsonEditor
          jsonString={jsonString}
          onJsonChange={handleJsonChange}
          validationErrors={state.protocolDraftValidationErrors}
        />
        <button
          onClick={() => downloadFile(jsonString, 'protocol_draft.json', 'application/json')}
          className="mt-4 bg-slate-600 hover:bg-slate-500 text-white font-semibold px-4 py-2 rounded-md text-sm"
        >
          Download protocol_draft.json
        </button>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-2">Checklist</h3>
        <div className="prose prose-invert bg-slate-900 p-4 rounded-md border border-slate-600">
           <pre className="whitespace-pre-wrap text-sm">{state.checklist}</pre>
        </div>
         <button
          onClick={() => downloadFile(state.checklist, 'checklist.md', 'text/markdown')}
          className="mt-4 bg-slate-600 hover:bg-slate-500 text-white font-semibold px-4 py-2 rounded-md text-sm"
        >
          Download checklist.md
        </button>
      </div>

      <div className="flex justify-end mt-4">
        <button
          onClick={() => dispatch({ type: 'SET_CURRENT_STEP', payload: Step.Refine })}
          className="bg-sky-600 hover:bg-sky-500 text-white font-bold px-6 py-3 rounded-md transition-colors"
        >
          Refine Criteria →
        </button>
      </div>
    </div>
  );
};

export default DraftStep;
