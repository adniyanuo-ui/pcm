<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { EditPen, Microphone, VideoPause, Warning } from '@element-plus/icons-vue'
import { initialTranscript } from '../data/demo'
import {
  AliyunRealtimeTranscriber,
  type SpeechSessionState,
  type TranscriptUpdate,
} from '../services/aliyunNls'
import type { TranscriptLine } from '../types/consultation'

const props = withDefaults(defineProps<{
  liveSpeech?: boolean
}>(), {
  liveSpeech: false,
})

const emit = defineEmits<{
  confirm: []
  transcriptChange: [text: string]
}>()

const state = ref<SpeechSessionState>('idle')
const elapsed = ref(0)
const editing = ref(false)
const errorMessage = ref('')
const transcript = ref<TranscriptLine[]>(
  props.liveSpeech ? [] : initialTranscript.map((line) => ({ ...line })),
)
let timer: number | undefined
let transcriber: AliyunRealtimeTranscriber | undefined
let currentSessionBase = 0

const recording = computed(() => state.value === 'recording')
const busy = computed(() => state.value === 'connecting' || state.value === 'stopping')
const hasTranscript = computed(() => transcript.value.some((line) => line.content.trim()))

const timeLabel = computed(() => {
  const minutes = Math.floor(elapsed.value / 60).toString().padStart(2, '0')
  const seconds = (elapsed.value % 60).toString().padStart(2, '0')
  return minutes + ':' + seconds
})

const stateLabel = computed(() => {
  const labels: Record<SpeechSessionState, string> = {
    idle: props.liveSpeech ? '准备开始实时转写' : '语音记录已暂停',
    connecting: '正在连接语音服务',
    recording: '正在记录医患对话',
    stopping: '正在保存最后一句',
    paused: '语音记录已暂停',
    error: '录音暂不可用',
  }
  return labels[state.value]
})

const stateHint = computed(() => {
  if (errorMessage.value) return errorMessage.value
  if (state.value === 'connecting') return '首次使用时，请在浏览器提示中允许麦克风'
  if (state.value === 'recording') return '可随时暂停，已识别内容不会丢失'
  if (props.liveSpeech) return '点击圆形按钮开始录音并实时转写'
  return '当前为界面演示模式'
})

const plainTranscript = computed({
  get: () => transcript.value.map((line) => line.role + '：' + line.content).join('\n'),
  set: (value: string) => {
    transcript.value = value.split('\n').filter(Boolean).map((line, index) => {
      const [possibleRole, ...content] = line.split('：')
      const role: TranscriptLine['role'] = possibleRole === '医生'
        ? '医生'
        : possibleRole === '患者'
          ? '患者'
          : '对话'
      return {
        id: index + 1,
        role,
        time: '',
        content: content.join('：') || possibleRole,
      }
    })
    notifyTranscriptChange()
  },
})

function nowLabel(): string {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date())
}

function notifyTranscriptChange() {
  emit('transcriptChange', plainTranscript.value)
}

function updateTranscript(update: TranscriptUpdate) {
  const id = currentSessionBase + update.index
  const existing = transcript.value.find((line) => line.id === id)
  if (existing) {
    existing.content = update.text
  } else {
    transcript.value.push({
      id,
      role: '对话',
      time: nowLabel(),
      content: update.text,
    })
    transcript.value.sort((left, right) => left.id - right.id)
  }
  notifyTranscriptChange()
}

function startTimer() {
  if (timer) return
  timer = window.setInterval(() => elapsed.value += 1, 1000)
}

function stopTimer() {
  if (timer) window.clearInterval(timer)
  timer = undefined
}

function createTranscriber() {
  currentSessionBase = Math.max(0, ...transcript.value.map((line) => line.id))
  transcriber = new AliyunRealtimeTranscriber({
    onState: (nextState) => {
      state.value = nextState
      if (nextState === 'recording') startTimer()
      if (nextState !== 'recording') stopTimer()
    },
    onTranscript: updateTranscript,
    onError: (message) => {
      errorMessage.value = message
      stopTimer()
    },
  })
}

async function startRecording() {
  errorMessage.value = ''
  if (!props.liveSpeech) {
    state.value = 'recording'
    startTimer()
    return
  }
  createTranscriber()
  try {
    await transcriber?.start()
  } catch {
    // 服务类已将可读错误写入界面。
  }
}

async function stopRecording() {
  stopTimer()
  if (!props.liveSpeech) {
    state.value = 'paused'
    return
  }
  await transcriber?.stop()
  transcriber = undefined
}

async function toggleRecording() {
  if (busy.value) return
  if (recording.value) {
    await stopRecording()
  } else {
    await startRecording()
  }
}

onBeforeUnmount(() => {
  stopTimer()
  void transcriber?.stop()
})
</script>

<template>
  <section class="content-section intake-layout">
    <div class="recording-card" :class="{ recording, error: state === 'error' }">
      <span class="speech-mode-badge">{{ liveSpeech ? '实时转写' : '界面演示' }}</span>
      <div class="sound-orbit">
        <span class="sound-ring ring-one"></span>
        <span class="sound-ring ring-two"></span>
        <button
          class="record-button"
          type="button"
          :disabled="busy"
          :aria-label="recording ? '暂停语音记录' : '开始语音记录'"
          @click="toggleRecording"
        >
          <el-icon :size="34"><VideoPause v-if="recording" /><Microphone v-else /></el-icon>
        </button>
      </div>
      <p class="record-state">{{ stateLabel }}</p>
      <strong class="record-time">{{ timeLabel }}</strong>
      <p class="record-hint">{{ stateHint }}</p>
      <div class="signal-bars" :class="{ active: recording }" aria-hidden="true">
        <i v-for="bar in 18" :key="bar"></i>
      </div>
    </div>

    <div class="panel transcript-panel">
      <div class="panel-heading">
        <div>
          <span class="section-kicker">原始证据</span>
          <h2>医患对话</h2>
        </div>
        <button class="text-button" type="button" @click="editing = !editing">
          <el-icon><EditPen /></el-icon>
          {{ editing ? '完成编辑' : '校对原文' }}
        </button>
      </div>

      <textarea
        v-if="editing"
        v-model="plainTranscript"
        class="transcript-editor"
        aria-label="编辑医患对话"
        placeholder="可在这里手工补充或修正录音原文……"
      ></textarea>
      <div v-else class="transcript-list">
        <div v-if="!transcript.length" class="empty-transcript">
          <el-icon><Microphone /></el-icon>
          <strong>还没有对话内容</strong>
          <p>点击左侧录音按钮，转写文字会逐句出现在这里。</p>
        </div>
        <div
          v-for="line in transcript"
          :key="line.id"
          class="transcript-line"
          :class="line.role === '医生' ? 'doctor' : line.role === '对话' ? 'dialogue' : 'patient'"
        >
          <span class="speaker">{{ line.role }}</span>
          <p>{{ line.content || '正在识别…' }}</p>
          <time>{{ line.time }}</time>
        </div>
      </div>

      <div v-if="errorMessage" class="speech-error">
        <el-icon><Warning /></el-icon>
        <span>{{ errorMessage }}</span>
      </div>
      <div class="panel-footer">
        <span class="safe-note">不保存原始音频；转写原文由大夫校对后进入四诊整理</span>
        <button class="primary-button" type="button" :disabled="!hasTranscript" @click="emit('confirm')">整理四诊信息</button>
      </div>
    </div>
  </section>
</template>
