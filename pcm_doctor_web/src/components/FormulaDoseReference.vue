<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getFormulaReference } from '../api/encounters'
import type { FormulaDoseConversion, FormulaDoseReference } from '../types/consultation'

const props = defineProps<{
  encounterId: number
  reference: FormulaDoseReference
  disabled?: boolean
}>()
const emit = defineEmits<{ converted: [conversion: FormulaDoseConversion] }>()
const current = ref(props.reference)
const factors = ref<Record<string, string>>({})
const basis = ref('')
const busy = ref(false)
const error = ref('')

watch(() => props.reference, value => {
  current.value = value
  factors.value = { ...(value.conversion?.grams_per_unit || {}) }
  basis.value = value.conversion?.basis || ''
})

const ready = computed(() => current.value.convertible_units.length > 0
  && current.value.convertible_units.every(unit => /^\d{1,6}(?:\.\d{1,6})?$/.test(factors.value[unit] || '') && Number(factors.value[unit]) > 0)
  && basis.value.trim().length > 0)

async function convert() {
  if (!ready.value || busy.value || props.disabled) return
  const conversion: FormulaDoseConversion = {
    basis: basis.value.trim(),
    grams_per_unit: Object.fromEntries(current.value.convertible_units.map(unit => [unit, factors.value[unit]])),
    confirmed: true,
  }
  busy.value = true; error.value = ''
  try {
    current.value = await getFormulaReference(props.encounterId, current.value.id, conversion)
    emit('converted', conversion)
  } catch (e) { error.value = e instanceof Error ? e.message : '换算失败，请核对后重试' }
  finally { busy.value = false }
}
</script>

<template>
  <details v-if="current.convertible_units.length" class="dose-conversion" @click.stop>
    <summary>古代重量换算（按需核定）</summary>
    <p>不同历史衡制不可统一套算。此处只换算原方重量，不代表当前患者的建议日服量。</p>
    <div class="conversion-fields">
      <label v-for="unit in current.convertible_units" :key="unit">1{{ unit }} =
        <input v-model.trim="factors[unit]" inputmode="decimal" maxlength="13" :disabled="disabled || busy" :aria-label="`1${unit}对应克数`" /> g
      </label>
      <label class="conversion-basis">换算依据
        <input v-model.trim="basis" maxlength="500" :disabled="disabled || busy" placeholder="填写已核定的年代、文献或诊所换算表" />
      </label>
    </div>
    <button type="button" :disabled="!ready || disabled || busy" @click.stop="convert">{{ busy ? '正在换算…' : '按已核定依据换算为 g' }}</button>
    <p v-if="error" class="conversion-error" role="alert">{{ error }}</p>
    <p v-if="current.conversion" class="converted-result"><strong>换算后原方参考：</strong>{{ current.text }}</p>
  </details>
</template>

<style scoped>
.dose-conversion { margin-top: 10px; color: #64756b; font-size: 12px; }
.dose-conversion summary { cursor: pointer; color: #37644e; }
.dose-conversion p { margin: 8px 0; line-height: 1.6; }
.conversion-fields { display: flex; flex-wrap: wrap; align-items: end; gap: 10px; margin: 10px 0; }
.conversion-fields label { display: flex; align-items: center; gap: 6px; }
.conversion-fields input { width: 88px; padding: 7px 9px; border: 1px solid #ccd8d0; border-radius: 6px; }
.conversion-fields .conversion-basis { flex: 1 1 300px; }
.conversion-fields .conversion-basis input { flex: 1; min-width: 180px; }
.dose-conversion button { padding: 7px 10px; border: 1px solid #aac3b6; border-radius: 6px; color: #285f43; background: #f4faf7; cursor: pointer; }
.dose-conversion button:disabled { opacity: .5; cursor: not-allowed; }
.conversion-error { color: #9a3d20; }.converted-result { color: #284f3b; }
</style>
