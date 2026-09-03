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

export interface RagSearchPayload {
  free_text?: string
  symptoms?: string[]
  tongue?: string[]
  pulse?: string[]
  complexion?: string[]
  voice?: string[]
  mechanisms?: string[]
  syndromes?: string[]
  treatments?: string[]
  formula_names?: string[]
  doctor_notes?: string[]
  top_k?: number
}

export interface RagApiCandidate {
  id: string
  name: string
  retrieval_score: number
  evidence_coverage: number
  match_reasons: string[]
  matched_terms: Record<string, string[]>
  syndrome_index_hits: Array<Record<string, unknown>>
  fields: Record<string, string>
  truncated_fields: string[]
  source: {
    volume: number
    pdf_pages: number[]
    book_pages: number[]
    citation: string
  }
  quality_flags: string[]
}

export interface RagSearchResult {
  query: RagSearchPayload
  candidates: RagApiCandidate[]
  retrieval: {
    candidate_pool: number
    returned: number
    score_note: string
  }
}
