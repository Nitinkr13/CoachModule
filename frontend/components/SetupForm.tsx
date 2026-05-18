import React, { useEffect, useState } from 'react';
import { PersonaSummary, ScenarioSummary, TrainingSessionConfig } from '../types';

interface SetupFormProps {
  onStart: (config: TrainingSessionConfig) => void;
}

const SetupForm: React.FC<SetupFormProps> = ({ onStart }) => {
  const [personas, setPersonas] = useState<PersonaSummary[]>([]);
  const [selectedPersonaId, setSelectedPersonaId] = useState('');
  const [personasError, setPersonasError] = useState('');
  const [loadingPersonas, setLoadingPersonas] = useState(true);
  const [loading, setLoading] = useState(false);
  const [micPermission, setMicPermission] = useState<'prompt' | 'granted' | 'denied'>('prompt');

  useEffect(() => {
    navigator.permissions.query({ name: 'microphone' as any }).then(result => {
      setMicPermission(result.state as any);
      result.onchange = () => setMicPermission(result.state as any);
    });
  }, []);

  useEffect(() => {
    const loadPersonas = async () => {
      const apiBase = import.meta.env.VITE_API_BASE_URL;
      if (!apiBase) {
        setPersonasError('Missing VITE_API_BASE_URL');
        setLoadingPersonas(false);
        return;
      }

      try {
        const response = await fetch(`${apiBase}/api/personas`);
        if (!response.ok) {
          throw new Error(`Failed to load personas: ${response.status}`);
        }

        const data = await response.json();
        const items = (data.personas || []) as PersonaSummary[];
        setPersonas(items);
        if (items.length > 0 && !selectedPersonaId) {
          setSelectedPersonaId(items[0].id);
        }
      } catch (err) {
        console.error(err);
        setPersonasError('Failed to load personas.');
      } finally {
        setLoadingPersonas(false);
      }
    };

    loadPersonas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const requestMic = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      setMicPermission('granted');
    } catch (err) {
      setMicPermission('denied');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (micPermission !== 'granted') {
      alert('Please enable microphone access to start the session.');
      return;
    }

    if (!selectedPersonaId) {
      alert('Please select a persona to start the session.');
      return;
    }

    setLoading(true);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL;
      if (!apiBase) {
        throw new Error('Missing VITE_API_BASE_URL');
      }

      const sessionResponse = await fetch(`${apiBase}/api/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          personaId: selectedPersonaId,
        }),
      });

      if (!sessionResponse.ok) {
        throw new Error(`Session start failed: ${sessionResponse.status}`);
      }

      const sessionData = await sessionResponse.json();
      const persona = sessionData.persona as PersonaSummary;
      const scenario = sessionData.scenario as ScenarioSummary;

      onStart({
        sessionId: sessionData.sessionId,
        personaId: persona.id,
        personaName: persona.name,
        scenarioId: scenario.id,
        scenarioName: scenario.name,
      });

    } catch (err) {
      console.error(err);
      alert('Failed to start session. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const selectedPersona = personas.find(persona => persona.id === selectedPersonaId);

  return (
    <div className="max-w-2xl mx-auto p-8 bg-white rounded-3xl shadow-xl border border-slate-100">
      <div className="flex items-center gap-4 mb-8">
        <div className="bg-indigo-600 p-3 rounded-2xl shadow-lg shadow-indigo-200">
          <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
        </div>
        <div>
          <h2 className="text-3xl font-bold text-slate-800">Session Setup</h2>
          <p className="text-slate-500">Select the RM persona for this coaching simulation</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="space-y-4">
          <label className="block text-sm font-bold text-slate-700 uppercase tracking-wider">RM Persona</label>
          <div className="space-y-3">
            {loadingPersonas ? (
              <div className="text-sm text-slate-500 bg-slate-50 border border-slate-100 rounded-2xl p-4">
                Loading personas...
              </div>
            ) : personasError ? (
              <div className="text-sm text-red-500 bg-red-50 border border-red-100 rounded-2xl p-4">
                {personasError}
              </div>
            ) : personas.length === 0 ? (
              <div className="text-sm text-slate-500 bg-slate-50 border border-slate-100 rounded-2xl p-4">
                No personas configured.
              </div>
            ) : (
              <select
                value={selectedPersonaId}
                onChange={(e) => setSelectedPersonaId(e.target.value)}
                className="w-full px-4 py-4 rounded-2xl border-2 border-slate-100 focus:border-indigo-500 focus:ring-0 outline-none transition-all text-sm font-medium"
              >
                {personas.map((persona) => (
                  <option key={persona.id} value={persona.id}>
                    {persona.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {selectedPersona && (
            <div className="p-5 bg-slate-50 rounded-2xl border border-slate-100 space-y-3">
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Persona description</p>
                <p className="text-sm text-slate-700 mt-1">{selectedPersona.description}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Behavior</p>
                <p className="text-sm text-slate-700 mt-1">{selectedPersona.behavior}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">CM treatment guidance</p>
                <p className="text-sm text-slate-700 mt-1">{selectedPersona.cmTreatment}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Business impact</p>
                <p className="text-sm text-slate-700 mt-1">{selectedPersona.impact}</p>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${micPermission === 'granted' ? 'bg-green-500' : 'bg-red-400 animate-pulse'}`}></div>
            <span className="text-sm font-semibold text-slate-700">Microphone Status</span>
          </div>
          {micPermission !== 'granted' ? (
            <button
              type="button"
              onClick={requestMic}
              className="text-xs bg-white border border-slate-200 hover:bg-slate-100 px-4 py-2 rounded-xl font-bold transition-all"
            >
              Enable Mic
            </button>
          ) : (
            <span className="text-xs text-green-600 font-bold uppercase">Ready</span>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || micPermission !== 'granted'}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white font-bold py-5 rounded-2xl shadow-xl shadow-indigo-100 transition-all flex items-center justify-center gap-3 text-lg"
        >
          {loading ? (
            <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : (
            <>
              <span>Begin Training Session</span>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </>
          )}
        </button>
      </form>
    </div>
  );
};

export default SetupForm;