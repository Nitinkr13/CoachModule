
import React, { useEffect, useState } from 'react';
import { TranscriptionItem, TrainingSessionConfig } from '../types';
import { marked } from 'marked';

interface EvaluationViewProps {
  history: TranscriptionItem[];
  config: TrainingSessionConfig;
  onReset: () => void;
}

const EvaluationView: React.FC<EvaluationViewProps> = ({ history, config, onReset }) => {
  const [feedbackHtml, setFeedbackHtml] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const generateFeedback = async () => {
      if (history.length === 0) {
        setFeedbackHtml("<p>No conversation data available for evaluation.</p>");
        setLoading(false);
        return;
      }

      try {
        const apiBase = import.meta.env.VITE_API_BASE_URL;
        if (!apiBase) {
          throw new Error('Missing VITE_API_BASE_URL');
        }

        const response = await fetch(`${apiBase}/api/evaluation`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            role: config.role,
            fileName: config.fileName,
            history: history.map(item => ({
              speaker: item.speaker,
              text: item.text,
            })),
          }),
        });

        if (!response.ok) {
          throw new Error(`Evaluation failed: ${response.status}`);
        }

        const data = await response.json();
        const rawText = data.feedback || "Failed to generate feedback.";
        const html = await marked.parse(rawText);
        setFeedbackHtml(html);
      } catch (err) {
        console.error(err);
        setFeedbackHtml("<p>Error generating feedback. Please check your connection.</p>");
      } finally {
        setLoading(false);
      }
    };

    generateFeedback();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-4xl mx-auto p-10 bg-white rounded-3xl shadow-2xl border border-slate-100">
      <div className="flex items-center justify-between mb-12 border-b pb-8">
        <div>
          <h2 className="text-4xl font-extrabold text-slate-900 mb-2">Performance Report</h2>
          <p className="text-slate-500 font-medium">Character Session: <span className="text-indigo-600">{config.role}</span></p>
        </div>
        <button
          onClick={onReset}
          className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold px-6 py-3 rounded-2xl transition-all flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          New Session
        </button>
      </div>

      {loading ? (
        <div className="space-y-8 animate-pulse">
          <div className="h-8 bg-slate-100 rounded-xl w-1/3"></div>
          <div className="space-y-3">
            <div className="h-4 bg-slate-50 rounded w-full"></div>
            <div className="h-4 bg-slate-50 rounded w-full"></div>
            <div className="h-4 bg-slate-50 rounded w-3/4"></div>
          </div>
          <div className="h-8 bg-slate-100 rounded-xl w-1/4 pt-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-slate-50 rounded w-full"></div>
            <div className="h-4 bg-slate-50 rounded w-5/6"></div>
          </div>
          <div className="h-40 bg-slate-50 rounded-2xl mt-8"></div>
        </div>
      ) : (
        <div 
          className="prose prose-slate max-w-none prose-headings:text-slate-900 prose-strong:text-indigo-600"
          dangerouslySetInnerHTML={{ __html: feedbackHtml }}
        />
      )}

      <div className="mt-16 pt-10 border-t border-slate-100 flex flex-col md:flex-row items-center gap-6">
        <button
          onClick={onReset}
          className="flex-1 w-full bg-slate-900 text-white py-5 rounded-2xl font-bold hover:bg-slate-800 shadow-xl shadow-slate-200 transition-all text-lg"
        >
          Start Another Training Session
        </button>
        <button
          onClick={() => window.print()}
          className="w-full md:w-auto px-10 bg-white border-2 border-slate-100 text-slate-700 py-5 rounded-2xl font-bold hover:border-slate-300 transition-all flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
          Save Report
        </button>
      </div>
    </div>
  );
};

export default EvaluationView;
