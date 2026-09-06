<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { audioBlob, type AudioChunk, type Recording } from '../api/voice'
const props = defineProps<{ encounterId: number; recording: Recording | null; startMs?: number; endMs?: number }>()
const player = ref<HTMLAudioElement>()
const source = ref('')
const error = ref('')
const loading = ref(false)
let generation = 0
let position = 0
let expiryTimer: ReturnType<typeof setTimeout> | undefined
const chunks = computed(() => props.recording?.chunks.filter(c => c.start_ms + c.duration_ms > (props.startMs || 0) && c.start_ms < (props.endMs ?? Infinity)) || [])
function release() {
  player.value?.pause()
  if (source.value) URL.revokeObjectURL(source.value)
  source.value = ''
}
async function load(chunk: AudioChunk | undefined) {
  const current = ++generation
  release(); error.value = ''
  if (!chunk || !chunk.available || props.recording?.expired) { error.value = '该录音已到期或尚未上传，无法回放。'; return }
  loading.value = true
  try {
    const blob = await audioBlob(props.encounterId, chunk.id)
    if (generation !== current) return
    source.value = URL.createObjectURL(blob)
    await nextTick()
  } catch (e) { if (generation === current) error.value = e instanceof Error ? e.message : '录音回放失败' }
  finally { if (generation === current) loading.value = false }
}
function ready() {
  const chunk = chunks.value[position]
  if (!player.value || !chunk) return
  player.value.currentTime = Math.max(0, ((props.startMs || 0) - chunk.start_ms) / 1000)
  void player.value.play().catch(() => { /* Browser may require pressing the visible play button. */ })
}
function timeUpdate() {
  const chunk = chunks.value[position]
  if (player.value && props.endMs && chunk && player.value.currentTime * 1000 + chunk.start_ms >= props.endMs) player.value.pause()
}
function next() {
  if (position + 1 < chunks.value.length) { position++; void load(chunks.value[position]) }
}
function enforceExpiry() {
  if (!props.recording) return
  const remaining = new Date(props.recording.expires_at).getTime() - Date.now()
  if (remaining <= 0) { generation++; release(); error.value = '录音已到期，回放已停止。'; return }
  expiryTimer = setTimeout(enforceExpiry, Math.min(remaining, 86400000))
}
watch(() => [props.recording?.id, props.startMs, props.endMs], () => {
  clearTimeout(expiryTimer)
  generation++; release(); position = 0
  if (props.recording) {
    const remaining = new Date(props.recording.expires_at).getTime() - Date.now()
    if (remaining <= 0) { error.value = '该录音已到期，无法回放。'; return }
    enforceExpiry()
    void load(chunks.value[0])
  }
}, { immediate: true })
onBeforeUnmount(() => { clearTimeout(expiryTimer); generation++; release() })
</script>

<template>
  <div v-if="recording" class="audio-review">
    <p>原音复核 · {{ Math.floor((startMs || 0) / 1000) }} 秒起 <span v-if="endMs">至 {{ Math.ceil(endMs / 1000) }} 秒</span></p>
    <p v-if="loading" role="status">正在读取私有录音……</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <audio v-if="source" ref="player" :src="source" controls @loadedmetadata="ready" @ended="next" @timeupdate="timeUpdate"></audio>
    <small>录音于 {{ new Date(recording.expires_at).toLocaleString() }} 到期；到期后文字记录仍保留。</small>
  </div>
</template>
<style scoped>.audio-review { padding: 14px; margin: 12px 0; border-radius: 10px; background: #f1f6f2; }audio { display: block; width: 100%; margin: 10px 0; }small { color: #617466; }</style>
