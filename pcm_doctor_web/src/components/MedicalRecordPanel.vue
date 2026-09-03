<script setup lang="ts">
import { ref } from 'vue'
import { DocumentChecked, Printer, Warning } from '@element-plus/icons-vue'

defineEmits<{
  confirm: []
}>()

const editing = ref(false)
const acknowledged = ref(false)
const recordText = ref(`主诉：乏力、纳差伴便溏2月余。

现病史：患者近2月来无明显诱因出现乏力、食欲减退，大便日行2—3次、质稀，食凉后加重，饭后偶有腹胀，偶感手足凉。饮水正常。

中医四诊：神清，面色少华，语声偏低。舌质淡，舌体略胖有齿痕，苔薄白。脉细弱，右关尤甚。

辨证：脾胃气虚证，兼轻度寒象。
病机：脾胃气虚，运化失健，清阳不振，故见纳差、便溏、腹胀、乏力；气虚失充则面色少华、语声低微、脉细弱。
治法：益气健脾，和胃止泻，酌情温中。

方药：四君子汤加减。党参12g、炒白术12g、茯苓12g、炙甘草6g、陈皮6g。7剂，水煎服，每日1剂，早晚分服。

医嘱：饮食清淡，忌生冷；观察大便次数、食欲及腹胀变化，如有不适及时复诊。`)
</script>

<template>
  <section class="content-section record-layout">
    <div class="section-heading-row">
      <div>
        <span class="section-kicker">第 5 步 · 只使用已确认信息</span>
        <h2>门诊病历草稿</h2>
        <p>系统已检查理、法、方、药的一致性；缺失信息不会自动编造。</p>
      </div>
      <div class="record-actions">
        <button class="text-button" type="button" @click="editing = !editing">{{ editing ? '完成编辑' : '编辑病历' }}</button>
        <button class="text-button" type="button"><el-icon><Printer /></el-icon> 打印预览</button>
      </div>
    </div>

    <div class="record-workspace">
      <div class="record-paper">
        <div class="record-paper-head">
          <div><span>中医门诊病历</span><em>AI 草稿</em></div>
          <small>就诊号：20260903-008</small>
        </div>
        <textarea v-if="editing" v-model="recordText" class="record-editor"></textarea>
        <div v-else class="record-body">
          <p v-for="paragraph in recordText.split('\n').filter(Boolean)" :key="paragraph">{{ paragraph }}</p>
        </div>
      </div>

      <aside class="record-checks">
        <h3>完整性检查</h3>
        <div class="check-item success"><el-icon><DocumentChecked /></el-icon><span><strong>诊疗逻辑一致</strong><small>病机、治法、基础方相互对应</small></span></div>
        <div class="check-item success"><el-icon><DocumentChecked /></el-icon><span><strong>处方信息完整</strong><small>药味、剂量、剂数、用法已填写</small></span></div>
        <div class="check-item warning"><el-icon><Warning /></el-icon><span><strong>生命体征待补</strong><small>T、P、R、BP 未记录，系统未代填</small></span></div>
        <div class="check-item warning"><el-icon><Warning /></el-icon><span><strong>辅助检查待确认</strong><small>尚未提供检查报告</small></span></div>
      </aside>
    </div>

    <div class="final-confirm">
      <label><input v-model="acknowledged" type="checkbox" /> 我已核对四诊信息、辨证结论与处方，本病历由我确认</label>
      <button class="primary-button" type="button" :disabled="!acknowledged" @click="$emit('confirm')">医师确认并保存</button>
    </div>
  </section>
</template>
