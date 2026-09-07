import { apiRequest } from './client'
import type { FormulaDoseConversion, FormulaDoseReference, RagApiCandidate, RagRetrieval } from '../types/consultation'
import type { VoiceSummary } from './voice'

export interface Patient { name: string; sex: string; age: number | null; allergy: string }
export type Prescription = { text: string } | { items: { herb: string; dose: string; note: string }[]; count: number; usage: string; advice: string; adjustment_note?: string }
export interface Encounter {
  id: number; patient_id: number; version: number; updated_at: string
  state: {
    patient: Patient; transcript: string; original_transcript: string; examinations: Record<string, string> | null
    analysis: Record<string, string> | null; candidates: RagApiCandidate[]; selected_id: string
    retrieval?: RagRetrieval | null; clinical_profile?: Record<string, string[]> | null
    selected_ids?: string[]; formula_references?: FormulaDoseReference[]
    prescription: Prescription | null; record: string; confirmed: boolean[]
    voice_summary?: VoiceSummary | null
    models: { stage: string; requested: string; actual: string; time: string }[]
  }
}
export interface VisitSummary { id: number; patient_id: number; patient: Patient; confirmed: boolean; updated_at: string }
const base = '/api/cms/llm/encounters/'
export const listVisits = () => apiRequest<VisitSummary[]>(base)
export const getVisit = (id: number) => apiRequest<Encounter>(base + id + '/')
export const createVisit = (patient: Patient, patientId?: number) => apiRequest<Encounter>(base, {
  method: 'POST', body: JSON.stringify(patientId ? { patient_id: patientId } : { patient }),
})
export const transition = (visit: Encounter, action: string, data: object = {}) => apiRequest<Encounter>(base + visit.id + '/transition/', {
  method: 'POST', body: JSON.stringify({ version: visit.version, action, data }),
}, 120_000)
export const getHistory = (id: number) => apiRequest<{ version: number; action: string; state: Encounter['state']; created_at: string }[]>(base + id + '/history/')
export const getFormulaReference = (id: number, candidateId: string, conversion?: FormulaDoseConversion) =>
  apiRequest<FormulaDoseReference>(base + id + '/formula_reference/', {
    method: 'POST', body: JSON.stringify({ id: candidateId, ...(conversion ? { conversion } : {}) }),
  })
