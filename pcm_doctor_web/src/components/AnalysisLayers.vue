<script setup lang="ts">
const model = defineModel<Record<string, string>>({ required: true })
defineEmits<{ changed: [] }>()
const layers = [
  { title: '辨病因、病位、病性，察病势', fields: [['cause', '病因'], ['location', '病位'], ['nature', '病性'], ['trend', '病势']] },
  { title: '推演、归纳病机，确定证型', fields: [['mechanism', '病机'], ['syndrome', '证型']] },
  { title: '确立治则、治法', fields: [['principle', '治则'], ['treatment', '治法']] },
]
</script>
<template>
  <div class="analysis-layers">
    <section v-for="(layer, i) in layers" :key="i" class="analysis-layer">
      <h3>{{ i + 1 }} · {{ layer.title }}</h3>
      <div class="analysis-fields"><label v-for="[key, label] in layer.fields" :key="key">{{ label }}<textarea v-model="model[key]" :aria-label="label" :rows="i === 1 ? 3 : 2" @input="$emit('changed')"></textarea></label></div>
    </section>
    <details class="analysis-evidence"><summary>支持证据与不确定性（按需展开）</summary>
      <label>证据摘要<textarea v-model="model.evidence" aria-label="支持证据与不确定性" @input="$emit('changed')"></textarea></label>
    </details>
  </div>
</template>
<style scoped>
.analysis-layer { margin: 20px 0; }.analysis-layer h3 { font-size: 14px; font-weight: 500; color: #526e5c; margin: 0 0 10px; }
.analysis-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 18px; }label { display: grid; gap: 6px; font-size: 13px; color: #68796e; }
textarea { width: 100%; resize: vertical; padding: 10px 12px; border: 1px solid #d9e2dc; border-radius: 8px; font: inherit; font-size: 20px; line-height: 1.65; color: #223d2e; background: white; }
.analysis-evidence { margin: 18px 0; font-size: 13px; color: #68796e; }.analysis-evidence label { margin-top: 12px; }summary { cursor: pointer; }@media(max-width: 700px) { .analysis-fields { grid-template-columns: 1fr; } }
</style>
