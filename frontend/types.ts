
export interface TrainingSessionConfig {
  role: string;
  contextText: string;
  fileName: string;
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
