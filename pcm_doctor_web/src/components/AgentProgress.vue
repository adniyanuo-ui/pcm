<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
const props = defineProps<{ active: boolean; message: string }>()
const seconds = ref(0)
let timer: ReturnType<typeof setInterval> | undefined
watch(() => props.active, active => {
  clearInterval(timer)
  seconds.value = 0
  if (active) timer = setInterval(() => seconds.value++, 1000)
}, { immediate: true })
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <aside v-if="active" class="agent-progress" role="status" aria-live="polite" aria-busy="true">
    <span class="agent-pulse" aria-hidden="true"></span>
    <div><strong>坐诊助手正在工作</strong><p>{{ message }}</p>
      <small>已等待 {{ seconds }} 秒 · {{ seconds >= 60 ? '仍在等待处理结果，请勿重复点击或刷新。' : '请稍候，完成后会显示可编辑的草稿。' }}</small>
    </div>
    <div class="agent-motion" aria-hidden="true"><i></i></div>
  </aside>
</template>

<style scoped>
.agent-progress { position: sticky; top: 12px; z-index: 1100; display: flex; gap: 16px; align-items: center; padding: 20px 24px; margin: 12px 0; color: #174831; background: #e6f5ed; border: 2px solid #40976e; border-radius: 14px; box-shadow: 0 8px 24px #163d2420; overflow: hidden; }
.agent-progress strong { font-size: 20px; }.agent-progress p { margin: 6px 0; }.agent-progress small { color: #4a6256; }
.agent-pulse { width: 26px; height: 26px; flex-shrink: 0; border: 3px solid #a7d6bc; border-top-color: #216e48; border-radius: 50%; animation: spin 1s linear infinite; }
.agent-motion { position: absolute; bottom: 0; left: 0; width: 100%; height: 3px; }.agent-motion i { display: block; width: 25%; height: 100%; background: #438d61; animation: sweep 2s ease-in-out infinite alternate; }
@keyframes spin { to { transform: rotate(360deg); } } @keyframes sweep { to { transform: translateX(300%); } }
@media (prefers-reduced-motion: reduce) { .agent-pulse, .agent-motion i { animation: none; } }
</style>
