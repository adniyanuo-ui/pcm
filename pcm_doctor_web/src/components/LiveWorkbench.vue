<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AuthenticationRequiredError, clearCmsToken } from '../api/client'
import { createVisit, getHistory, getVisit, listVisits, transition, type Encounter, type Patient, type Prescription, type VisitSummary } from '../api/encounters'
import { toFormulaCandidate } from '../api/rag'
import { stages } from '../data/demo'
import StageRail from './StageRail.vue'
import VoiceIntake from './VoiceIntake.vue'
import FormulaPanel from './FormulaPanel.vue'

const emit = defineEmits<{ logout: [] }>()
const visit = ref<Encounter | null>(null)
const visits = ref<VisitSummary[]>([])
const busy = ref(false)
const error = ref('')
const dirty = ref(false)
const step = ref(0)
const patient = ref<Patient>({ name: '', sex: '未提供', age: null, allergy: '待确认' })
const transcript = ref('')
const originalTranscript = ref('')
const recording = ref(false)
const examinations = ref<Record<string, string>>({})
const analysis = ref<Record<string, string>>({})
const selected = ref('')
const prescription = ref<Prescription>({ items: [], count: 1, usage: '', advice: '' })
const record = ref('')
const reviewed = ref(false)
const history = ref<Awaited<ReturnType<typeof getHistory>>>([])
const model = ref('deepseek-v4-pro')
const candidates = computed(() => visit.value?.state.candidates.map(toFormulaCandidate) || [])
const selectedCandidate = computed(() => visit.value?.state.candidates.find(c => c.id === visit.value?.state.selected_id))
const examinationLabels: Record<string, string> = { inspection: '望诊', listening: '闻诊', inquiry: '问诊（主诉、病程及病史）', palpation: '切诊' }
const analysisLabels: Record<string, string> = { cause: '病因', location: '病位', nature: '病性', trend: '病势', syndrome: '证型', mechanism: '病机', treatment: '治法', evidence: '支持证据与不确定性', questions: '待追问项' }

function hydrate(value: Encounter) {
  visit.value = value
  patient.value = { ...value.state.patient }
  transcript.value = value.state.transcript
  originalTranscript.value = value.state.original_transcript || ''
  examinations.value = { ...(value.state.examinations || {}) }
  analysis.value = { ...(value.state.analysis || {}) }
  selected.value = value.state.selected_id
  prescription.value = structuredClone(value.state.prescription || { items: [], count: 1, usage: '', advice: '' })
  record.value = value.state.record
  reviewed.value = false
  dirty.value = false
}
async function run(work: () => Promise<void>) {
  if (busy.value) return
  if (recording.value) { error.value = '请先暂停录音，等待最后一句转写完成。'; return }
  busy.value = true
  error.value = ''
  try { await work() } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败，请重试'
    if (e instanceof AuthenticationRequiredError) {
      // Keep unsaved values visible until the doctor can copy them or retry after login.
      error.value += '。未保存内容仍在当前页面，请先复制留存，再退出重新登录。'
    }
  } finally { busy.value = false }
}
async function send(action: string, data: object = {}) {
  if (!visit.value) throw new Error('请先创建就诊')
  const value = await transition(visit.value, action, data)
  hydrate(value)
}
async function save() {
  if (step.value === 0) {
    const text = transcript.value
    const original = originalTranscript.value
    try {
      if (JSON.stringify(patient.value) !== JSON.stringify(visit.value?.state.patient)) await send('save_patient', patient.value)
      await send('save_transcript', { text, original })
    } catch (e) {
      transcript.value = text
      originalTranscript.value = original
      dirty.value = true
      throw e
    }
  }
  if (step.value === 1) await send('save_examinations', examinations.value)
  if (step.value === 2) await send('save_analysis', analysis.value)
  if (step.value === 3) await send('save_prescription', prescription.value)
  if (step.value === 4) await send('save_record', { text: record.value })
}
async function navigate(next: number) {
  await run(async () => {
    if (dirty.value) await save()
    if (next > 0 && !visit.value?.state.confirmed[next - 1]) throw new Error('请先完成并确认前一步')
    step.value = next
  })
}
async function organize() {
  await run(async () => {
    await save()
    await send('organize', { model: model.value })
    step.value = 1
  })
}
async function confirmExaminations() {
  await run(async () => {
    await save()
    await send('confirm_examinations')
    step.value = 2
    await send('analyze', { model: model.value })
  })
}
async function confirmAnalysis() {
  await run(async () => {
    await save()
    await send('confirm_analysis')
    step.value = 3
    await send('retrieve')
  })
}
async function confirmPrescription() {
  await run(async () => {
    await save()
    await send('confirm_prescription')
    step.value = 4
    await send('generate_record')
  })
}
async function adoptFormula() {
  const id = selected.value
  await run(async () => {
    if (dirty.value) await save()
    await send('select_formula', { id })
  })
}
async function confirmRecord() {
  await run(async () => {
    if (!reviewed.value) throw new Error('请先勾选医师审核确认')
    await save()
    await send('confirm_record', { reviewed: true })
    ElMessage.success('医师确认版本已保存，可刷新或重新登录恢复')
  })
}
async function open(id: number) {
  await run(async () => {
    hydrate(await getVisit(id))
    const first = visit.value!.state.confirmed.findIndex(v => !v)
    step.value = first < 0 ? 4 : first
  })
}
async function back() {
  await run(async () => {
    if (dirty.value) await save()
    visits.value = await listVisits()
    visit.value = null
    patient.value = { name: '', sex: '未提供', age: null, allergy: '待确认' }
    history.value = []
  })
}
async function logout() {
  if (busy.value || recording.value) return
  if (dirty.value) {
    try { await ElMessageBox.confirm('有尚未保存的内容。退出将丢失这些修改，是否继续？', '退出登录') } catch { return }
  }
  clearCmsToken()
  emit('logout')
}
function guardLeave(event: BeforeUnloadEvent) {
  if (dirty.value || busy.value || recording.value) { event.preventDefault(); event.returnValue = '' }
}
function exportRecord() {
  if (!visit.value?.state.confirmed[4] || dirty.value) return
  const blob = new Blob([record.value], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '病历-' + visit.value.id + '.txt'
  link.click()
  URL.revokeObjectURL(url)
}
onMounted(() => { window.addEventListener('beforeunload', guardLeave); void run(async () => { visits.value = await listVisits() }) })
onBeforeUnmount(() => window.removeEventListener('beforeunload', guardLeave))
</script>

<template>
  <div class="app-shell live-workbench">
    <header class="live-header">
      <div><h1>医生坐诊工作台</h1><p>{{ visit ? visit.state.patient.name + ' · 就诊 ' + visit.id : '患者与就诊' }}</p></div>
      <div class="live-actions">
        <button v-if="visit" :disabled="busy || recording" @click="back">返回就诊列表</button>
        <button :disabled="busy || recording" @click="logout">退出登录</button>
      </div>
    </header>
    <p v-if="error" class="live-error" role="alert">{{ error }}</p>
    <p v-if="busy" role="status">正在处理，请稍候。模型生成可能需要约一分钟……</p>
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
      <p class="live-save-status">{{ dirty ? '有未保存修改，保存后将使下游结果失效' : '已保存于 ' + new Date(visit.updated_at).toLocaleString() }} · 版本 {{ visit.version }}</p>
      <div class="workspace-layout live-layout">
        <StageRail :stages="stages" :current="step" :confirmed="visit.state.confirmed" @select="navigate" />
        <main class="main-workspace">
          <h2>{{ stages[step].label }}</h2>
          <fieldset :disabled="busy" class="live-fieldset">
            <label v-if="step < 3" class="live-model">草稿模型
              <select v-model="model"><option value="deepseek-v4-pro">DeepSeek V4 Pro</option><option value="deepseek-v4-flash">DeepSeek V4 Flash</option><option value="qwen3.7-plus">Qwen3.7 Plus（显式备用）</option></select>
            </label>
            <template v-if="step === 0">
              <div class="live-fields">
                <label>姓名<input v-model="patient.name" maxlength="80" @input="dirty = true" /></label>
                <label>性别<select v-model="patient.sex" @change="dirty = true"><option>未提供</option><option>男</option><option>女</option></select></label>
                <label>年龄<input v-model.number="patient.age" type="number" min="0" max="130" @input="dirty = true" /></label>
                <label>药物过敏史<input v-model="patient.allergy" @input="dirty = true" /></label>
              </div>
              <VoiceIntake :key="visit.id" :live-speech="true" :initial-text="transcript" @transcript-change="if (transcript !== $event) { transcript = $event; dirty = true }" @original-change="originalTranscript = $event" @recording-change="recording = $event" @confirm="organize" />
              <button @click="run(save)">保存转写原文</button>
            </template>
            <section v-else-if="step === 1" class="panel live-panel">
              <p>AI 整理草稿，请补充面诊信息并校对。空白表示未提供。</p>
              <label v-for="(label, key) in examinationLabels" :key="key" class="live-text">{{ label }}<textarea v-model="examinations[key]" @input="dirty = true" /></label>
              <button @click="run(save)">保存修改</button>
              <button class="primary-button" @click="confirmExaminations">确认四诊，生成辨证</button>
            </section>
            <section v-else-if="step === 2" class="panel live-panel">
              <p>AI 辨证草稿，由医师审核；下方展示证据摘要。</p>
              <button @click="run(async () => { if (dirty) await save(); await send('analyze', { model }) })">重新生成辨证</button>
              <template v-if="visit.state.analysis">
                <label v-for="(label, key) in analysisLabels" :key="key" class="live-text">{{ label }}<textarea v-model="analysis[key]" @input="dirty = true" /></label>
                <button @click="run(save)">保存修改</button>
                <button class="primary-button" @click="confirmAnalysis">确认治法，检索基础方</button>
              </template>
            </section>
            <section v-else-if="step === 3">
              <FormulaPanel v-model="selected" :candidates="candidates" :stale="false" :loading="busy" :candidate-pool="candidates.length" data-mode="live" @refresh="run(async () => { if (dirty) await save(); await send('retrieve') })" @confirm="adoptFormula" />
              <section v-if="visit.state.selected_id" class="panel live-panel">
                <h3>医师填写处方</h3>
                <p>辞典组成原文：{{ selectedCandidate?.fields['组成'] || '未提供' }}</p>
                <p>请根据原文填写药味及带单位剂量；古代剂量不自动换算。</p>
                <div v-for="(item, index) in prescription.items" :key="index" class="live-fields">
                  <label>药味<input v-model="item.herb" @input="dirty = true" /></label>
                  <label>剂量（含单位）<input v-model="item.dose" @input="dirty = true" /></label>
                  <label>加减依据 / 煎法<input v-model="item.note" @input="dirty = true" /></label>
                  <button @click="prescription.items.splice(index, 1); dirty = true">删除</button>
                </div>
                <button @click="prescription.items.push({ herb: '', dose: '', note: '' }); dirty = true">添加药味</button>
                <div class="live-fields">
                  <label>剂数<input v-model.number="prescription.count" type="number" min="1" max="90" @input="dirty = true" /></label>
                  <label>用法<input v-model="prescription.usage" @input="dirty = true" /></label>
                  <label>医嘱<input v-model="prescription.advice" @input="dirty = true" /></label>
                </div>
                <button @click="run(save)">保存处方</button>
                <button class="primary-button" @click="confirmPrescription">确认处方，生成病历</button>
              </section>
            </section>
            <section v-else class="panel live-panel">
              <p>病历由已确认字段汇总生成。缺失项标注待填，请医师补充或明确记录未提供。</p>
              <button v-if="!record" @click="run(async () => { await send('generate_record') })">生成病历草稿</button>
              <label class="live-text">病历正文<textarea v-model="record" class="live-record" @input="dirty = true; reviewed = false" /></label>
              <label><input v-model="reviewed" type="checkbox" /> 我已审核病历、处方及所有待填项，确认保存此版本。</label>
              <div class="live-actions">
                <button @click="run(save)">保存草稿</button>
                <button class="primary-button" :disabled="!reviewed" @click="confirmRecord">医师确认并保存</button>
                <button :disabled="!visit.state.confirmed[4] || dirty" @click="exportRecord">导出已确认病历</button>
              </div>
              <p v-if="visit.state.confirmed[4] && !dirty">医师已确认并保存。</p>
            </section>
          </fieldset>
          <details class="live-panel"><summary @click="run(async () => { history = await getHistory(visit!.id) })">查看保存与修改历史</summary>
            <details v-for="revision in history" :key="revision.version">
              <summary>版本 {{ revision.version }} · {{ revision.state.confirmed[4] ? '医师已确认' : '草稿' }} · {{ revision.created_at }}</summary>
              <p>患者：{{ revision.state.patient.name }} · 药物过敏史：{{ revision.state.patient.allergy }}</p>
              <h4>当时的转写原文</h4><pre>{{ revision.state.original_transcript || '未录音或未保存原始识别文本' }}</pre>
              <h4>校对文本</h4><pre>{{ revision.state.transcript }}</pre>
              <p v-for="(label, key) in examinationLabels" :key="key">{{ label }}：{{ revision.state.examinations?.[key] || '未提供' }}</p>
              <p v-for="(label, key) in analysisLabels" :key="key">{{ label }}：{{ revision.state.analysis?.[key] || '尚未生成' }}</p>
              <h4>病历</h4><pre>{{ revision.state.record || '尚未生成' }}</pre>
            </details>
          </details>
          <p v-if="visit.state.models.length">最近生成模型：{{ visit.state.models.at(-1)?.actual }}</p>
        </main>
      </div>
    </template>
    <footer class="global-footer">诊疗辅助草稿，最终内容由执业医师审核确认。</footer>
  </div>
</template>

<style scoped>
.live-workbench { max-width: 1500px; margin: auto; padding: 24px; }
.live-header, .live-actions, .live-visit { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.live-header h1 { font-size: 24px; }.live-header p, .live-save-status { color: #52665c; }
.live-layout { grid-template-columns: 240px minmax(0, 1fr); }
.live-fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.live-fieldset:disabled { opacity: .65; }
.live-panel { padding: 24px; margin: 16px 0; }
.live-fields { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin: 18px 0; }
.live-fields label, .live-text { display: flex; flex-direction: column; gap: 8px; }
.live-text { margin: 18px 0; }
input:not([type=checkbox]), select, textarea { border: 1px solid #c9d4cd; border-radius: 8px; padding: 10px; background: white; color: #253d31; font: inherit; }
textarea { width: 100%; min-height: 100px; resize: vertical; }.live-record { min-height: 620px; }
button { padding: 10px 16px; border-radius: 8px; border: 1px solid #c9d4cd; cursor: pointer; margin: 4px; }button:disabled { opacity: .5; cursor: not-allowed; }
.live-error { background: #fff0ea; color: #983919; padding: 16px; border-radius: 8px; }
.live-visit { border-top: 1px solid #dbe4df; padding: 12px 0; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 13px; }
@media (max-width: 850px) { .live-layout { grid-template-columns: 1fr; }.live-workbench { padding: 12px; } }
</style>
