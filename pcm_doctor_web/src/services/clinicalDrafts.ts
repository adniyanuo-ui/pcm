import type { Prescription } from '../api/encounters'

export function prescriptionText(value: Prescription | null): string {
  if (!value) return ''
  if ('text' in value) return value.text
  return [value.items.map(i => [i.herb, i.dose, i.note].filter(Boolean).join(' ')).join('\n'),
    `共${value.count}剂。${value.usage}`, value.advice, value.adjustment_note].filter(Boolean).join('\n\n')
}

export function displayConfirmations(confirmed: boolean[]): boolean[] {
  return [confirmed[0] && confirmed[1], ...confirmed.slice(2)]
}
