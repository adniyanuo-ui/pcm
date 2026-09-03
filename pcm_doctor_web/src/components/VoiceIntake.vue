<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { EditPen, Microphone, VideoPause } from '@element-plus/icons-vue'
import { initialTranscript } from '../data/demo'

const emit = defineEmits<{
  confirm: []
}>()

const recording = ref(false)
const elapsed = ref(0)
const editing = ref(false)
const transcript = ref(initialTranscript.map((line) => ({ ...line })))
let timer: number | undefined

const timeLabel = computed(() => {
  const minutes = Math.floor(elapsed.value / 60).toString().padStart(2, '0')
  const seconds = (elapsed.value % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
})

const plainTranscript = computed({
  get: () => transcript.value.map((line) => `${line.role}：${line.content}`).join('\n'),
  set: (value: string) => {
    transcript.value = value.split('\n').filter(Boolean).map((line, index) => {
      const [possibleRole, ...content] = line.split('：')
      const role = possibleRole === '医生' ? '医生' : '患者'
      return { id: index + 1, role, time: '', content: content.join('：') || possibleRole }
    })
  },
})

function toggleRecording() {
  recording.value = !recording.value
  if (recording.value) {
    timer = window.setInterval(() => elapsed.value += 1, 1000)
  } else if (timer) {
    window.clearInterval(timer)
    timer = undefined
  }
}

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <section class="content-section intake-layout">
    <div class="recording-card" :class="{ recording }">
      <div class="sound-orbit">
        <span class="sound-ring ring-one"></span>
        <span class="sound-ring ring-two"></span>
        <button
          class="record-button"
          type="button"
          :aria-label="recording ? '暂停语音记录' : '继续语音记录'"
          @click="toggleRecording"
        >
          <el-icon :size="34"><VideoPause v-if="recording" /><Microphone v-else /></el-icon>
        </button>
      </div>
      <p class="record-state">{{ recording ? '正在记录医患对话' : '语音记录已暂停' }}</p>
      <strong class="record-time">{{ timeLabel }}</strong>
      <p class="record-hint">{{ recording ? '可随时暂停，已识别内容不会丢失' : '点击圆形按钮继续录音' }}</p>
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

      <textarea v-if="editing" v-model="plainTranscript" class="transcript-editor" aria-label="编辑医患对话"></textarea>
      <div v-else class="transcript-list">
        <div v-for="line in transcript" :key="line.id" class="transcript-line" :class="line.role === '医生' ? 'doctor' : 'patient'">
          <span class="speaker">{{ line.role }}</span>
          <p>{{ line.content }}</p>
          <time>{{ line.time }}</time>
        </div>
      </div>

      <div class="panel-footer">
        <span class="safe-note">原始对话始终保留，整理结果可由大夫修改</span>
        <button class="primary-button" type="button" @click="emit('confirm')">整理四诊信息</button>
      </div>
    </div>
  </section>
</template>
