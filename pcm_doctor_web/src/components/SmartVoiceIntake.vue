<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Microphone, VideoPause } from '@element-plus/icons-vue'
import { AliyunRealtimeTranscriber, type SpeechSessionState, type TranscriptUpdate } from '../services/aliyunNls'
import { PcmChunker, toBase64 } from '../services/audioChunks'
import { SerialUploadQueue } from '../services/serialUploadQueue'
import { createRecording, recordings, previewVoice, recoverRecording, snapshot, uploadChunk, type Recording, type VoiceSegment, type VoiceSummary } from '../api/voice'
import AudioReview from './AudioReview.vue'

const props = defineProps<{ encounterId: number; text: string; summary?: VoiceSummary | null; disabled: boolean }>()
const emit = defineEmits<{ change: [text: string]; recordingChange: [active: boolean]; finish: [] }>()
const state = ref<SpeechSessionState>('idle')
const consent = ref(false)
const failure = ref('')
const previewError = ref('')
const preview = ref<VoiceSummary | null>(props.summary || null)
const previewBusy = ref(false)
const processing = ref(false)
const finishing = ref(false)
let finishRequested = false
const draft = ref(props.text)
const doctorEdited = ref(false)
const sessions = ref<Recording[]>([])
const elapsed = ref(0)
const queued = ref(0)
const unsaved = ref(false)
const selectedAudio = ref<Recording | null>(null)
const playbackKey = ref(0)
const playStart = ref(0)
const playEnd = ref<number>()
let recorder: AliyunRealtimeTranscriber | undefined
let chunker: PcmChunker | undefined
let current: Recording | undefined
let segments = new Map<number, VoiceSegment>()
let sequence = 0
let textRevision = 0
let previewRevision = 0
let chunkIndex = 0
let mounted = true
let epoch = 0
let stopTask: Promise<boolean> | undefined
let snapshotTask: Promise<unknown> = Promise.resolve()
const uploads = new SerialUploadQueue<{ recordingId: string; index: number; audio: string }>(
  item => uploadChunk(props.encounterId, item.recordingId, item.index, item.audio),
  size => { queued.value = size },
)
let previewTimer: ReturnType<typeof setTimeout> | undefined
let clock: ReturnType<typeof setInterval> | undefined

const active = computed(() => ['connecting', 'recording', 'stopping'].includes(state.value))
const pending = computed(() => active.value || processing.value || queued.value > 0 || unsaved.value)
const timeLabel = computed(() => `${String(Math.floor(elapsed.value / 60)).padStart(2, '0')}:${String(elapsed.value % 60).padStart(2, '0')}`)
const stateLabel = computed(() => ({ idle: '准备记录问诊信息', connecting: '正在连接录音', recording: '正在记录医患对话', stopping: '正在保存录音', paused: '语音记录已暂停', error: '录音暂不可用' })[state.value])
watch(pending, value => emit('recordingChange', value), { flush: 'sync' })
watch(() => props.text, value => { if (draft.value !== value) doctorEdited.value = false; draft.value = value })
watch(() => props.summary, value => { preview.value = value || null })

async function reload() { sessions.value = await recordings(props.encounterId) }
function readable(e: unknown) { return e instanceof Error ? e.message : '录音操作失败，请重试' }
function drain(): Promise<void> {
  return uploads.drain()
}
function receiveAudio(pcm: ArrayBuffer) {
  chunker?.push(pcm)
  if ((chunker?.totalSamples || 0) >= 16000 * 7200 || queued.value >= 12) {
    failure.value = '录音达到时长或上传缓冲上限，已暂停；请保存后继续。'
    void pause()
  }
}
function sendSnapshot(closed = false): Promise<unknown> {
  if (!current || current.closed) return Promise.resolve()
  const recordingId = current.id
  const version = ++sequence
  const values = [...segments.values()].map(s => ({ ...s }))
  const work = snapshotTask.catch(() => {}).then(() => snapshot(props.encounterId, recordingId, version, values, closed))
  snapshotTask = work
  return work
}
function updateTranscript(update: TranscriptUpdate) {
  if (!update.text.trim()) return
  const old = segments.get(update.index)
  const capturedMs = Math.round((chunker?.totalSamples || 0) / 16)
  const start = update.beginTime ?? old?.start_ms ?? Math.max(0, capturedMs - 1000)
  const end = Math.max(start + 1, update.endTime ?? capturedMs)
  segments.set(update.index, { index: update.index, text: update.text, start_ms: start, end_ms: end })
  if (update.isFinal) { textRevision++; schedulePreview() }
}
function schedulePreview() {
  if (!mounted || previewTimer || previewBusy.value || textRevision === previewRevision) return
  previewTimer = setTimeout(() => { previewTimer = undefined; void summarize() }, 4000)
}
async function summarize() {
  if (!current || !segments.size || previewBusy.value || processing.value) return
  const ticket = epoch
  const revision = textRevision
  previewBusy.value = true; previewError.value = ''
  try {
    await sendSnapshot()
    const result = await previewVoice(props.encounterId)
    if (mounted && epoch === ticket) { preview.value = result; previewRevision = revision }
  } catch (e) { if (mounted && epoch === ticket) previewError.value = '症状提取暂未完成；录音继续保存。' }
  finally {
    if (mounted) previewBusy.value = false
    if (mounted && state.value === 'recording' && textRevision !== revision) schedulePreview()
  }
}
async function start() {
  if (!consent.value || processing.value || props.disabled || queued.value) return
  failure.value = ''; processing.value = true; epoch++
  try {
    finishRequested = false
    current = await createRecording(props.encounterId)
    unsaved.value = true
    segments = new Map(); sequence = 0; chunkIndex = 0
    const recordingId = current.id
    chunker = new PcmChunker(wav => {
      uploads.enqueue({ recordingId, index: chunkIndex++, audio: toBase64(wav) })
      void drain().catch(e => { failure.value = '音频上传中断，未上传内容暂留本页，请勿刷新。' + readable(e) })
    })
    recorder = new AliyunRealtimeTranscriber({
      onState: next => { state.value = next },
      onTranscript: updateTranscript,
      onAudio: receiveAudio,
      onError: message => { failure.value = message; void pause() },
    })
    await recorder.start()
    clearInterval(clock)
    clock = setInterval(() => { if (state.value === 'recording') elapsed.value++ }, 1000)
  } catch (e) { failure.value = readable(e) }
  finally { processing.value = false }
}
function pause(): Promise<boolean> {
  if (stopTask) return stopTask
  processing.value = true; epoch++; clearTimeout(previewTimer); previewTimer = undefined
  clearInterval(clock)
  stopTask = (async () => {
    try {
      await recorder?.stop(); recorder = undefined
      chunker?.flush()
      await drain()
      await sendSnapshot(true)
      if (current) current.closed = true
      unsaved.value = false
      await reload()
      return true
    } catch (e) { failure.value = '录音尚未全部保存，请勿刷新或离开。' + readable(e); return false }
  })().finally(() => { processing.value = false; stopTask = undefined })
  return stopTask
}
async function finish() {
  if (finishing.value) return
  finishing.value = true; finishRequested = true
  try {
    if (!await pause() || queued.value || unsaved.value || (current && !current.closed)) return
    await nextTick()
    if (!mounted) return
    emit('recordingChange', false)
    finishRequested = false
    emit('finish')
  } finally { finishing.value = false }
}
async function retryUpload() {
  failure.value = ''
  if (finishRequested) await finish()
  else await pause()
}
async function recover(session: Recording) {
  processing.value = true
  try { await recoverRecording(props.encounterId, session.id); await reload() }
  catch (e) { failure.value = readable(e) }
  finally { processing.value = false }
}
async function playSource(sourceId: string) {
  try {
    await reload()
    const [recordingId, index] = sourceId.split(':')
    const session = sessions.value.find(s => s.id === recordingId)
    const segment = session?.segments.find(s => s.index === Number(index))
    if (!session || !segment) throw new Error('对应录音尚未保存，请暂停后再回放')
    playStart.value = segment.start_ms; playEnd.value = segment.end_ms; selectedAudio.value = session; playbackKey.value++
  } catch (e) { failure.value = readable(e) }
}
onMounted(() => { void reload().catch(e => { failure.value = readable(e) }) })
onBeforeUnmount(() => {
  mounted = false; epoch++; clearTimeout(previewTimer); clearInterval(clock)
  void recorder?.stop()
})
</script>

<template>
  <section class="smart-voice">
    <div class="voice-layout">
      <div class="recording-card" :class="{ recording: state === 'recording', error: state === 'error' }">
        <div class="sound-orbit">
          <span class="sound-ring ring-one"></span><span class="sound-ring ring-two"></span>
          <button class="record-button" type="button"
            :aria-label="state === 'recording' ? '暂停语音记录' : '开始语音记录'"
            :disabled="processing || disabled || (state !== 'recording' && (!consent || queued > 0 || unsaved))"
            @click="state === 'recording' ? pause() : start()">
            <el-icon :size="34"><VideoPause v-if="state === 'recording'" /><Microphone v-else /></el-icon>
          </button>
        </div>
        <p class="record-state">{{ stateLabel }}</p>
        <strong class="record-time">{{ timeLabel }}</strong>
        <div class="signal-bars" :class="{ active: state === 'recording' }" aria-hidden="true"><i v-for="bar in 18" :key="bar"></i></div>
        <label class="record-consent"><input v-model="consent" type="checkbox" :disabled="active || processing" /> 已告知并取得录音同意 · 原音保留30天</label>
        <button class="finish-recording" :disabled="processing || finishing || disabled || (!current && !sessions.length)" @click="finish">结束录音，自动整理</button>
        <p v-if="queued" class="record-hint">正在保存录音，请勿关闭页面。</p>
      </div>
      <section class="panel symptoms-panel">
        <h3>患者症状 <small>待医师核实</small></h3>
        <p v-if="previewBusy" class="live-extraction" role="status"><i></i>正在提取症状……</p>
        <p v-if="!preview?.symptoms.length" class="empty-symptoms">点击左侧录音，症状关键词将在这里出现。</p>
        <p v-if="previewError" class="uncertainty">{{ previewError }}</p>
        <div class="symptom-chips">
          <div v-for="(symptom, index) in preview?.symptoms || []" :key="index" class="symptom-chip">
            <strong>{{ symptom.label }}</strong>
            <button v-for="(source, i) in symptom.source_ids" :key="source" :disabled="active || processing" @click="playSource(source)">回放依据{{ symptom.source_ids.length > 1 ? i + 1 : '' }}</button>
          </div>
        </div>
        <p v-if="preview?.uncertainty" class="uncertainty">识别疑点：{{ preview.uncertainty }}</p>
        <p v-if="doctorEdited && preview?.symptoms.length" class="quiet-note">正文已校对；关键词仍保留原音依据。</p>
        <AudioReview :key="playbackKey" :encounter-id="encounterId" :recording="selectedAudio" :start-ms="playStart" :end-ms="playEnd" />
      </section>
    </div>
    <div v-if="failure" class="speech-error" role="alert">{{ failure }} <button v-if="queued || (current && !current.closed)" @click="retryUpload">重试保存录音</button></div>
    <div v-for="session in sessions.filter(s => !s.closed && s.id !== current?.id)" :key="session.id" class="recovery-notice" role="alert">
      上次录音中断，部分内容可能未上传。
      <button :disabled="processing || active" @click="recover(session)">保留已上传部分并收尾</button>
    </div>
    <section class="panel voice-draft">
      <h3>{{ doctorEdited ? '问诊结果 · 医师校对' : '问诊信息整理稿' }}</h3>
      <textarea v-model="draft" aria-label="编辑问诊信息" :disabled="active || processing || disabled"
        placeholder="结束录音后自动整理，也可直接填写。请核对症状、否定表述与病程。"
        @input="doctorEdited = true; emit('change', draft)"></textarea>
    </section>
  </section>
</template>

<style scoped>
.voice-layout { display: grid; grid-template-columns: minmax(260px, .7fr) minmax(0, 1.6fr); gap: 20px; align-items: stretch; }
.recording-card { min-height: 380px; padding: 20px; }.record-consent { z-index: 1; font-size: 12px; color: #d4e5dc; margin: 18px 0 10px; line-height: 1.6; text-align: center; }
.signal-bars { margin-top: 12px; }.record-state { margin-top: 4px; }.sound-orbit { width: 170px; height: 170px; }
.recording-card .record-button { width: 88px; height: 88px; padding: 0; margin: 0; border: 5px solid rgba(255,255,255,.84); border-radius: 50%; }
.finish-recording { z-index: 1; border: 1px solid #9ebcb0; border-radius: 8px; padding: 10px 18px; color: #f2f8f4; background: #ffffff12; cursor: pointer; }
.symptoms-panel, .voice-draft { padding: 24px; }.symptoms-panel { min-width: 0; }h3 { margin: 0 0 18px; font-size: 19px; }small { font-size: 13px; font-weight: normal; color: #718175; margin-left: 10px; }
.empty-symptoms, .quiet-note { color: #75857b; }.symptom-chips { display: flex; flex-wrap: wrap; gap: 12px; }.symptom-chip { padding: 12px; background: #eff7f2; border: 1px solid #bfdcc9; border-radius: 10px; }
.symptom-chip strong { display: block; margin-bottom: 8px; font-size: 18px; }.symptom-chip button { background: transparent; border: 0; font-size: 13px; color: #286442; padding: 3px 8px 3px 0; cursor: pointer; }
.voice-draft { margin-top: 20px; }textarea { width: 100%; min-height: 260px; border: 1px solid #c4d4ca; border-radius: 8px; padding: 16px; font: inherit; font-size: 20px; line-height: 1.9; color: #223d2e; resize: vertical; }
.uncertainty, .speech-error, .recovery-notice { background: #fff4e8; color: #834619; padding: 12px; border-radius: 8px; margin-top: 12px; }
.live-extraction { color: #24704c; }.live-extraction i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: #2c8759; animation: extracting 1s infinite alternate; }
@keyframes extracting { to { opacity: .3; } }button:disabled { cursor: not-allowed; opacity: .5; }
@media(max-width: 700px) { .voice-layout { grid-template-columns: 1fr; }.recording-card { min-height: 350px; } }
@media(prefers-reduced-motion: reduce) { .signal-bars i, .sound-ring, .live-extraction i { animation: none !important; } }
</style>
