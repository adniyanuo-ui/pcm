export type VisitStage = 'intake' | 'examination' | 'analysis' | 'formula' | 'record'

export interface StageDefinition {
  key: VisitStage
  shortLabel: string
  label: string
  hint: string
}

export interface TranscriptLine {
  id: number
  role: '医生' | '患者'
  time: string
  content: string
}

export interface ExaminationSection {
  key: '望' | '闻' | '问' | '切'
  title: string
  value: string
  placeholder: string
  source: string
}

export interface AnalysisItem {
  label: string
  value: string
  evidence: string
}

export interface FormulaCandidate {
  id: string
  name: string
  source: string
  match: number
  summary: string
  supports: string[]
  cautions: string[]
  composition: string
  original: string
  citation: {
    volume: number
    pdfPage: number
    bookPage: number
  }
}

export interface PrescriptionItem {
  id: number
  herb: string
  dose: string
  note: string
}
