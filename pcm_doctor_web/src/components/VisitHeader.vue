<script setup lang="ts">
import { ArrowLeft, MoreFilled, User } from '@element-plus/icons-vue'

defineEmits<{
  back: []
}>()
</script>

<template>
  <header class="visit-header">
    <div class="brand-block">
      <div class="brand-seal">辅</div>
      <div>
        <p class="brand-eyebrow">AI 辅助中医诊疗</p>
        <h1>坐诊工作台</h1>
      </div>
    </div>

    <div class="patient-strip" aria-label="当前患者">
      <span class="patient-avatar"><el-icon><User /></el-icon></span>
      <div>
        <div class="patient-line">
          <strong>胡女士</strong>
          <span>42岁</span>
          <span>复诊</span>
          <em>演示病例</em>
        </div>
        <p>就诊号 20260903-008 · 今日 09:38 到诊</p>
      </div>
    </div>

    <div class="header-actions">
      <span class="draft-badge"><i></i> AI 草稿 · 待医师确认</span>
      <button class="icon-button" type="button" aria-label="更多"><el-icon><MoreFilled /></el-icon></button>
      <button class="quiet-button" type="button" @click="$emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        返回患者列表
      </button>
    </div>
  </header>
</template>
