<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AuthenticationRequiredError, clearCmsToken } from '../api/client'
import { createVisit, getVisit, listVisits, transition, type Encounter, type Patient, type VisitSummary } from '../api/encounters'
import { toFormulaCandidate } from '../api/rag'
import { displayConfirmations, prescriptionText } from '../services/clinicalDrafts'
import type { FormulaDoseConversion } from '../types/consultation'
import SmartVoiceIntake from './SmartVoiceIntake.vue'
import AgentProgress from './AgentProgress.vue'
import AnalysisLayers from './AnalysisLayers.vue'
import FormulaPanel from './FormulaPanel.vue'

const emit = defineEmits<{ logout: [] }>()
const visit = ref<Encounter | null>(null)
const visits = ref<VisitSummary[]>([])
const busy = ref(false)
const busyMessage = ref('正在读取就诊资料……')
const error = ref('')
const dirty = ref(false)
const step = ref(0)
const stages = ['问诊记录', '辨证论治', '选方遣药', '病历确认']
const confirmed = computed(() => displayConfirmations(visit.value?.state.confirmed || [false, false, false, false, false]))
const patient = ref<Patient>({ name: '', sex: '未提供', age: null, allergy: '待确认' })
const transcript = ref('')
const recording = ref(false)
const examinations = ref<Record<string, string>>({ inspection: '', palpation: '', listening: '' })
const analysis = ref<Record<string, string>>({})
const selected = ref('')
const selectedIds = ref<string[]>([])
const formulaConversions = ref<Record<string, FormulaDoseConversion>>({})
const prescription = ref('')
const record = ref('')
const reviewed = ref(false)
const candidates = computed(() => visit.value?.state.candidates.map(toFormulaCandidate) || [])
const adoptedIds = computed(() => visit.value?.state.selected_ids?.length
  ? visit.value.state.selected_ids
  : visit.value?.state.selected_id ? [visit.value.state.selected_id] : [])
const adoptedNames = computed(() => adoptedIds.value.map(id => visit.value?.state.candidates.find(c => c.id === id)?.name).filter(Boolean).join('、'))
const operationLabels: Record<string, string> = {
  save_intake: '正在保存问诊记录……', confirm_intake: '正在确认问诊结果与望切补充……',
  finalize_voice: '录音已保存，正在整理问诊信息……', analyze: '正在整理辨证论治草稿……',
  retrieve: '正在检索基础方及辞典依据……', generate_record: '正在汇总已确认内容，生成病历草稿……',
}

function hydrate(value: Encounter) {
  visit.value = value
  patient.value = { ...value.state.patient }
  // Preserve previously confirmed/edited inquiry when opening a legacy five-step encounter.
  transcript.value = value.state.examinations?.inquiry ?? value.state.transcript
  examinations.value = { inspection: '', palpation: '', listening: '', ...(value.state.examinations || {}) }
  analysis.value = { ...(value.state.analysis || {}) }
  selected.value = value.state.selected_id
  selectedIds.value = []
  formulaConversions.value = {}
  prescription.value = prescriptionText(value.state.prescription)
  record.value = value.state.record
  reviewed.value = false
  dirty.value = false
}
async function run(work: () => Promise<void>) {
  if (busy.value) return
  if (recording.value) { error.value = '请先暂停录音并完成保存。'; return }
  busy.value = true; busyMessage.value = '正在保存或读取就诊资料……'; error.value = ''
  try { await work() } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败，请重试'
    if (e instanceof AuthenticationRequiredError) error.value += '。未保存内容仍在本页，请先复制留存，再退出重新登录。'
  } finally { busy.value = false }
}
async function send(action: string, data: object = {}) {
  if (!visit.value) throw new Error('请先创建就诊')
  busyMessage.value = operationLabels[action] || '正在保存医师修改与确认结果……'
  hydrate(await transition(visit.value, action, data))
}
function intakeData() {
  return { patient: { ...patient.value }, text: transcript.value,
    inspection: examinations.value.inspection, palpation: examinations.value.palpation, listening: examinations.value.listening }
}
async function save() {
  if (step.value === 0) await send('save_intake', intakeData())
  if (step.value === 1) await send('save_analysis', analysis.value)
  if (step.value === 2) await send('save_prescription', { text: prescription.value })
  if (step.value === 3) await send('save_record', { text: record.value })
}
async function navigate(next: number) {
  await run(async () => {
    if (dirty.value) await save()
    if (next > 0 && !confirmed.value[next - 1]) throw new Error('请先完成并确认前一步')
    step.value = next
  })
}
async function finalizeVoice() {
  await run(async () => {
    if (dirty.value) await save()
    await send('finalize_voice')
  })
}
async function confirmIntake() {
  await run(async () => {
    await send('confirm_intake', { ...intakeData(), reviewed: true })
    step.value = 1
    await send('analyze')
  })
}
async function confirmAnalysis() {
  await run(async () => {
    if (dirty.value) await save()
    await send('confirm_analysis')
    step.value = 2
    await send('retrieve')
  })
}
async function confirmPrescription() {
  await run(async () => {
    if (dirty.value) await save()
    await send('confirm_prescription', { reviewed: true })
    step.value = 3
    await send('generate_record')
  })
}
async function adoptFormula() {
  const ids = [...selectedIds.value]
  const conversions = Object.fromEntries(ids.filter(id => formulaConversions.value[id]).map(id => [id, formulaConversions.value[id]]))
  await run(async () => {
    if (dirty.value) await save()
    await send('select_formulas', { ids, conversions })
  })
}
async function confirmRecord() {
  await run(async () => {
    if (!reviewed.value) throw new Error('请先勾选医师审核确认')
    if (dirty.value) await save()
    await send('confirm_record', { reviewed: true })
    ElMessage.success('医师确认版本已保存')
  })
}
async function open(id: number) {
  await run(async () => {
    hydrate(await getVisit(id))
    const first = confirmed.value.findIndex(v => !v)
    step.value = first < 0 ? 3 : first
  })
}
async function back() {
  await run(async () => {
    if (dirty.value) await save()
    visits.value = await listVisits(); visit.value = null
    patient.value = { name: '', sex: '未提供', age: null, allergy: '待确认' }
  })
}
async function logout() {
  if (busy.value || recording.value) return
  if (dirty.value) {
    try { await ElMessageBox.confirm('有未保存修改，退出会丢失。是否继续？', '退出登录') } catch { return }
  }
  clearCmsToken(); emit('logout')
}
function guardLeave(event: BeforeUnloadEvent) {
  if (dirty.value || busy.value || recording.value) { event.preventDefault(); event.returnValue = '' }
}
function exportRecord() {
  if (!visit.value?.state.confirmed[4] || dirty.value) return
  const url = URL.createObjectURL(new Blob([record.value], { type: 'text/plain;charset=utf-8' }))
  const link = document.createElement('a'); link.href = url; link.download = '病历-' + visit.value.id + '.txt'; link.click()
  URL.revokeObjectURL(url)
}
onMounted(() => { window.addEventListener('beforeunload', guardLeave); void run(async () => { visits.value = await listVisits() }) })
onBeforeUnmount(() => window.removeEventListener('beforeunload', guardLeave))
</script>

<template>
  <div class="app-shell live-workbench">
    <header class="live-header">
      <div><h1>医生坐诊工作台</h1><p>{{ visit ? visit.state.patient.name : '患者与就诊' }}</p></div>
      <div class="live-actions">
        <button v-if="visit" :disabled="busy || recording" @click="back">返回就诊列表</button>
        <button :disabled="busy || recording" @click="logout">退出登录</button>
      </div>
    </header>
    <p v-if="error" class="live-error" role="alert">{{ error }}</p>
    <AgentProgress :active="busy" :message="busyMessage" />
    <section v-if="!visit" class="panel live-panel">
      <h2>创建患者与就诊</h2>
      <form class="live-fields" @submit.prevent="run(async () => { hydrate(await createVisit(patient)); step = 0 })">
        <label>姓名<input v-model="patient.name" required maxlength="80" /></label>
        <label>性别<select v-model="patient.sex"><option>未提供</option><option>男</option><option>女</option></select></label>
        <label>年龄<input v-model.number="patient.age" type="number" required min="0" max="130" /></label>
        <label>药物过敏史<input v-model="patient.allergy" required placeholder="未核实时填写待确认" /></label>
        <button class="primary-button" :disabled="busy">创建就诊</button>
      </form>
      <h2>最近就诊</h2>
      <p v-if="!visits.length">暂无记录。开发验证请使用虚构病例。</p>
      <article v-for="item in visits" :key="item.id" class="live-visit">
        <span>{{ item.patient.name }} · {{ item.confirmed ? '医师已确认' : '进行中' }} · {{ new Date(item.updated_at).toLocaleString() }}</span>
        <button :disabled="busy" @click="open(item.id)">打开就诊 {{ item.id }}</button>
        <button :disabled="busy" @click="run(async () => { hydrate(await createVisit(item.patient, item.patient_id)); step = 0 })">新增复诊</button>
      </article>
    </section>
    <template v-else>
      <nav class="compact-stages" aria-label="诊疗流程">
        <button v-for="(label, index) in stages" :key="label" :class="{ active: step === index }" :aria-current="step === index ? 'step' : undefined" :disabled="busy || recording" @click="navigate(index)">
          <span>{{ confirmed[index] ? '✓' : index + 1 }}</span>{{ label }}
        </button>
      </nav>
      <p class="live-save-status">{{ dirty ? '修改将在确认本步时保存' : '已保存 · ' + new Date(visit.updated_at).toLocaleTimeString() }}</p>
      <main class="main-workspace">
        <fieldset :disabled="busy" class="live-fieldset">
          <template v-if="step === 0">
            <details class="patient-details"><summary>患者信息 · {{ patient.name }} · {{ patient.age }}岁 · 过敏史：{{ patient.allergy }}</summary>
              <div class="live-fields">
                <label>姓名<input v-model="patient.name" maxlength="80" @input="dirty = true" /></label>
                <label>性别<select v-model="patient.sex" @change="dirty = true"><option>未提供</option><option>男</option><option>女</option></select></label>
                <label>年龄<input v-model.number="patient.age" type="number" min="0" max="130" @input="dirty = true" /></label>
                <label>药物过敏史<input v-model="patient.allergy" @input="dirty = true" /></label>
              </div>
            </details>
            <SmartVoiceIntake :key="visit.id" :encounter-id="visit.id" :text="transcript" :summary="visit.state.voice_summary" :disabled="busy" @change="if (transcript !== $event) { transcript = $event; dirty = true }" @recording-change="recording = $event" @finish="finalizeVoice" />
            <section class="panel live-panel supplements">
              <h3>望切补充</h3>
              <div class="supplement-fields">
                <label class="live-text">望诊<textarea v-model="examinations.inspection" aria-label="望诊补充" placeholder="舌象、神色等，可留空" @input="dirty = true" /></label>
                <label class="live-text">切诊<textarea v-model="examinations.palpation" aria-label="切诊补充" placeholder="脉象、按诊等，可留空" @input="dirty = true" /></label>
              </div>
              <details :open="Boolean(examinations.listening)"><summary>其他面诊补充（可选）</summary>
                <label class="live-text">闻诊<textarea v-model="examinations.listening" aria-label="闻诊补充" @input="dirty = true" /></label>
              </details>
            </section>
            <div class="live-actions intake-actions">
              <button class="primary-button" :disabled="recording || !transcript.trim()" @click="confirmIntake">确认问诊，生成辨证</button>
            </div>
          </template>
          <section v-else-if="step === 1" class="panel live-panel">
            <div class="section-title"><h2>辨证论治草稿</h2></div>
            <template v-if="visit.state.analysis">
              <AnalysisLayers v-model="analysis" @changed="dirty = true" />
              <div class="live-actions"><button class="primary-button" @click="confirmAnalysis">确认辨证论治，检索基础方</button></div>
            </template>
          </section>
          <section v-else-if="step === 2">
            <FormulaPanel v-model="selected" v-model:selected-ids="selectedIds" multiple
              :adopted-ids="adoptedIds" :encounter-id="visit.id" :candidates="candidates" :stale="false"
              :loading="busy" :candidate-pool="visit.state.retrieval?.candidate_pool || candidates.length" data-mode="live"
              @conversion="(id, conversion) => formulaConversions[id] = conversion" @confirm="adoptFormula" />
            <section v-if="adoptedIds.length" class="panel live-panel prescription-editor">
              <div class="section-title"><h2>大夫编辑处方</h2><span>已带入：{{ adoptedNames }}</span></div>
              <p class="quiet-note">基础方保留在上方，可上下滑动复看。请在原方参考上增减，并核对重复药味、剂量及用法。</p>
              <textarea v-model="prescription" class="prescription-text" aria-label="编辑处方" placeholder="此条目无组成原文，请由医师填写本次处方。" @input="dirty = true" />
              <div class="live-actions"><button class="primary-button" @click="confirmPrescription">确认处方，生成病历</button></div>
            </section>
          </section>
          <section v-else class="panel live-panel">
            <h2>病历草稿</h2>
            <button v-if="!record" @click="run(async () => { await send('generate_record') })">生成病历草稿</button>
            <label class="live-text">病历正文<textarea v-model="record" class="live-record" @input="dirty = true; reviewed = false" /></label>
            <label><input v-model="reviewed" type="checkbox" /> 我已审核病历、处方及待填项，确认保存此版本。</label>
            <div class="live-actions"><button class="primary-button" :disabled="!reviewed" @click="confirmRecord">医师确认并保存</button><button :disabled="!visit.state.confirmed[4] || dirty" @click="exportRecord">导出已确认病历</button></div>
            <p v-if="visit.state.confirmed[4] && !dirty">医师已确认并保存。</p>
          </section>
        </fieldset>
      </main>
    </template>
    <footer class="global-footer">诊疗辅助草稿，最终内容由执业医师审核确认。</footer>
  </div>
</template>

<style scoped>
.live-workbench { max-width: 1320px; margin: auto; padding: 24px; }
.live-workbench > .global-footer { position: static; margin-top: 24px; }
.live-header, .live-actions, .live-visit, .section-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.live-header h1 { font-size: 24px; }.live-header p, .live-save-status, .quiet-note { color: #617369; }.live-save-status { text-align: right; font-size: 13px; margin: 10px 0; }
.live-workbench .compact-stages { display: flex; border-bottom: 1px solid #d8e1db; margin-top: 20px; gap: 12px; }
.live-workbench .compact-stages button { display: flex; align-items: center; gap: 10px; border: 0; border-radius: 0; background: transparent; padding: 14px 20px; margin: 0; font-size: 17px; color: #67796e; }
.live-workbench .compact-stages button.active { color: #20563c; border-bottom: 3px solid #2c694a; font-weight: 700; }.compact-stages span { font-size: 14px; }
.live-fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }.live-fieldset:disabled { opacity: .65; }
.live-panel { padding: 24px; margin: 16px 0; }.live-panel h2 { font-size: 21px; }.live-panel h3 { font-size: 18px; }
.live-fields { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin: 18px 0; }
.live-fields label, .live-text { display: flex; flex-direction: column; gap: 8px; }.live-text { margin: 14px 0; }
input:not([type=checkbox]), select, textarea { border: 1px solid #c9d4cd; border-radius: 8px; padding: 12px; background: white; color: #253d31; font: inherit; }
textarea { width: 100%; min-height: 90px; resize: vertical; font-size: 19px; line-height: 1.8; }.live-record { min-height: 620px; }.prescription-text { min-height: 360px; margin: 14px 0; }
.live-workbench button { padding: 10px 16px; border-radius: 8px; border: 1px solid #c9d4cd; cursor: pointer; margin: 4px; }.live-workbench button:disabled { opacity: .5; cursor: not-allowed; }
.live-workbench .primary-button { font-size: 15px; }
.live-error { background: #fff0ea; color: #983919; padding: 16px; border-radius: 8px; }.live-visit { border-top: 1px solid #dbe4df; padding: 12px 0; }
.supplement-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }.patient-details { margin-bottom: 16px; }summary { cursor: pointer; color: #617369; }.intake-actions { justify-content: flex-end; margin: 18px 0; }
@media (max-width: 700px) { .live-workbench { padding: 12px; }.supplement-fields { grid-template-columns: 1fr; }.live-workbench .compact-stages { gap: 0; }.live-workbench .compact-stages button { padding: 10px 5px; font-size: 15px; flex: 1; justify-content: center; gap: 4px; } }
</style>
