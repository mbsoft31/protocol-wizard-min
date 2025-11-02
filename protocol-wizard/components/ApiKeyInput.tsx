
import React, { useContext, useState, useEffect } from 'react';
import { AppContext } from '../state/AppContext';

const ApiKeyInput: React.FC = () => {
  const { state, dispatch } = useContext(AppContext);
  const [localKey, setLocalKey] = useState(state.apiKey);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    setLocalKey(state.apiKey);
  }, [state.apiKey]);

  const handleSave = () => {
    dispatch({ type: 'SET_API_KEY', payload: localKey });
    setIsEditing(false);
  };
  
  const envKeyExists = !!process.env.VITE_GOOGLE_API_KEY;

  if (envKeyExists) {
      return (
          <div className="text-center text-sm text-green-400 p-2 bg-green-900/50 rounded-md">
            API key loaded from environment variable.
          </div>
      )
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="w-full max-w-md">
        {isEditing ? (
          <div className="flex items-center gap-2">
            <input
              type="password"
              value={localKey}
              onChange={(e) => setLocalKey(e.target.value)}
              placeholder="Enter your Gemini API Key"
              className="w-full bg-slate-700 text-slate-200 border border-slate-600 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
            />
            <button
              onClick={handleSave}
              className="bg-sky-600 hover:bg-sky-500 text-white font-semibold px-4 py-2 rounded-md text-sm transition-colors"
            >
              Save
            </button>
          </div>
        ) : (
          <button
            onClick={() => setIsEditing(true)}
            className="text-slate-400 hover:text-sky-400 underline text-sm"
          >
            {state.apiKey ? 'Edit API Key' : 'Set API Key'}
          </button>
        )}
      </div>
      <p className="text-xs text-slate-500">Your key is stored only in your browser's localStorage.</p>
    </div>
  );
};

export default ApiKeyInput;
