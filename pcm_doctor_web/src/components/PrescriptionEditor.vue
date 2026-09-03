<script setup lang="ts">
import { computed } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import type { PrescriptionItem } from '../types/consultation'

const items = defineModel<PrescriptionItem[]>({ required: true })

defineEmits<{
  changed: []
  confirm: []
}>()

const nextId = computed(() => Math.max(0, ...items.value.map((item) => item.id)) + 1)

function addItem() {
  items.value.push({ id: nextId.value, herb: '', dose: '', note: '' })
}

function removeItem(id: number) {
  items.value = items.value.filter((item) => item.id !== id)
}
</script>

<template>
  <div class="prescription-panel">
    <div class="panel-heading">
      <div>
        <span class="section-kicker">医师编辑区</span>
        <h2>处方草稿</h2>
      </div>
      <span class="draft-label">AI 草稿</span>
    </div>

    <div class="prescription-table">
      <div class="prescription-row table-head">
        <span>药味</span><span>剂量</span><span>加减依据 / 用药说明</span><span></span>
      </div>
      <div v-for="item in items" :key="item.id" class="prescription-row">
        <input v-model="item.herb" aria-label="药味" @input="$emit('changed')" />
        <input v-model="item.dose" aria-label="剂量" @input="$emit('changed')" />
        <input v-model="item.note" aria-label="用药说明" @input="$emit('changed')" />
        <button type="button" aria-label="删除药味" @click="removeItem(item.id)"><el-icon><Delete /></el-icon></button>
      </div>
    </div>

    <button class="add-herb-button" type="button" @click="addItem">
      <el-icon><Plus /></el-icon> 添加药味
    </button>

    <div class="prescription-settings">
      <label><span>剂数</span><input value="7" /><em>剂</em></label>
      <label><span>用法</span><input value="水煎服，每日1剂，早晚分服" /></label>
      <label><span>医嘱</span><input value="饮食清淡，忌生冷；如有不适及时复诊" /></label>
    </div>

    <div class="action-row prescription-action">
      <span>处方仍为草稿，进入病历后还可以返回修改</span>
      <button class="primary-button" type="button" @click="$emit('confirm')">确认处方，生成病历</button>
    </div>
  </div>
</template>
