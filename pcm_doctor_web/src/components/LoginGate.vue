<script setup lang="ts">
import { ref } from 'vue'
import { Lock, User } from '@element-plus/icons-vue'
import { loginCms } from '../api/rag'

const emit = defineEmits<{
  authenticated: []
}>()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  if (!username.value.trim() || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await loginCms(username.value.trim(), password.value)
    emit('authenticated')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-intro">
      <div class="login-brand"><span>辅</span><p>AI 辅助中医诊疗<small>临床决策支持工具</small></p></div>
      <div class="intro-copy">
        <em>稳定 · 有据 · 可修改</em>
        <h1>让每一次辨证<br />都完整走完。</h1>
        <p>记录医患对话，梳理四诊信息，从辞典中检索候选基础方，最后由大夫修改并确认。</p>
      </div>
      <div class="intro-flow"><span>四诊合参</span><i></i><span>辨证求机</span><i></i><span>以法统方</span></div>
    </section>

    <section class="login-form-side">
      <form class="login-card" @submit.prevent="submit">
        <span class="section-kicker">医生工作台</span>
        <h2>欢迎回来</h2>
        <p>使用诊所分配的医生账号登录</p>

        <label>
          <span>账号</span>
          <div class="login-input"><el-icon><User /></el-icon><input v-model="username" autocomplete="username" placeholder="请输入医生账号" /></div>
        </label>
        <label>
          <span>密码</span>
          <div class="login-input"><el-icon><Lock /></el-icon><input v-model="password" type="password" autocomplete="current-password" placeholder="请输入密码" /></div>
        </label>

        <div v-if="error" class="login-error" role="alert">{{ error }}</div>
        <button class="login-submit" type="submit" :disabled="loading">{{ loading ? '正在登录…' : '进入坐诊工作台' }}</button>
        <small>本系统仅供医疗机构内已授权医师使用</small>
      </form>
    </section>
  </main>
</template>
