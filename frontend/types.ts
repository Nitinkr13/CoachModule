
export interface TrainingSessionConfig {
  role: string;
  sessionId: string;
  documentId: string;
  documentName: string;
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
