// Real Chrome interaction using the built-in Node WebSocket API; no browser dependency.
import { spawn } from 'node:child_process'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import assert from 'node:assert/strict'

const profile = await mkdtemp(join(tmpdir(), 'pcm-chrome-'))
const chrome = spawn('/usr/bin/google-chrome', ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage',
  ...((process.env.PCM_REAL_SPEECH_TEST === '1' || process.env.PCM_FIXTURE_SPEECH_TEST === '1') ? ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] : []),
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
  async function waitFor(expression, timeout = 120000, expectPageError = false) {
    const start = Date.now()
    while (Date.now() - start < timeout) {
      if (await evaluate(expression)) return
      const error = await evaluate("document.querySelector('.live-error, .speech-error')?.textContent")
      if (error && !expectPageError) throw new Error(error)
      await delay(300)
    }
    throw new Error('Browser timed out: ' + expression)
  }
  async function click(text) {
    const name = JSON.stringify(text)
    await waitFor(`Array.from(document.querySelectorAll('button')).some(b => b.textContent.trim() === ${name} && !b.matches(':disabled'))`)
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
  async function screenshot(name) {
    if (!process.env.PCM_SCREENSHOT_DIR) return
    const shot = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
    await writeFile(join(process.env.PCM_SCREENSHOT_DIR, name + '.png'), Buffer.from(shot.data, 'base64'))
  }
  await cdp('Runtime.enable')
  await cdp('Page.enable')
  await cdp('Emulation.setDeviceMetricsOverride', { width: 1280, height: 1000, deviceScaleFactor: 1, mobile: false })
  if (process.env.PCM_FIXTURE_SPEECH_TEST === '1') {
    await cdp('Page.addScriptToEvaluateOnNewDocument', { source: `
      const NativeWebSocket = window.WebSocket;
      window.WebSocket = class extends EventTarget {
        static pcmFixture = true;
        static OPEN = 1; static CLOSED = 3; readyState = 1;
        constructor(url, protocols) {
          super();
          if (!String(url).includes('speech-fixture.invalid')) return new NativeWebSocket(url, protocols);
          setTimeout(() => this.onopen?.(), 0);
        }
        message(name, payload = {}) { this.onmessage?.({ data: JSON.stringify({ header: { name, status: 20000000 }, payload }) }); }
        send(data) {
          if (typeof data !== 'string') return;
          const name = JSON.parse(data).header.name;
          if (name === 'StartTranscription') {
            this.message('TranscriptionStarted');
            this.resultTimer = setTimeout(() => this.message('SentenceEnd', { index: 1, result: '虚构患者：食少便溏两周，没有发热。', begin_time: 0, time: 1500 }), 1600);
          }
          if (name === 'StopTranscription') this.message('TranscriptionCompleted');
        }
        close() { clearTimeout(this.resultTimer); this.readyState = 3; this.onclose?.(); }
      };
    ` })
  }
  await cdp('Page.navigate', { url: 'http://127.0.0.1:5176' })
  await login()
  if (process.env.PCM_FIXTURE_SPEECH_TEST === '1') assert.equal(await evaluate('window.WebSocket.pcmFixture'), true, 'speech fixture injection')
  await fill('form.live-fields input', '虚构浏览器患者')
  await fill('form.live-fields input[type=number]', '30')
  await click('创建就诊')
  await waitFor("document.body.innerText.includes('问诊信息整理稿')")
  assert.equal(await evaluate("/deepseek|qwen|最近生成模型|草稿模型/i.test(document.body.innerText)"), false)
  assert.equal(await evaluate("document.querySelectorAll('.compact-stages button').length"), 4)
  assert.equal(await evaluate("/原始录音复核|查看保存与修改历史|四诊合参/.test(document.body.innerText)"), false)
  assert.ok(await evaluate("document.querySelector('.recording-card').getBoundingClientRect().right < document.querySelector('.symptoms-panel').getBoundingClientRect().left"), 'recorder remains left of symptoms')
  assert.equal(await evaluate("document.body.innerText.includes('就诊信息整理稿')"), false)
  assert.ok(await evaluate("parseFloat(getComputedStyle(document.querySelector('textarea[aria-label=\"编辑问诊信息\"]')).fontSize) >= 19"))
  assert.equal(await evaluate("/保存问诊记录|保存修改|保存处方|保存草稿/.test(document.body.innerText)"), false)
  if (process.env.PCM_REAL_SPEECH_TEST === '1' || process.env.PCM_FIXTURE_SPEECH_TEST === '1') {
    await evaluate("document.querySelector('.record-consent input').click()")
    for (let round = 0; round < 2; round++) {
      await evaluate("document.querySelector('button[aria-label=\"开始语音记录\"]').click()")
      await waitFor("document.querySelector('.record-state')?.textContent.includes('正在记录')")
      await delay(round === 0 && process.env.PCM_FIXTURE_SPEECH_TEST === '1' ? 6500 : 2200)
      if (round === 0 && process.env.PCM_FIXTURE_SPEECH_TEST === '1') {
        await waitFor("document.querySelectorAll('.symptom-chip').length > 0")
        assert.equal(await evaluate("document.body.innerText.includes('虚构患者：食少便溏两周，没有发热。')"), false)
      }
      if (round === 1 && process.env.PCM_FIXTURE_SPEECH_TEST === '1') break
      await evaluate("document.querySelector('button[aria-label=\"暂停语音记录\"]').click()")
      await waitFor("document.querySelector('.record-state')?.textContent.includes('已暂停')")
      await waitFor("!document.querySelector('button[aria-label=\"开始语音记录\"]').disabled")
      assert.equal(await evaluate("document.querySelector('.speech-error')?.textContent || ''"), '')
    }
    console.log('PASS: browser audio capture with synthetic microphone, authenticated uploads, start/pause/resume/stop')
  }
  if (process.env.PCM_FIXTURE_SPEECH_TEST === '1') {
    const finalStarted = Date.now()
    await click('结束录音，自动整理')
    await waitFor("document.querySelector('textarea[aria-label=\"编辑问诊信息\"]').value.length > 0 && !document.querySelector('.agent-progress')")
    console.log('Voice final UI elapsed seconds: ' + ((Date.now() - finalStarted) / 1000).toFixed(2))
    assert.ok(Date.now() - finalStarted < 60000, 'final summary sample should finish within one minute')
    const replay = await evaluate("Array.from(document.querySelectorAll('.symptom-chip button')).find(b => !b.disabled)?.textContent.trim()")
    assert.ok(replay, 'final voice summary must include source-linked symptoms')
    await click(replay)
    await waitFor("!!document.querySelector('audio')?.src")
    console.log('PASS: automatic final voice summary and symptom-linked private audio playback')
  }
  await fill('textarea[aria-label="编辑问诊信息"]', '我是虚构测试患者，食少便溏两周，乏力，无其他已知资料。')
  await fill('textarea[aria-label="望诊补充"]', '舌淡')
  await fill('textarea[aria-label="切诊补充"]', '脉弱')
  await screenshot('pcm-intake')
  await cdp('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true })
  assert.ok(await evaluate("document.documentElement.scrollWidth <= 390"), 'mobile intake must not overflow horizontally')
  await screenshot('pcm-intake-mobile')
  await cdp('Emulation.setDeviceMetricsOverride', { width: 1280, height: 1000, deviceScaleFactor: 1, mobile: false })
  await click('确认问诊，生成辨证')
  await waitFor("document.body.innerText.includes('确认辨证论治，检索基础方')")
  assert.equal(await evaluate("document.querySelectorAll('.analysis-layer').length"), 3)
  assert.equal(await evaluate("document.querySelectorAll('.analysis-layer')[0].textContent.includes('辨病因、病位、病性，察病势')"), true)
  assert.equal(await evaluate("document.querySelectorAll('.analysis-layer')[1].textContent.includes('推演、归纳病机，确定证型')"), true)
  assert.equal(await evaluate("document.querySelectorAll('.analysis-layer')[2].textContent.includes('确立治则、治法')"), true)
  assert.equal(await evaluate("document.querySelector('.analysis-evidence').open"), false)
  assert.equal(await evaluate("document.body.innerText.includes('待追问项')"), false)
  assert.equal(await evaluate("/第一层|核心枢纽层|归纳层/.test(document.body.innerText)"), false)
  await screenshot('pcm-analysis')
  await click('确认辨证论治，检索基础方')
  await waitFor("document.querySelectorAll('.formula-card').length > 2")
  await evaluate("document.querySelectorAll('.formula-card')[0].click(); document.querySelectorAll('.formula-card')[1].click()")
  await click('查看完整方剂')
  await waitFor("document.body.innerText.includes('完整基础方 · 辞典原文')")
  assert.ok(await evaluate("Array.from(document.querySelectorAll('.source-content dt')).some(e => e.textContent === '宜忌')"))
  await evaluate("document.querySelector('.source-dialog .el-dialog__headerbtn').click()")
  const scrollBeforeAdopt = await evaluate('window.scrollY')
  await click('带入所选基础方')
  await waitFor("!!document.querySelector('.prescription-editor')")
  assert.equal(await evaluate("document.querySelectorAll('.formula-card.adopted').length"), 2)
  assert.ok(await evaluate("Boolean(document.querySelector('.content-section').compareDocumentPosition(document.querySelector('.prescription-editor')) & Node.DOCUMENT_POSITION_FOLLOWING)"), 'doctor editor must remain below formula list on the same page')
  assert.ok(Math.abs(await evaluate('window.scrollY') - scrollBeforeAdopt) < 3, 'adopting formulas must not auto-scroll')
  assert.equal(await evaluate("/添加药味|辞典组成原文|医师加减说明|煎服方法（必填）|查看保存与修改历史/.test(document.body.innerText)"), false)
  await fill('textarea[aria-label="编辑处方"]', '医师自定义修改标记，不得被后续选方覆盖。')
  await evaluate("document.querySelectorAll('.formula-card')[2].click()")
  await click('带入所选基础方')
  await waitFor("document.querySelectorAll('.formula-card.adopted').length === 3")
  assert.ok(await evaluate("document.querySelector('textarea[aria-label=\"编辑处方\"]').value.includes('医师自定义修改标记，不得被后续选方覆盖。')"))
  await screenshot('pcm-prescription')
  await fill('textarea[aria-label="编辑处方"]', '')
  await click('确认处方，生成病历')
  await waitFor("document.querySelector('.live-error')?.textContent.includes('不能为空')", 10000, true)
  await fill('textarea[aria-label="编辑处方"]', '虚构软件测试药味 1g\n仅验证保存，不用于治疗。')
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
  // Check combined intake invalidation and regenerate so the final stored encounter is complete.
  await evaluate("document.querySelector('.compact-stages button').click()")
  await waitFor("!!document.querySelector('textarea[aria-label=\"望诊补充\"]')")
  await fill('textarea[aria-label="望诊补充"]', '舌淡，医师补充虚构测试')
  await click('确认问诊，生成辨证')
  await waitFor("document.body.innerText.includes('确认辨证论治，检索基础方')")
  await click('确认辨证论治，检索基础方')
  await waitFor("document.querySelectorAll('.formula-card').length > 0")
  await evaluate("document.querySelector('.formula-card').click()")
  await click('带入所选基础方')
  await fill('textarea[aria-label="编辑处方"]', '虚构软件测试药味 1g\n仅验证保存，不用于治疗。')
  await click('确认处方，生成病历')
  await waitFor("!!document.querySelector('.live-record')?.value")
  await evaluate("document.querySelector('input[type=checkbox]').click()")
  await click('医师确认并保存')
  await waitFor("document.body.innerText.includes('医师已确认并保存。')")
  assert.deepEqual(errors, [])
  console.log('PASS: compact four-step workflow, merged intake, analysis, RAG, free-text prescription, confirmation, recovery and upstream invalidation; no browser exceptions')
} finally {
  socket?.close()
  chrome.kill('SIGTERM')
  await new Promise(resolve => chrome.once('exit', resolve))
  await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 })
}
