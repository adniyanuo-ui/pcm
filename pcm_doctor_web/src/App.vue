<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AnalysisPanel from './components/AnalysisPanel.vue'
import EvidenceSidebar from './components/EvidenceSidebar.vue'
import FormulaPanel from './components/FormulaPanel.vue'
import FourExaminations from './components/FourExaminations.vue'
import LoginGate from './components/LoginGate.vue'
import MedicalRecordPanel from './components/MedicalRecordPanel.vue'
import PrescriptionEditor from './components/PrescriptionEditor.vue'
import StageRail from './components/StageRail.vue'
import VisitHeader from './components/VisitHeader.vue'
import VoiceIntake from './components/VoiceIntake.vue'
import {
  analysisItems,
  formulaCandidates as demoFormulaCandidates,
  initialExaminations,
  initialPrescription,
  stages,
} from './data/demo'
import { hasCmsToken, isRagApiConfigured, searchFormulas, toFormulaCandidate } from './api/rag'

const apiConfigured = isRagApiConfigured()
const authenticated = ref(!apiConfigured || hasCmsToken())
const currentStep = ref(0)
const confirmed = reactive(stages.map(() => false))
const examinations = ref(initialExaminations.map((item) => ({ ...item })))
const mechanism = ref('脾胃气虚，运化失健，清阳不振；寒象尚轻，暂不径断脾阳虚。')
const treatment = ref('益气健脾，和胃止泻；根据畏寒、脉象复核结果决定是否佐以温中。')
const formulaCandidates = ref(demoFormulaCandidates.map((item) => ({ ...item })))
const selectedFormulaId = ref(formulaCandidates.value[0].id)
const prescription = ref(initialPrescription.map((item) => ({ ...item })))
const downstreamStale = ref(false)
const prescriptionVisible = ref(false)
const retrievalLoading = ref(false)
const retrievalPool = ref(126)
const dataMode = ref<'demo' | 'live'>('demo')

const selectedFormula = computed(() => formulaCandidates.value.find((item) => item.id === selectedFormulaId.value))

function selectStage(index: number) {
  currentStep.value = index
}

function confirmStep(index: number, next = index + 1) {
  confirmed[index] = true
  currentStep.value = Math.min(next, stages.length - 1)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function markClinicalDataChanged() {
  downstreamStale.value = true
  for (let index = 2; index < confirmed.length; index += 1) confirmed[index] = false
}

function refreshEvidence(message: string) {
  downstreamStale.value = false
  ElMessage.success(message)
}

function examinationValue(key: string): string[] {
  const value = examinations.value.find((item) => item.key === key)?.value
  return value ? [value] : []
}

async function retrieveFormulas() {
  downstreamStale.value = false
  if (!isRagApiConfigured()) {
    dataMode.value = 'demo'
    formulaCandidates.value = demoFormulaCandidates.map((item) => ({ ...item }))
    selectedFormulaId.value = formulaCandidates.value[0].id
    ElMessage.info('当前使用演示数据；配置 VITE_API_BASE_URL 后启用真实辞典检索')
    return
  }
  retrievalLoading.value = true
  try {
    const result = await searchFormulas({
      symptoms: examinationValue('问'),
      tongue: examinationValue('望'),
      pulse: examinationValue('切'),
      voice: examinationValue('闻'),
      mechanisms: [mechanism.value],
      syndromes: ['脾胃气虚证'],
      treatments: [treatment.value],
      top_k: 5,
    })
    const mapped = result.candidates.map(toFormulaCandidate)
    if (!mapped.length) throw new Error('辞典中未召回候选方，请补充信息后重试')
    formulaCandidates.value = mapped
    selectedFormulaId.value = mapped[0].id
    retrievalPool.value = result.retrieval.candidate_pool
    dataMode.value = 'live'
    ElMessage.success('已从辞典召回并重排 ' + result.retrieval.candidate_pool + ' 条候选')
  } catch (error) {
    const message = error instanceof Error ? error.message : '真实检索失败'
    ElMessage.error(message)
  } finally {
    retrievalLoading.value = false
  }
}

async function confirmAnalysis() {
  confirmStep(2, 3)
  await retrieveFormulas()
}

async function openPrescription() {
  prescriptionVisible.value = true
  await nextTick()
  document.querySelector('.prescription-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function completeVisit() {
  confirmed[4] = true
  ElMessageBox.alert(
    '演示接诊已完成。正式版本将在此保存医师确认版本，并保留 AI 草稿、修改记录和典籍证据。',
    '病历已确认',
    { confirmButtonText: '知道了', type: 'success' },
  )
}
</script>

<template>
  <LoginGate v-if="!authenticated" @authenticated="authenticated = true" />
  <div v-else class="app-shell">
    <VisitHeader @back="ElMessage.info('演示页面：这里将返回患者列表')" />

    <div class="workspace-layout">
      <StageRail :stages="stages" :current="currentStep" :confirmed="confirmed" @select="selectStage" />

      <main class="main-workspace">
        <div class="workspace-titlebar">
          <div>
            <span>当前步骤 {{ currentStep + 1 }} / {{ stages.length }}</span>
            <h2>{{ stages[currentStep].label }}</h2>
          </div>
          <p>{{ stages[currentStep].hint }}</p>
        </div>

        <Transition name="stage-fade" mode="out-in">
          <VoiceIntake v-if="currentStep === 0" key="intake" @confirm="confirmStep(0)" />

          <FourExaminations
            v-else-if="currentStep === 1"
            key="examination"
            v-model="examinations"
            @changed="markClinicalDataChanged"
            @confirm="confirmStep(1)"
          />

          <AnalysisPanel
            v-else-if="currentStep === 2"
            key="analysis"
            v-model:mechanism="mechanism"
            v-model:treatment="treatment"
            :items="analysisItems"
            :stale="downstreamStale"
            @changed="markClinicalDataChanged"
            @refresh="refreshEvidence('已根据最新四诊重新分析')"
            @confirm="confirmAnalysis"
          />

          <div v-else-if="currentStep === 3" key="formula" class="formula-stage">
            <FormulaPanel
              v-model="selectedFormulaId"
              :candidates="formulaCandidates"
              :stale="downstreamStale"
              :loading="retrievalLoading"
              :candidate-pool="retrievalPool"
              :data-mode="dataMode"
              @refresh="retrieveFormulas"
              @confirm="openPrescription"
            />
            <Transition name="stage-fade">
              <PrescriptionEditor
                v-if="prescriptionVisible"
                v-model="prescription"
                @changed="confirmed[3] = false"
                @confirm="confirmStep(3)"
              />
            </Transition>
          </div>

          <MedicalRecordPanel v-else key="record" @confirm="completeVisit" />
        </Transition>
      </main>

      <EvidenceSidebar
        :current="currentStep"
        :stages="stages"
        :confirmed="confirmed"
        :selected-formula="selectedFormula"
        :stale="downstreamStale"
      />
    </div>

    <footer class="global-footer">
      <span>本工具仅提供诊疗辅助草稿，不替代执业医师判断</span>
      <span>自动保存于 10:06:24</span>
    </footer>
  </div>
</template>
