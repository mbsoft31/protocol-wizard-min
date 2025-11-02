
import React, { useContext } from 'react';
import { AppContext } from '../state/AppContext';
import { Step } from '../types';

interface StepIndicatorProps {
  currentStep: Step;
}

const STEPS = [Step.Subject, Step.Draft, Step.Refine, Step.Queries, Step.Freeze];

const StepIndicator: React.FC<StepIndicatorProps> = ({ currentStep }) => {
  const { state, dispatch } = useContext(AppContext);
  const currentIndex = STEPS.indexOf(currentStep);

  const isStepCompleted = (step: Step) => {
    switch (step) {
      case Step.Subject:
        return !!state.subjectText;
      case Step.Draft:
        return !!state.protocolDraft;
      case Step.Refine:
        return !!state.refinements;
      case Step.Queries:
        return state.queries.length > 0 || state.wasQueriesFromFallback;
      case Step.Freeze:
        return !!state.frozenProtocol;
      default:
        return false;
    }
  };
  
  const handleStepClick = (step: Step, index: number) => {
    if (index < currentIndex || isStepCompleted(step)) {
      dispatch({ type: 'SET_CURRENT_STEP', payload: step });
    }
  };

  return (
    <nav className="flex justify-center">
      <ol className="flex items-center space-x-2 sm:space-x-4">
        {STEPS.map((step, index) => {
          const isCurrent = index === currentIndex;
          const isCompleted = index < currentIndex || isStepCompleted(step);
          const isClickable = index < currentIndex || isStepCompleted(step);

          return (
            <li key={step} className="flex items-center">
              <button
                onClick={() => handleStepClick(step, index)}
                disabled={!isClickable && !isCurrent}
                className={`flex flex-col items-center text-center px-2 py-1 rounded-md transition-colors ${
                  isClickable ? 'cursor-pointer hover:bg-slate-700' : 'cursor-default'
                } ${isCurrent ? 'text-sky-400' : 'text-slate-400'}`}
              >
                <span
                  className={`flex items-center justify-center w-8 h-8 rounded-full border-2 font-bold text-sm mb-1 ${
                    isCurrent ? 'bg-sky-400 border-sky-400 text-slate-900' : isCompleted ? 'bg-green-500 border-green-500 text-white' : 'border-slate-600'
                  }`}
                >
                  {index + 1}
                </span>
                <span className="text-xs sm:text-sm font-medium">{step}</span>
              </button>
              {index < STEPS.length - 1 && (
                <div className="h-0.5 w-8 sm:w-16 bg-slate-600 mx-1 sm:mx-2" />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

export default StepIndicator;
