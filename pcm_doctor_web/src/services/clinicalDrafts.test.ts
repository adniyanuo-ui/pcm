import { describe, expect, it } from 'vitest'
import { displayConfirmations, prescriptionText } from './clinicalDrafts'

describe('compact workbench compatibility', () => {
  it('requires both old intake stages before showing the combined step as confirmed', () => {
    expect(displayConfirmations([true, false, false, false, false])).toEqual([false, false, false, false])
    expect(displayConfirmations([true, true, true, false, false])).toEqual([true, true, false, false])
  })
  it('keeps free text verbatim and includes all legacy prescription information', () => {
    expect(prescriptionText({ text: '医师药甲 1g\n共1剂' })).toBe('医师药甲 1g\n共1剂')
    expect(prescriptionText({ items: [{ herb: '药甲', dose: '1g', note: '备注' }], count: 2,
      usage: '测试用法', advice: '测试医嘱', adjustment_note: '测试加减' })).toBe('药甲 1g 备注\n\n共2剂。测试用法\n\n测试医嘱\n\n测试加减')
    expect(prescriptionText(null)).toBe('')
  })
})
