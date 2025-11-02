
import React, { useContext, useEffect, useState } from 'react';
import { AppContext } from '../state/AppContext';
import { Protocol, Manifest, Step } from '../types';
import { useToast } from '../hooks/useToast';
import { canonicalJSONStringify, prettyJSONStringify } from '../utils/json';
import { sha256Hex } from '../utils/crypto';
import { downloadFile } from '../utils/download';

const FreezeStep: React.FC = () => {
  const { state, dispatch } = useContext(AppContext);
  const { addToast } = useToast();
  const [isFrozen, setIsFrozen] = useState(false);

  const handleFreeze = async () => {
    if (!state.protocolDraft || !state.refinements) {
      addToast('Missing data to freeze protocol.', 'error');
      return;
    }

    const finalProtocol: Protocol = {
      ...state.protocolDraft,
      screening: {
        ...state.protocolDraft.screening,
        inclusion_criteria: state.refinements.inclusion_criteria_refined,
        exclusion_criteria: state.refinements.exclusion_criteria_refined,
      },
    };

    const canonicalString = canonicalJSONStringify(finalProtocol);
    const hash = await sha256Hex(canonicalString);

    const manifest: Manifest = {
      timestamp_utc: new Date().toISOString(),
      sha256_hash: hash,
      source_files: [state.subjectFileName],
    };

    dispatch({
      type: 'SET_FROZEN_DATA',
      payload: { protocol: finalProtocol, manifest },
    });
    addToast('Protocol has been frozen successfully!', 'success');
    setIsFrozen(true);
  };
  
  useEffect(() => {
    if (state.frozenProtocol && state.frozenManifest) {
      setIsFrozen(true);
    }
  }, [state.frozenProtocol, state.frozenManifest]);


  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-semibold text-sky-300">5. Freeze Protocol</h2>
      
      {!isFrozen && (
        <div className="flex flex-col items-center text-center p-8 bg-slate-700/50 rounded-lg">
          <p className="mb-4">
            This final step will merge the refined criteria into the protocol, compute a SHA-256 hash to ensure integrity, and generate a manifest file. This action is irreversible for the current session.
          </p>
          <button
            onClick={handleFreeze}
            className="bg-green-600 hover:bg-green-500 text-white font-bold px-8 py-4 rounded-md text-lg transition-colors"
          >
            Freeze Protocol
          </button>
        </div>
      )}
      
      {isFrozen && state.frozenProtocol && state.frozenManifest && (
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold mb-2">Frozen Protocol</h3>
            <pre className="bg-slate-900 p-4 rounded-md border border-slate-600 h-96 overflow-auto text-xs font-mono">
                {prettyJSONStringify(state.frozenProtocol)}
            </pre>
            <button
              onClick={() => downloadFile(prettyJSONStringify(state.frozenProtocol), 'protocol.json', 'application/json')}
              className="mt-4 bg-slate-600 hover:bg-slate-500 text-white font-semibold px-4 py-2 rounded-md text-sm"
            >
              Download protocol.json
            </button>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-2">Manifest</h3>
             <pre className="bg-slate-900 p-4 rounded-md border border-slate-600 h-auto overflow-auto text-xs font-mono">
                {prettyJSONStringify(state.frozenManifest)}
            </pre>
             <button
              onClick={() => downloadFile(prettyJSONStringify(state.frozenManifest), 'manifest.json', 'application/json')}
              className="mt-4 bg-slate-600 hover:bg-slate-500 text-white font-semibold px-4 py-2 rounded-md text-sm"
            >
              Download manifest.json
            </button>
            <div className="mt-4 p-4 bg-slate-900 rounded-md">
                <h4 className="font-bold text-slate-300">SHA-256 Hash</h4>
                <p className="font-mono text-green-400 text-xs break-all">{state.frozenManifest.sha256_hash}</p>
            </div>
          </div>
        </div>
      )}

       <div className="flex justify-end mt-4">
        <button
          onClick={() => dispatch({type: 'SET_CURRENT_STEP', payload: Step.Subject})}
          className="bg-sky-600 hover:bg-sky-500 text-white font-bold px-6 py-3 rounded-md transition-colors"
        >
          Start Over
        </button>
      </div>
    </div>
  );
};

export default FreezeStep;
