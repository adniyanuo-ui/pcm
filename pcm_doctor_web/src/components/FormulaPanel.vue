<script setup lang="ts">
import { ref } from 'vue'
import { ElDialog } from 'element-plus'
import { CircleCheck, Document, RefreshRight, Warning } from '@element-plus/icons-vue'
import type { FormulaCandidate } from '../types/consultation'

const selectedId = defineModel<string>({ required: true })

defineProps<{
  candidates: FormulaCandidate[]
  stale: boolean
}>()

defineEmits<{
  refresh: []
  confirm: []
}>()

const originalVisible = ref(false)
const originalCandidate = ref<FormulaCandidate | null>(null)

function showOriginal(candidate: FormulaCandidate) {
  originalCandidate.value = candidate
  originalVisible.value = true
}
</script>

<template>
  <section class="content-section">
    <div class="section-heading-row formula-heading">
      <div>
        <span class="section-kicker">第 4 步 · 方从法出</span>
        <h2>候选基础方</h2>
        <p>按“益气健脾”及已确认的四诊信息检索，共召回 126 条，重排后展示前 3 条。</p>
      </div>
      <button class="refresh-button" :class="{ urgent: stale }" type="button" @click="$emit('refresh')">
        <el-icon><RefreshRight /></el-icon>
        {{ stale ? '信息已变更，重新检索' : '重新检索' }}
      </button>
    </div>

    <div class="formula-list">
      <article
        v-for="(candidate, index) in candidates"
        :key="candidate.id"
        class="formula-card"
        :class="{ selected: selectedId === candidate.id }"
        role="radio"
        tabindex="0"
        :aria-checked="selectedId === candidate.id"
        @click="selectedId = candidate.id"
        @keydown.enter="selectedId = candidate.id"
        @keydown.space.prevent="selectedId = candidate.id"
      >
        <div class="formula-rank">0{{ index + 1 }}</div>
        <div class="formula-main">
          <div class="formula-title">
            <div>
              <h3>{{ candidate.name }}</h3>
              <span>方号 {{ candidate.id }} · {{ candidate.source }}</span>
            </div>
            <div class="match-score"><strong>{{ candidate.match }}</strong><small>匹配度</small></div>
          </div>
          <p class="formula-summary">{{ candidate.summary }}</p>

          <div class="evidence-lines">
            <div class="support-line">
              <span><el-icon><CircleCheck /></el-icon> 支持</span>
              <p><i v-for="item in candidate.supports" :key="item">{{ item }}</i></p>
            </div>
            <div class="caution-line">
              <span><el-icon><Warning /></el-icon> 不足</span>
              <p><i v-for="item in candidate.cautions" :key="item">{{ item }}</i></p>
            </div>
          </div>

          <div class="citation-row">
            <span>《中医方剂大辞典》第{{ candidate.citation.volume }}册 · PDF {{ candidate.citation.pdfPage }}页 · 书内{{ candidate.citation.bookPage }}页</span>
            <button type="button" @click.stop="showOriginal(candidate)">
              <el-icon><Document /></el-icon> 查看原文
            </button>
          </div>
        </div>
        <span class="select-dot"><i></i></span>
      </article>
    </div>

    <div class="action-row">
      <span>当前选择：<strong>{{ candidates.find(item => item.id === selectedId)?.name }}</strong>，大夫仍可增减药味与剂量</span>
      <button class="primary-button" type="button" @click="$emit('confirm')">采用此方，编辑处方</button>
    </div>

    <el-dialog v-model="originalVisible" width="min(620px, 92vw)" class="source-dialog" title="辞典原文">
      <template v-if="originalCandidate">
        <div class="dialog-title-row">
          <strong>{{ originalCandidate.name }}</strong>
          <span>方号 {{ originalCandidate.id }}</span>
        </div>
        <dl class="source-content">
          <dt>方源</dt><dd>{{ originalCandidate.source }}</dd>
          <dt>组成</dt><dd>{{ originalCandidate.composition }}</dd>
          <dt>原文节选</dt><dd>{{ originalCandidate.original }}</dd>
        </dl>
        <p class="source-location">定位：第{{ originalCandidate.citation.volume }}册，PDF {{ originalCandidate.citation.pdfPage }}页，书内{{ originalCandidate.citation.bookPage }}页</p>
      </template>
    </el-dialog>
  </section>
</template>
