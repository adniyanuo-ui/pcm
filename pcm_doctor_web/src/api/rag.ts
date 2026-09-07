import type {
  FormulaCandidate,
  RagApiCandidate,
  RagSearchPayload,
  RagSearchResult,
} from '../types/consultation'
import { apiRequest } from './client'

export async function searchFormulas(payload: RagSearchPayload): Promise<RagSearchResult> {
  return apiRequest<RagSearchResult>(
    '/api/cms/llm/rag/search/',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  )
}

function firstPage(pages: number[]): number {
  return pages.length ? pages[0] : 0
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))]
}

export function toFormulaCandidate(candidate: RagApiCandidate): FormulaCandidate {
  const reverse = candidate.reverse_validation
  const supports = unique([
    ...(reverse?.matched_treatment || []),
    ...(reverse?.matched_pathogenesis || []),
    ...(reverse?.matched_clinical_evidence || []),
    ...Object.values(candidate.matched_terms).flat(),
  ]).slice(0, 9)
  const source = candidate.fields['方源'] || candidate.source.citation
  const action = candidate.fields['功用'] || ''
  const indication = candidate.fields['主治'] || candidate.fields['正文及其他'] || ''
  const summary = action || (indication.length > 90 ? indication.slice(0, 90) + '…' : indication)
  const cautions = reverse?.cautions?.length
    ? reverse.cautions
    : candidate.quality_flags.length
    ? ['该条目带质量标记：' + candidate.quality_flags.join('、')]
    : ['召回阶段尚未生成不匹配点，需结合完整四诊复核']

  return {
    id: candidate.id,
    name: candidate.name,
    source,
    match: candidate.evidence_coverage,
    summary,
    supports: supports.length ? supports : candidate.match_reasons.slice(0, 4),
    cautions,
    composition: candidate.dose_reference?.text || candidate.fields['组成'] || '辞典本条未提供组成字段',
    original: indication || '辞典本条未提供主治字段',
    fields: candidate.fields,
    truncatedFields: candidate.truncated_fields,
    fullCitation: candidate.source.citation,
    doseReference: candidate.dose_reference,
    selectionLayer: candidate.selection_layer,
    treatmentFamily: candidate.treatment_family ? {
      id: candidate.treatment_family.id,
      name: candidate.treatment_family.name,
      parentFormulas: candidate.treatment_family.parent_formulas,
    } : undefined,
    reverseValidation: reverse ? {
      consistency: reverse.consistency,
      compositionSource: reverse.composition_source,
      formulaMeaning: reverse.formula_meaning,
      actualTreatment: reverse.actual_treatment,
      actualIndications: reverse.actual_indications,
      matchedTreatment: reverse.matched_treatment,
      matchedPathogenesis: reverse.matched_pathogenesis,
      matchedClinicalEvidence: reverse.matched_clinical_evidence,
      cautions: reverse.cautions,
    } : undefined,
    citation: {
      volume: candidate.source.volume,
      pdfPage: firstPage(candidate.source.pdf_pages),
      bookPage: firstPage(candidate.source.book_pages),
    },
  }
}
