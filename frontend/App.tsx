
import React, { useState } from 'react';
import { SessionState, TrainingSessionConfig, TranscriptionItem } from './types';
import SetupForm from './components/SetupForm';
import LiveConversation from './components/LiveConversation';
import EvaluationView from './components/EvaluationView';

const App: React.FC = () => {
  const [state, setState] = useState<SessionState>(SessionState.SETUP);
  const [config, setConfig] = useState<TrainingSessionConfig | null>(null);
  const [history, setHistory] = useState<TranscriptionItem[]>([]);

  const handleStart = (newConfig: TrainingSessionConfig) => {
    setConfig(newConfig);
    setState(SessionState.ACTIVE);
  };

  const handleEnd = (finalHistory: TranscriptionItem[]) => {
    setHistory(finalHistory);
    setState(SessionState.EVALUATION);
  };

  const handleReset = () => {
    setState(SessionState.SETUP);
    setConfig(null);
    setHistory([]);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-slate-800 tracking-tight">Bandhan Life Trainer</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs font-semibold px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full">LIVE API 2.5</span>
          </div>
        </div>
      </header>

      <main className="flex-1 p-6 lg:p-12 max-w-7xl mx-auto w-full">
        {state === SessionState.SETUP && (
          <SetupForm onStart={handleStart} />
        )}

        {state === SessionState.ACTIVE && config && (
          <LiveConversation config={config} onEnd={handleEnd} />
        )}

        {state === SessionState.EVALUATION && config && (
          <EvaluationView history={history} config={config} onReset={handleReset} />
        )}
      </main>

      <footer className="py-6 px-6 text-center text-slate-400 text-sm border-t border-slate-100">
        Bandhan Life
      </footer>
    </div>
  );
};

export default App;
