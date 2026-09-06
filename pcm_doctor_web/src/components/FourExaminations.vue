<script setup lang="ts">
import { CircleCheck, EditPen } from '@element-plus/icons-vue'
import type { ExaminationSection } from '../types/consultation'

const sections = defineModel<ExaminationSection[]>({ required: true })

defineEmits<{
  changed: []
  confirm: []
}>()
</script>

<template>
  <section class="content-section">
    <div class="section-heading-row">
      <div>
        <span class="section-kicker">第 2 步 · 信息必须由大夫确认</span>
        <h2>四诊合参</h2>
        <p>系统已将录音内容带入“问诊”，望、闻、切诊由大夫补充；所有内容都可直接修改。</p>
      </div>
      <span class="source-legend"><i></i> 带来源记录</span>
    </div>

    <div class="examination-grid">
      <article v-for="section in sections" :key="section.key" class="examination-card">
        <div class="examination-head">
          <span class="examination-mark">{{ section.key }}</span>
          <div>
            <h3>{{ section.title }}</h3>
            <span>{{ section.source }}</span>
          </div>
          <el-icon class="edit-icon"><EditPen /></el-icon>
        </div>
        <textarea
          v-model="section.value"
          :placeholder="section.placeholder"
          @input="$emit('changed')"
        ></textarea>
      </article>
    </div>


    <div class="action-row">
      <span><el-icon><CircleCheck /></el-icon> 四诊信息将作为后续检索的唯一患者事实来源</span>
      <button class="primary-button" type="button" @click="$emit('confirm')">确认四诊，进入辨证</button>
    </div>
  </section>
</template>
