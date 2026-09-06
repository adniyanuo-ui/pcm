import { describe, expect, it } from 'vitest'
import { toFormulaCandidate } from './rag'
import type { RagApiCandidate } from '../types/consultation'

describe('complete formula source', () => {
  it('retains full fields and all citation pages for the detail dialog', () => {
    const raw: RagApiCandidate = { id: 'test', name: '虚构方', retrieval_score: 1, evidence_coverage: 10,
      match_reasons: [], matched_terms: {}, syndrome_index_hits: [], truncated_fields: [], quality_flags: [],
      fields: { '组成': '原文组成', '主治': '原文主治', '用法': '原文用法', '加减': '原文加减', '宜忌': '原文宜忌' },
      source: { volume: 1, pdf_pages: [10, 11], book_pages: [2, 3], citation: '第1册，PDF第10、11页，书内第2、3页' } }
    const card = toFormulaCandidate(raw)
    expect(card.fields).toEqual(raw.fields)
    expect(card.fullCitation).toBe(raw.source.citation)
  })
})
