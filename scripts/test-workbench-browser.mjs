// Real Chrome interaction using the built-in Node WebSocket API; no browser dependency.
import { spawn } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import assert from 'node:assert/strict'

const profile = await mkdtemp(join(tmpdir(), 'pcm-chrome-'))
const chrome = spawn('/usr/bin/google-chrome', ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage',
  ...(process.env.PCM_REAL_SPEECH_TEST === '1' ? ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] : []),
  '--remote-debugging-port=9228', '--remote-debugging-address=127.0.0.1', '--user-data-dir=' + profile, 'about:blank'], { stdio: 'ignore' })
let socket
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
try {
  let targets
  for (let i = 0; i < 80; i++) {
    try { targets = await (await fetch('http://127.0.0.1:9228/json')).json(); break } catch { await delay(250) }
  }
  assert.ok(targets, 'Chrome failed to start')
  socket = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl)
  await new Promise(resolve => socket.addEventListener('open', resolve, { once: true }))
  let id = 0
  const pending = new Map()
  const errors = []
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text)
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id)
      pending.delete(message.id)
      message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result)
    }
  })
  function cdp(method, params = {}) {
    return new Promise((resolve, reject) => { const key = ++id; pending.set(key, { resolve, reject }); socket.send(JSON.stringify({ id: key, method, params })) })
  }
  async function evaluate(expression) {
    const result = await cdp('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text)
    return result.result.value
  }
  async function waitFor(expression, timeout = 120000) {
    const start = Date.now()
    while (Date.now() - start < timeout) {
      if (await evaluate(expression)) return
      const error = await evaluate("document.querySelector('.live-error, .speech-error')?.textContent")
      if (error) throw new Error(error)
      await delay(300)
    }
    throw new Error('Browser timed out: ' + expression)
  }
  async function click(text) {
    const name = JSON.stringify(text)
    await waitFor(`Array.from(document.querySelectorAll('button')).some(b => b.textContent.trim() === ${name} && !b.disabled)`)
    await evaluate(`Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === ${name}).click()`)
    await delay(80)
  }
  async function fill(selector, value) {
    await evaluate(`{ const el = document.querySelector(${JSON.stringify(selector)}); if (!el) throw Error('Missing input'); el.value = ${JSON.stringify(value)}; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }`)
  }
  async function login() {
    await waitFor("!!document.querySelector('input[autocomplete=username]')")
    await fill('input[autocomplete=username]', process.env.PCM_BROWSER_USERNAME)
    await fill('input[autocomplete=current-password]', process.env.PCM_BROWSER_PASSWORD)
    await click('进入坐诊工作台')
    await waitFor("document.body.innerText.includes('创建患者与就诊')")
  }
  await cdp('Runtime.enable')
  await cdp('Page.navigate', { url: 'http://127.0.0.1:5176' })
  await login()
  await fill('form.live-fields input', '虚构浏览器患者')
  await fill('form.live-fields input[type=number]', '30')
  await click('创建就诊')
  await waitFor("document.body.innerText.includes('医患对话')")
  if (process.env.PCM_REAL_SPEECH_TEST === '1') {
    for (let round = 0; round < 2; round++) {
      await evaluate("document.querySelector('button[aria-label=\"开始语音记录\"]').click()")
      await waitFor("document.querySelector('.record-state')?.textContent.includes('正在记录')")
      await delay(2000)
      await evaluate("document.querySelector('button[aria-label=\"暂停语音记录\"]').click()")
      await waitFor("document.querySelector('.record-state')?.textContent.includes('已暂停')")
      assert.equal(await evaluate("document.querySelector('.speech-error')?.textContent || ''"), '')
    }
    console.log('PASS: real NLS token, browser audio capture with synthetic microphone, WebSocket start/pause/resume/stop')
  }
  await click('校对原文')
  await fill('textarea[aria-label="编辑医患对话"]', '患者：我是虚构测试患者，食少便溏两周，乏力，无其他已知资料。医生：舌淡，脉弱。')
  await click('校对完成，整理四诊')
  await waitFor("document.body.innerText.includes('确认四诊，生成辨证')")
  await click('确认四诊，生成辨证')
  await waitFor("document.body.innerText.includes('确认治法，检索基础方')")
  await click('确认治法，检索基础方')
  await waitFor("document.querySelectorAll('.formula-card').length > 0")
  await evaluate("document.querySelector('.formula-card').click()")
  await click('采用此方，编辑处方')
  await waitFor("document.body.innerText.includes('医师填写处方')")
  await click('添加药味')
  await fill('.live-fields input', '虚构软件测试药味')
  await fill('.live-fields label:nth-child(2) input', '1g')
  await fill('.live-fields label:nth-child(3) input', '仅验证软件')
  await fill('section.live-panel > .live-fields:last-of-type label:nth-child(2) input', '仅验证保存，不用于治疗')
  await click('确认处方，生成病历')
  await waitFor("!!document.querySelector('.live-record')?.value")
  const record = await evaluate("document.querySelector('.live-record').value")
  assert.ok(record.includes('虚构浏览器患者'))
  assert.ok(record.includes('未提供'))
  await evaluate("document.querySelector('input[type=checkbox]').click()")
  await click('医师确认并保存')
  await waitFor("document.body.innerText.includes('医师已确认并保存。')")
  await cdp('Page.reload')
  await waitFor("document.body.innerText.includes('打开就诊')")
  const openText = await evaluate("Array.from(document.querySelectorAll('button')).find(b => b.textContent.startsWith('打开就诊')).textContent.trim()")
  await click(openText)
  await waitFor("document.body.innerText.includes('医师已确认并保存。')")
  assert.equal(await evaluate("document.querySelector('.live-record').value"), record)
  await click('退出登录')
  await login()
  await click(openText)
  await waitFor("document.body.innerText.includes('医师已确认并保存。')")
  assert.equal(await evaluate("document.querySelector('.live-record').value"), record)
  assert.deepEqual(errors, [])
  console.log('PASS: real login, create, organize, analyze, RAG, prescription, confirm, reload, logout/login recovery; no browser exceptions')
} finally {
  socket?.close()
  chrome.kill('SIGTERM')
  await new Promise(resolve => chrome.once('exit', resolve))
  await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 })
}
