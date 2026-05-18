import React, { useEffect, useState } from 'react';
import { DocumentSummary, TrainingSessionConfig } from '../types';
 
interface SetupFormProps {
  onStart: (config: TrainingSessionConfig) => void;
}
 
const SetupForm: React.FC<SetupFormProps> = ({ onStart }) => {
  const [role, setRole] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentsError, setDocumentsError] = useState('');
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [loading, setLoading] = useState(false);
  const [micPermission, setMicPermission] = useState<'prompt' | 'granted' | 'denied'>('prompt');
 
  useEffect(() => {
    navigator.permissions.query({ name: 'microphone' as any }).then(result => {
      setMicPermission(result.state as any);
      result.onchange = () => setMicPermission(result.state as any);
    });
  }, []);

  useEffect(() => {
    const loadDocuments = async () => {
      const apiBase = import.meta.env.VITE_API_BASE_URL;
      if (!apiBase) {
        setDocumentsError('Missing VITE_API_BASE_URL');
        setLoadingDocuments(false);
        return;
      }

      try {
        const response = await fetch(`${apiBase}/api/documents`);
        if (!response.ok) {
          throw new Error(`Failed to load documents: ${response.status}`);
        }

        const data = await response.json();
        const docs = (data.documents || []) as DocumentSummary[];
        setDocuments(docs);
        if (docs.length > 0 && !selectedDocumentId) {
          setSelectedDocumentId(docs[0].id);
        }
      } catch (err) {
        console.error(err);
        setDocumentsError('Failed to load documents.');
      } finally {
        setLoadingDocuments(false);
      }
    };

    loadDocuments();
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
 
    setLoading(true);
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL;
      if (!apiBase) {
        throw new Error('Missing VITE_API_BASE_URL');
      }

      let documentId = selectedDocumentId;

      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        const uploadResponse = await fetch(`${apiBase}/api/documents/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!uploadResponse.ok) {
          throw new Error(`Upload failed: ${uploadResponse.status}`);
        }

        const uploadData = await uploadResponse.json();
        documentId = uploadData.document?.id || '';
      }

      if (!documentId) {
        alert('No documents available.');
        setLoading(false);
        return;
      }

      const sessionResponse = await fetch(`${apiBase}/api/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role,
          documentId,
        }),
      });

      if (!sessionResponse.ok) {
        throw new Error(`Session start failed: ${sessionResponse.status}`);
      }

      const sessionData = await sessionResponse.json();
      const document = sessionData.document as DocumentSummary;

      onStart({
        role,
        sessionId: sessionData.sessionId,
        documentId: document.id,
        documentName: document.name,
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
            {loadingDocuments ? (
              <div className="col-span-1 md:col-span-2 text-sm text-slate-500 bg-slate-50 border border-slate-100 rounded-2xl p-4">
                Loading documents...
              </div>
            ) : documentsError ? (
              <div className="col-span-1 md:col-span-2 text-sm text-red-500 bg-red-50 border border-red-100 rounded-2xl p-4">
                {documentsError}
              </div>
            ) : documents.length === 0 ? (
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
                onChange={(e) => { setFile(e.target.files?.[0] || null); setSelectedDocumentId(''); }}
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

            {documents.length > 0 && (
              <div className="col-span-1 md:col-span-2 space-y-2">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Preset Document</label>
                <select
                  value={selectedDocumentId}
                  onChange={(e) => setSelectedDocumentId(e.target.value)}
                  disabled={!!file}
                  className="w-full px-4 py-3 rounded-2xl border-2 border-slate-100 focus:border-indigo-500 focus:ring-0 outline-none transition-all text-sm font-medium disabled:bg-slate-50"
                >
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.name}
                    </option>
                  ))}
                </select>
                {file && (
                  <p className="text-xs text-slate-400">Uploaded file will be used instead of preset.</p>
                )}
              </div>
            )}
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