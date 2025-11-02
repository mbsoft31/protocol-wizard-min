
import React from 'react';
import { prettyJSONStringify } from '../utils/json';

interface JsonEditorProps {
  jsonString: string;
  onJsonChange: (newJsonString: string) => void;
  validationErrors: any[];
  readOnly?: boolean;
}

const JsonEditor: React.FC<JsonEditorProps> = ({ jsonString, onJsonChange, validationErrors, readOnly = false }) => {
  const formatJson = () => {
    try {
      const parsed = JSON.parse(jsonString);
      onJsonChange(prettyJSONStringify(parsed));
    } catch (e) {
      // Ignore formatting errors if JSON is invalid
      console.error("Cannot format invalid JSON");
    }
  };

  return (
    <div>
      <div className="flex justify-end mb-2">
        {!readOnly && (
           <button
             onClick={formatJson}
             className="bg-slate-600 hover:bg-slate-500 text-white font-semibold px-3 py-1 rounded-md text-xs transition-colors"
           >
             Format JSON
           </button>
        )}
      </div>
      <textarea
        value={jsonString}
        onChange={(e) => onJsonChange(e.target.value)}
        readOnly={readOnly}
        className={`w-full h-96 p-3 font-mono text-sm bg-slate-900 border rounded-md focus:ring-2 focus:outline-none transition-colors ${
          validationErrors.length > 0 ? 'border-red-500 focus:ring-red-500' : 'border-slate-600 focus:ring-sky-500'
        }`}
        spellCheck="false"
      />
      {validationErrors.length > 0 && (
        <div className="mt-2 p-3 bg-red-900/50 border border-red-700 rounded-md text-red-300 text-sm">
          <h4 className="font-bold mb-1">Validation Errors:</h4>
          <ul>
            {validationErrors.map((error, index) => (
              <li key={index} className="font-mono text-xs">
                {error.instancePath && `${error.instancePath}: `}
                {error.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default JsonEditor;
