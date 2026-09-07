export type VisitStage = 'intake' | 'examination' | 'analysis' | 'formula' | 'record'

export interface StageDefinition {
  key: VisitStage
  shortLabel: string
  label: string
  hint: string
}

export interface TranscriptLine {
  id: number
  role: '医生' | '患者' | '对话'
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
  fields?: Record<string, string>
  truncatedFields?: string[]
  fullCitation?: string
  doseReference?: FormulaDoseReference
  selectionLayer?: 'core' | 'archive'
  treatmentFamily?: {
    id: string
    name: string
    parentFormulas: string[]
  }
  reverseValidation?: {
    consistency: string
    compositionSource: string
    formulaMeaning: string
    actualTreatment: string
    actualIndications: string
    matchedTreatment: string[]
    matchedPathogenesis: string[]
    matchedClinicalEvidence: string[]
    cautions: string[]
  }
  citation: {
    volume: number
    pdfPage: number
    bookPage: number
  }
}

export interface FormulaDoseConversion {
  basis: string
  grams_per_unit: Record<string, string>
  confirmed: true
}

export interface FormulaDoseReference {
  id: string
  name: string
  original: string
  text: string
  items: Array<{
    herb: string
    note: string
    dose: string
    quantities: Array<{ amount: string; unit: string }>
    grams: string | null
    display: string
  }>
  convertible_units: string[]
  conversion: FormulaDoseConversion | null
  warnings: string[]
  source: {
    volume: number
    pdf_pages: number[]
    book_pages: number[]
    citation: string
  }
  usage: string
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
  dose_reference?: FormulaDoseReference
  selection_layer?: 'core' | 'archive'
  treatment_family?: {
    id: string
    name: string
    parent_formulas: string[]
    review_status: string
  } | null
  reverse_validation?: {
    consistency: string
    composition_source: string
    formula_meaning: string
    actual_treatment: string
    actual_indications: string
    matched_treatment: string[]
    matched_pathogenesis: string[]
    matched_clinical_evidence: string[]
    treatment_ontology_supported: boolean
    unmatched_treatment_structures: string[]
    cautions: string[]
    facts_inferred_by_model: false
  }
}

export interface RagRetrieval {
  candidate_pool: number
  returned: number
  treatment_prototypes?: Array<{
    id: string
    name: string
    parent_formulas: string[]
    matched_treatments: string[]
    matched_pathogenesis: string[]
  }>
  gold_size?: number
  gold_ready?: boolean
  search_path?: string[]
  stopped_at?: 'clinical_profile' | 'core' | 'archive'
  fallback_used?: boolean
  fallback_reason?: string
  reverse_validation_rejected?: number
  validation_status?: 'clinical_profile_conflict' | 'consistent_candidates_found' | 'no_consistent_candidate'
  profile_conflicts?: string[]
  score_note: string
}

export interface RagSearchResult {
  query: RagSearchPayload
  candidates: RagApiCandidate[]
  retrieval: RagRetrieval
}
