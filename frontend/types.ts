
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
