
import React, { useContext } from 'react';
import { AppContext } from './state/AppContext';
import Layout from './components/Layout';
import StepIndicator from './components/StepIndicator';
import SubjectStep from './pages/SubjectStep';
import DraftStep from './pages/DraftStep';
import RefineStep from './pages/RefineStep';
import QueriesStep from './pages/QueriesStep';
import FreezeStep from './pages/FreezeStep';
import { Step } from './types';

const App: React.FC = () => {
  const { state } = useContext(AppContext);

  const renderStep = () => {
    switch (state.currentStep) {
      case Step.Subject:
        return <SubjectStep />;
      case Step.Draft:
        return <DraftStep />;
      case Step.Refine:
        return <RefineStep />;
      case Step.Queries:
        return <QueriesStep />;
      case Step.Freeze:
        return <FreezeStep />;
      default:
        return <SubjectStep />;
    }
  };

  return (
    <Layout>
      <header className="text-center mb-8">
        <h1 className="text-4xl font-bold text-sky-400">Protocol Wizard</h1>
        <p className="text-slate-400 mt-2">Generate SLR protocols with AI assistance</p>
      </header>
      <StepIndicator currentStep={state.currentStep} />
      <main className="mt-8 bg-slate-800 p-4 sm:p-6 rounded-lg shadow-lg min-h-[50vh]">
        {renderStep()}
      </main>
    </Layout>
  );
};

export default App;
