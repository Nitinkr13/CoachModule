
import React, { useEffect, useState } from 'react';
import {
  EvaluationReport,
  EvaluationReportSection,
  EvaluationRubricItem,
  TranscriptionItem,
  TrainingSessionConfig
} from '../types';
import { marked } from 'marked';

interface EvaluationViewProps {
  history: TranscriptionItem[];
  config: TrainingSessionConfig;
  onReset: () => void;
}

const EvaluationView: React.FC<EvaluationViewProps> = ({ history, config, onReset }) => {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [impactFeedback, setImpactFeedback] = useState<string>('');
  const [fallbackHtml, setFallbackHtml] = useState<string>('');
  const [rubric, setRubric] = useState<EvaluationRubricItem[]>([]);
  const [overallScore, setOverallScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const generateFeedback = async () => {
      try {
        const apiBase = import.meta.env.VITE_API_BASE_URL;
        if (!apiBase) {
          throw new Error('Missing VITE_API_BASE_URL');
        }

        const response = await fetch(`${apiBase}/api/evaluation`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sessionId: config.sessionId,
          }),
        });

        if (!response.ok) {
          throw new Error(`Evaluation failed: ${response.status}`);
        }

        const data = await response.json();
        const reportData = (data.report || null) as EvaluationReport | null;
        const feedbackText = typeof data.feedback === 'string' ? data.feedback : '';
        const reportMarkdown = typeof data.reportMarkdown === 'string' ? data.reportMarkdown : '';
        const rubricItems = (data.rubric || []) as EvaluationRubricItem[];
        const scoreValue = typeof data.score === 'number' ? data.score : null;
        const fallbackText = reportMarkdown || feedbackText || "Failed to generate feedback.";
        const html = await marked.parse(fallbackText);

        setReport(reportData);
        setImpactFeedback(feedbackText);
        setFallbackHtml(html);
        setRubric(rubricItems);
        setOverallScore(scoreValue);
      } catch (err) {
        console.error(err);
        setFallbackHtml("<p>Error generating feedback. Please check your connection.</p>");
      } finally {
        setLoading(false);
      }
    };

    generateFeedback();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reportTemplate = report?.evaluation_report_template;

  const renderSectionDetails = (section: EvaluationReportSection) => {
    return (
      <div className="space-y-4">
        {section.criteria && section.criteria.length > 0 && (
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Criteria</p>
            <ul className="list-disc list-inside text-sm text-slate-600 mt-2 space-y-1">
              {section.criteria.map((item, idx) => (
                <li key={`${section.observation_area}-criteria-${idx}`}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {section.sub_sections && section.sub_sections.length > 0 && (
          <div className="space-y-4">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Structured approach</p>
            {section.sub_sections.map((sub, idx) => (
              <div key={`${section.observation_area}-sub-${idx}`} className="p-4 rounded-2xl border border-slate-100 bg-slate-50">
                <p className="text-sm font-bold text-slate-800">{sub.framework}</p>
                <p className="text-xs text-slate-500 mt-1">{sub.criteria}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                  <div>
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">What went well</p>
                    <p className="text-sm text-slate-700 mt-1">{sub.what_went_well || ' '}</p>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">What could have been better</p>
                    <p className="text-sm text-slate-700 mt-1">{sub.what_could_have_been_better || ' '}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {(section.what_went_well || section.what_could_have_been_better) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">What went well</p>
              <p className="text-sm text-slate-700 mt-1">{section.what_went_well || ' '}</p>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">What could have been better</p>
              <p className="text-sm text-slate-700 mt-1">{section.what_could_have_been_better || ' '}</p>
            </div>
          </div>
        )}

        {section.comments && (
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Comments</p>
            <p className="text-sm text-slate-700 mt-1">{section.comments}</p>
          </div>
        )}

        {section.overall_comments && (
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Overall comments</p>
            <p className="text-sm text-slate-700 mt-1">{section.overall_comments}</p>
          </div>
        )}

        {section.rating !== null && section.rating !== undefined && (
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Rating</p>
            <p className="text-sm text-slate-700 mt-1">{section.rating}</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-10 bg-white rounded-3xl shadow-2xl border border-slate-100">
      <div className="flex items-center justify-between mb-12 border-b pb-8">
        <div>
          <h2 className="text-4xl font-extrabold text-slate-900 mb-2">Performance Report</h2>
          <p className="text-slate-500 font-medium">Persona Session: <span className="text-indigo-600">{config.personaName}</span></p>
          <p className="text-slate-400 text-sm">Scenario: {config.scenarioName}</p>
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
        <div className="space-y-10">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 rounded-2xl border border-slate-100 bg-slate-50">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Overall score</p>
              <p className="text-3xl font-extrabold text-slate-900 mt-2">
                {overallScore !== null ? overallScore : 'N/A'}
              </p>
            </div>
            {rubric.map((item) => (
              <div key={item.id} className="p-5 rounded-2xl border border-slate-100 bg-white">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">{item.label}</p>
                <p className="text-2xl font-bold text-slate-900 mt-2">{item.score}</p>
                {item.notes && (
                  <p className="text-sm text-slate-500 mt-2">{item.notes}</p>
                )}
              </div>
            ))}
          </div>

          <div className="p-6 rounded-2xl border border-slate-100 bg-slate-50">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Impact-based feedback</p>
            <p className="text-base text-slate-800 mt-2">{impactFeedback || ' '}</p>
          </div>

          {reportTemplate ? (
            <div className="space-y-6">
              <div>
                <h3 className="text-2xl font-bold text-slate-900">{reportTemplate.title}</h3>
              </div>
              {reportTemplate.sections.map((section, idx) => (
                <div key={`${section.observation_area}-${idx}`} className="p-6 rounded-3xl border border-slate-100 bg-white shadow-sm">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-bold text-slate-800">{section.observation_area}</h4>
                    {section.rating !== null && section.rating !== undefined && (
                      <span className="text-sm font-semibold text-slate-500">Rating: {section.rating}</span>
                    )}
                  </div>
                  <div className="mt-4">
                    {renderSectionDetails(section)}
                  </div>
                </div>
              ))}

              <div className="p-6 rounded-3xl border border-slate-100 bg-slate-50">
                <h4 className="text-lg font-bold text-slate-800">Overall summary</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  <div>
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Strengths</p>
                    <p className="text-sm text-slate-700 mt-1">{reportTemplate.overall_summary.strengths || ' '}</p>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Development areas</p>
                    <p className="text-sm text-slate-700 mt-1">{reportTemplate.overall_summary.development_areas || ' '}</p>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Recommended next steps</p>
                    <p className="text-sm text-slate-700 mt-1">{reportTemplate.overall_summary.recommended_next_steps || ' '}</p>
                  </div>
                  {reportTemplate.overall_summary.overall_rating !== null && reportTemplate.overall_summary.overall_rating !== undefined && (
                    <div>
                      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Final score</p>
                      <p className="text-sm text-slate-700 mt-1">{reportTemplate.overall_summary.overall_rating}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div
              className="prose prose-slate max-w-none prose-headings:text-slate-900 prose-strong:text-indigo-600"
              dangerouslySetInnerHTML={{ __html: fallbackHtml }}
            />
          )}
        </div>
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
