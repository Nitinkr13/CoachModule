
export interface TrainingSessionConfig {
  sessionId: string;
  personaId: string;
  personaName: string;
  scenarioId: string;
  scenarioName: string;
}

export enum SessionState {
  SETUP = 'SETUP',
  ACTIVE = 'ACTIVE',
  EVALUATION = 'EVALUATION'
}

export interface TranscriptionItem {
  speaker: 'user' | 'model';
  text: string;
  timestamp: number;
}

export interface DocumentSummary {
  id: string;
  name: string;
  source: string;
}

export interface PersonaSummary {
  id: string;
  name: string;
  description: string;
  behavior: string;
  cmTreatment: string;
  impact: string;
}

export interface ScenarioSummary {
  id: string;
  name: string;
  goal: string;
}

export interface EvaluationRubricItem {
  id: string;
  label: string;
  score: number;
  notes: string;
}

export interface EvaluationReportSubSection {
  framework: string;
  criteria: string;
  what_went_well: string;
  what_could_have_been_better: string;
}

export interface EvaluationReportSection {
  observation_area: string;
  criteria?: string[];
  sub_sections?: EvaluationReportSubSection[];
  what_went_well?: string;
  what_could_have_been_better?: string;
  rating?: number | null;
  comments?: string;
  overall_comments?: string;
}

export interface EvaluationReportOverallSummary {
  strengths: string;
  development_areas: string;
  recommended_next_steps: string;
  overall_rating: number | null;
}

export interface EvaluationReportTemplate {
  title: string;
  sections: EvaluationReportSection[];
  overall_summary: EvaluationReportOverallSummary;
}

export interface EvaluationReport {
  evaluation_report_template: EvaluationReportTemplate;
}
