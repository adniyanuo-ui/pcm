<script setup lang="ts">
import { CircleCheck, RefreshRight } from '@element-plus/icons-vue'
import type { AnalysisItem } from '../types/consultation'

const mechanism = defineModel<string>('mechanism', { required: true })
const treatment = defineModel<string>('treatment', { required: true })

defineProps<{
  items: AnalysisItem[]
  stale: boolean
}>()

defineEmits<{
  changed: []
  refresh: []
  confirm: []
}>()
</script>

<template>
  <section class="content-section">
    <div class="section-heading-row">
      <div>
        <span class="section-kicker">第 3 步 · 先辨证，再立法</span>
        <h2>辨证分析与病机</h2>
        <p>这里呈现证据链，不展示模型内部思维。大夫可以直接修改结论并重新检索。</p>
      </div>
      <button v-if="stale" class="refresh-button" type="button" @click="$emit('refresh')">
        <el-icon><RefreshRight /></el-icon>
        依据已变更，重新分析
      </button>
    </div>

    <div class="analysis-table">
      <div v-for="item in items" :key="item.label" class="analysis-row">
        <span class="analysis-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <p>{{ item.evidence }}</p>
      </div>
    </div>

    <div class="conclusion-grid">
      <label class="conclusion-card">
        <span>核心病机 <em>AI 草稿</em></span>
        <textarea v-model="mechanism" @input="$emit('changed')"></textarea>
      </label>
      <label class="conclusion-card treatment-card">
        <span>综合治法 <em>由病机推导</em></span>
        <textarea v-model="treatment" @input="$emit('changed')"></textarea>
      </label>
    </div>

    <div class="logic-line" aria-label="诊疗逻辑">
      <span>四诊</span><i>→</i><span>脾胃气虚</span><i>→</i><span>运化失健</span><i>→</i><strong>益气健脾</strong>
    </div>

    <div class="action-row">
      <span><el-icon><CircleCheck /></el-icon> 修改病机或治法后，系统会重新检索，而非只改写原答案</span>
      <button class="primary-button" type="button" @click="$emit('confirm')">确认治法，检索基础方</button>
    </div>
  </section>
</template>
