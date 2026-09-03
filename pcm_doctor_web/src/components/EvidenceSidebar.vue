<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, DataAnalysis, Files, Warning } from '@element-plus/icons-vue'
import type { FormulaCandidate, StageDefinition } from '../types/consultation'

const props = defineProps<{
  current: number
  stages: StageDefinition[]
  confirmed: boolean[]
  selectedFormula?: FormulaCandidate
  stale: boolean
}>()

const progress = computed(() => Math.round((props.confirmed.filter(Boolean).length / props.stages.length) * 100))
</script>

<template>
  <aside class="evidence-sidebar">
    <div class="sidebar-head">
      <div>
        <span class="section-kicker">全程可回溯</span>
        <h2>诊疗证据链</h2>
      </div>
      <strong>{{ progress }}%</strong>
    </div>
    <div class="progress-track"><i :style="{ width: `${progress}%` }"></i></div>

    <div class="evidence-timeline">
      <div class="evidence-node done">
        <span><el-icon><Files /></el-icon></span>
        <div><strong>原始信息</strong><p>医患对话 5 条 · 面诊补充 3 项</p></div>
      </div>
      <div class="evidence-node" :class="{ done: current >= 2 }">
        <span><el-icon><DataAnalysis /></el-icon></span>
        <div><strong>辨证与治法</strong><p>脾胃气虚 · 益气健脾</p></div>
      </div>
      <div class="evidence-node" :class="{ done: current >= 3 }">
        <span><el-icon><CircleCheck /></el-icon></span>
        <div>
          <strong>典籍候选方</strong>
          <p v-if="selectedFormula">{{ selectedFormula.name }} · 方号 {{ selectedFormula.id }}</p>
          <p v-else>等待检索</p>
        </div>
      </div>
    </div>

    <div v-if="stale" class="sidebar-warning">
      <el-icon><Warning /></el-icon>
      <p><strong>信息已发生变化</strong><span>确认前需要重新执行分析或检索。</span></p>
    </div>

    <div class="source-card">
      <span class="source-seal">典</span>
      <div>
        <strong>知识来源</strong>
        <p>《中医方剂大辞典》正编</p>
        <small>96,381 条可检索记录</small>
      </div>
    </div>

    <div class="boundary-note">
      <strong>人与 AI 的边界</strong>
      <p>AI 负责整理、检索和起草；所有四诊、辨证、处方及病历均由大夫修改并最终确认。</p>
    </div>
  </aside>
</template>
