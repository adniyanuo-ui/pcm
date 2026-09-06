<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElDialog } from 'element-plus'
import { CircleCheck, Document, RefreshRight, Warning } from '@element-plus/icons-vue'
import type { FormulaCandidate, FormulaDoseConversion } from '../types/consultation'
import FormulaDoseReference from './FormulaDoseReference.vue'

const selectedId = defineModel<string>({ required: true })
const selectedIds = defineModel<string[]>('selectedIds', { default: () => [] })
const pendingSelection = ref<string[]>([...selectedIds.value])

const props = defineProps<{
  candidates: FormulaCandidate[]
  stale: boolean
  loading: boolean
  candidatePool: number
  dataMode: 'demo' | 'live'
  multiple?: boolean
  adoptedIds?: string[]
  encounterId?: number
}>()

const emit = defineEmits<{
  refresh: []
  confirm: []
  conversion: [id: string, conversion: FormulaDoseConversion]
}>()

const originalVisible = ref(false)
const originalCandidate = ref<FormulaCandidate | null>(null)
watch(selectedIds, value => { pendingSelection.value = [...value] }, { flush: 'sync' })

function showOriginal(candidate: FormulaCandidate) {
  originalCandidate.value = candidate
  originalVisible.value = true
}

function adopted(id: string) { return props.adoptedIds?.includes(id) || false }
function chosen(id: string) { return props.multiple ? adopted(id) || pendingSelection.value.includes(id) : selectedId.value === id }
function choose(id: string) {
  if (!props.multiple) { selectedId.value = id; return }
  if (adopted(id)) return
  const next = pendingSelection.value.includes(id)
    ? pendingSelection.value.filter(value => value !== id)
    : (props.adoptedIds?.length || 0) + pendingSelection.value.length < 5 ? [...pendingSelection.value, id] : pendingSelection.value
  pendingSelection.value = next
  selectedIds.value = next
}
</script>

<template>
  <section class="content-section">
    <div class="section-heading-row formula-heading">
      <div>
        <h2>候选基础方</h2>
        <p>
          <template v-if="dataMode === 'live'">根据已确认的问诊与辨证检索 · {{ candidates.length }} 个候选</template>
          <template v-else>当前展示内置演示结果，配置 API 后切换为真实辞典检索。</template>
        </p>
      </div>
      <span v-if="dataMode === 'demo'" class="data-mode-badge demo">演示数据</span>
      <button v-if="!multiple" class="refresh-button" :class="{ urgent: stale }" type="button" :disabled="loading" @click="$emit('refresh')">
        <el-icon><RefreshRight /></el-icon>
        {{ loading ? '检索中…' : stale ? '信息已变更，重新检索' : '重新检索' }}
      </button>
    </div>

    <div v-if="loading" class="formula-loading">
      <i v-for="item in 3" :key="item"></i>
      <p>正在检索辞典原文并重排候选方…</p>
    </div>
    <div v-else class="formula-list">
      <article
        v-for="(candidate, index) in candidates"
        :key="candidate.id"
        class="formula-card"
        :class="{ selected: chosen(candidate.id), adopted: adopted(candidate.id) }"
        :role="multiple ? 'checkbox' : 'radio'"
        :tabindex="adopted(candidate.id) ? -1 : 0"
        :aria-checked="chosen(candidate.id)"
        @click="choose(candidate.id)"
        @keydown.enter="choose(candidate.id)"
        @keydown.space.prevent="choose(candidate.id)"
      >
        <div class="formula-rank">0{{ index + 1 }}</div>
        <div class="formula-main">
          <div class="formula-title">
            <div>
              <h3>{{ candidate.name }}</h3>
              <span>方号 {{ candidate.id }} · {{ candidate.source }}</span>
              <em v-if="adopted(candidate.id)" class="adopted-label">已带入编辑框</em>
            </div>
            <div class="match-score"><strong>{{ candidate.match }}</strong><small>% 证据覆盖</small></div>
          </div>
          <p class="formula-summary">{{ candidate.summary }}</p>

          <p class="formula-composition"><strong>组成：</strong>{{ candidate.composition }}</p>
          <p v-if="candidate.doseReference?.warnings[0]" class="dose-warning">{{ candidate.doseReference.warnings[0] }}</p>
          <FormulaDoseReference v-if="dataMode === 'live' && encounterId && candidate.doseReference"
            :encounter-id="encounterId" :reference="candidate.doseReference" :disabled="adopted(candidate.id)"
            @converted="emit('conversion', candidate.id, $event)" />
          <details class="evidence-lines" @click.stop><summary>支持证据与不确定性</summary>
            <div class="support-line">
              <span><el-icon><CircleCheck /></el-icon> 支持</span>
              <p><i v-for="item in candidate.supports" :key="item">{{ item }}</i></p>
            </div>
            <div class="caution-line">
              <span><el-icon><Warning /></el-icon> 不足</span>
              <p><i v-for="item in candidate.cautions" :key="item">{{ item }}</i></p>
            </div>
          </details>

          <div class="citation-row">
            <span>《中医方剂大辞典》第{{ candidate.citation.volume }}册 · PDF {{ candidate.citation.pdfPage }}页 · 书内{{ candidate.citation.bookPage }}页</span>
            <button type="button" @click.stop="showOriginal(candidate)">
              <el-icon><Document /></el-icon> 查看完整方剂
            </button>
          </div>
        </div>
        <span class="select-dot"><i></i></span>
      </article>
    </div>

    <div class="action-row">
      <span v-if="multiple">已带入 {{ adoptedIds?.length || 0 }} 方，待带入 {{ pendingSelection.length }} 方；合方须由大夫核对重复药味与总量。</span>
      <span v-else>当前选择：<strong>{{ candidates.find(item => item.id === selectedId)?.name }}</strong>，大夫仍可增减药味与剂量</span>
      <button class="primary-button" type="button" :disabled="multiple ? !pendingSelection.length || loading || stale : !selectedId || loading || stale" @click="$emit('confirm')">
        {{ multiple ? '带入所选基础方' : '采用此方，编辑处方' }}
      </button>
    </div>

    <el-dialog v-model="originalVisible" width="min(900px, 94vw)" class="source-dialog" title="完整基础方 · 辞典原文">
      <template v-if="originalCandidate">
        <div class="dialog-title-row">
          <strong>{{ originalCandidate.name }}</strong>
          <span>方号 {{ originalCandidate.id }}</span>
        </div>
        <dl class="source-content">
          <template v-if="originalCandidate.fields">
            <template v-for="label in ['方源', '组成', '用法', '功用', '主治', '加减', '宜忌', '正文及其他']" :key="label">
              <dt>{{ label }}</dt><dd style="white-space: pre-wrap">{{ originalCandidate.fields[label] || '辞典本条未提供，不以推测补全' }}</dd>
            </template>
          </template>
          <template v-else><dt>方源</dt><dd>{{ originalCandidate.source }}</dd><dt>组成</dt><dd>{{ originalCandidate.composition }}</dd><dt>主治</dt><dd>{{ originalCandidate.original }}</dd></template>
        </dl>
        <p v-if="originalCandidate.truncatedFields?.length">此历史记录的 {{ originalCandidate.truncatedFields.join('、') }} 存在截断，请关闭详情并重新检索后查看完整条目。</p>
        <p class="source-location">定位：{{ originalCandidate.fullCitation || `第${originalCandidate.citation.volume}册，PDF ${originalCandidate.citation.pdfPage}页，书内${originalCandidate.citation.bookPage}页` }}</p>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.formula-summary { font-size: 15px; line-height: 1.7; }
.formula-composition { margin: 10px 0; font-size: 16px; line-height: 1.75; color: #263f32; }
.dose-warning { margin: 7px 0; color: #886224; font-size: 13px; line-height: 1.6; }
.citation-row > span { font-size: 12px; }.citation-row button { font-size: 12px; }
.action-row > span { font-size: 14px; }
.adopted-label { display: inline-block; margin: 6px 0 0 8px; padding: 2px 7px; border-radius: 5px; color: #276044; background: #e7f3ec; font-size: 12px; font-style: normal; }
.formula-card[role=checkbox] .select-dot { border-radius: 4px; }
</style>
