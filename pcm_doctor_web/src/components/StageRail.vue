<script setup lang="ts">
import { Check } from '@element-plus/icons-vue'
import type { StageDefinition } from '../types/consultation'

defineProps<{
  stages: StageDefinition[]
  current: number
  confirmed: boolean[]
}>()

defineEmits<{
  select: [index: number]
}>()
</script>

<template>
  <nav class="stage-rail" aria-label="诊疗流程">
    <button
      v-for="(stage, index) in stages"
      :key="stage.key"
      class="stage-button"
      :class="{ active: current === index, done: confirmed[index] }"
      type="button"
      @click="$emit('select', index)"
    >
      <span class="stage-mark">
        <el-icon v-if="confirmed[index]"><Check /></el-icon>
        <span v-else>{{ stage.shortLabel }}</span>
      </span>
      <span class="stage-copy">
        <strong>{{ stage.label }}</strong>
        <small>{{ stage.hint }}</small>
      </span>
      <span v-if="current === index" class="stage-current">当前</span>
    </button>
  </nav>
</template>
