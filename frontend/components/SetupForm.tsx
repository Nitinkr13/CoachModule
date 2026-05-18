import React, { useState, useEffect, useMemo } from 'react';
import { TrainingSessionConfig } from '../types';
import { readFileAsText } from '../utils/pdf';
 
interface SetupFormProps {
  onStart: (config: TrainingSessionConfig) => void;
}
 
const presetModules = import.meta.glob('../docs/*.txt', { as: 'raw', eager: true });
 
const SetupForm: React.FC<SetupFormProps> = ({ onStart }) => {
  const [role, setRole] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [micPermission, setMicPermission] = useState<'prompt' | 'granted' | 'denied'>('prompt');
 
  const presetFiles = useMemo(() => {
    return Object.entries(presetModules).map(([path, content]) => {
      const name = path.split('/').pop() || 'Unknown.txt';
      return { name, content: content as string };
    });
  }, []);
 
  useEffect(() => {
    navigator.permissions.query({ name: 'microphone' as any }).then(result => {
      setMicPermission(result.state as any);
      result.onchange = () => setMicPermission(result.state as any);
    });
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
 
    setLoading(true);
    try {
      let text = '';
      let fileName = '';

      if (file) {
        text = await readFileAsText(file);
        fileName = file.name;
      } else {
        // If no file uploaded, use selected preset or default to first preset
        let preset = null;

        if (selectedPreset) {
          preset = presetFiles.find(p => p.name === selectedPreset);
        }

        // If no preset selected, use first document as default
        if (!preset && presetFiles.length > 0) {
          preset = presetFiles[0];
        }

        if (!preset) {
          alert('No documents available.');
          setLoading(false);
          return;
        }

        text = preset.content || '';
        fileName = preset.name || '';
      }

      onStart({
        role,
        contextText: text,
        fileName: fileName
      });

    } catch (err) {
      console.error(err);
      alert('Failed to process context. Please try again.');
    } finally {
      setLoading(false);
    }
  };
 
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
          <p className="text-slate-500">Prepare your AI Trainer persona and context</p>
        </div>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="space-y-4">
          <label className="block text-sm font-bold text-slate-700 uppercase tracking-wider">AI Persona (Character)</label>
          <div className="relative">
            <input
              type="text"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-5 py-4 rounded-2xl border-2 border-slate-100 focus:border-indigo-500 focus:ring-0 outline-none transition-all text-lg font-medium"
              placeholder="Add Customer Profile."
              required
            />
            <p className="mt-2 text-xs text-slate-400">The AI will strictly inhabit this character throughout the conversation.</p>
          </div>
        </div>
 
        <div className="space-y-4">
          <label className="block text-sm font-bold text-slate-700 uppercase tracking-wider">Document Upload</label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {presetFiles.length === 0 ? (
              <div className="col-span-1 md:col-span-2 text-sm text-slate-500 bg-slate-50 border border-slate-100 rounded-2xl p-4">
                Add txt file here.
              </div>
            ) : null}
            {file && (
              <div className="text-left p-4 rounded-2xl border-2 border-indigo-500 bg-indigo-50">
                <div className="font-bold text-slate-800 text-sm mb-1">
                  {file.name}
                </div>
                <div className="text-xs text-slate-500">
                  File uploaded successfully
                </div>
              </div>
            )}
            
            <div className="relative col-span-1 md:col-span-2">
              <input
                type="file"
                accept=".pdf,.txt"
                onChange={(e) => { setFile(e.target.files?.[0] || null); setSelectedPreset(null); }}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div className={`p-4 rounded-2xl border-2 border-dashed transition-all flex items-center gap-3 ${
                file ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200 hover:border-indigo-300'
              }`}>
                <div className="p-2 bg-slate-100 rounded-lg text-slate-500">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-slate-600">
                  {file ? file.name : "Upload Product Text File"}
                </span>
              </div>
            </div>
          </div>
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