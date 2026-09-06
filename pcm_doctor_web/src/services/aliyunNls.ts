import { getSpeechCredentials, type SpeechCredentials } from '../api/speech'

export type SpeechSessionState =
  | 'idle'
  | 'connecting'
  | 'recording'
  | 'stopping'
  | 'paused'
  | 'error'

export interface TranscriptUpdate {
  index: number
  text: string
  isFinal: boolean
  beginTime?: number
  endTime?: number
}

export interface SpeechSessionHandlers {
  onState: (state: SpeechSessionState) => void
  onTranscript: (update: TranscriptUpdate) => void
  onError: (message: string) => void
  onAudio?: (pcm: ArrayBuffer) => void
}

const TARGET_SAMPLE_RATE = 16_000
const SUCCESS_STATUS = 20_000_000

function randomId(): string {
  if (typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replaceAll('-', '')
  }
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  return Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('')
}

export function downsampleTo16k(input: Float32Array, inputRate: number): Float32Array {
  if (inputRate === TARGET_SAMPLE_RATE) return input
  if (inputRate < TARGET_SAMPLE_RATE) {
    throw new Error('当前麦克风采样率低于16kHz，无法用于实时识别')
  }
  const ratio = inputRate / TARGET_SAMPLE_RATE
  const outputLength = Math.max(1, Math.round(input.length / ratio))
  const output = new Float32Array(outputLength)
  for (let index = 0; index < outputLength; index += 1) {
    const start = Math.floor(index * ratio)
    const end = Math.min(input.length, Math.max(start + 1, Math.floor((index + 1) * ratio)))
    let total = 0
    for (let sourceIndex = start; sourceIndex < end; sourceIndex += 1) {
      total += input[sourceIndex]
    }
    output[index] = total / (end - start)
  }
  return output
}

export function floatTo16BitPcm(input: Float32Array): ArrayBuffer {
  const pcm = new Int16Array(input.length)
  for (let index = 0; index < input.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, input[index]))
    pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
  }
  return pcm.buffer
}

function readableError(reason: unknown): string {
  if (reason instanceof DOMException && reason.name === 'NotAllowedError') {
    return '麦克风权限被拒绝，请在浏览器地址栏中允许麦克风后重试'
  }
  if (reason instanceof DOMException && reason.name === 'NotFoundError') {
    return '没有检测到可用麦克风'
  }
  if (reason instanceof Error && reason.name === 'AbortError') {
    return '连接语音服务超时，请检查网络后重试'
  }
  return reason instanceof Error ? reason.message : '录音启动失败，请稍后重试'
}

export class AliyunRealtimeTranscriber {
  private websocket?: WebSocket
  private audioContext?: AudioContext
  private mediaStream?: MediaStream
  private sourceNode?: MediaStreamAudioSourceNode
  private captureNode?: AudioWorkletNode | ScriptProcessorNode
  private silentGain?: GainNode
  private taskId = ''
  private credentials?: SpeechCredentials
  private stopRequested = false
  private completed = false

  constructor(private readonly handlers: SpeechSessionHandlers) {}

  async start(): Promise<void> {
    this.stopRequested = false
    this.completed = false
    this.handlers.onState('connecting')
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('当前浏览器不支持麦克风录音，请使用最新版Chrome或Safari')
      }
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      if (this.stopRequested) { await this.releaseAudio(); return }
      const credentials = await getSpeechCredentials()
      if (this.stopRequested) { await this.releaseAudio(); return }
      this.credentials = credentials
      this.audioContext = new AudioContext({ latencyHint: 'interactive' })
      await this.audioContext.resume()
      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream)
      await this.connectWebSocket(credentials)
      if (this.stopRequested) { await this.releaseAudio(); return }
      await this.connectAudioCapture()
      this.handlers.onState('recording')
    } catch (reason) {
      await this.releaseAudio()
      this.websocket?.close()
      if (this.stopRequested) return
      this.handlers.onState('error')
      const message = readableError(reason)
      this.handlers.onError(message)
      throw new Error(message, { cause: reason })
    }
  }

  async stop(): Promise<void> {
    if (this.stopRequested) return
    this.stopRequested = true
    this.handlers.onState('stopping')
    await this.releaseAudio()

    if (this.websocket?.readyState === WebSocket.OPEN && this.credentials) {
      this.websocket.send(
        JSON.stringify({
          header: {
            appkey: this.credentials.appkey,
            namespace: 'SpeechTranscriber',
            name: 'StopTranscription',
            task_id: this.taskId,
            message_id: randomId(),
          },
        }),
      )
      await new Promise<void>((resolve) => {
        const finish = () => { window.clearInterval(check); window.clearTimeout(timeout); resolve() }
        const check = window.setInterval(() => {
          if (this.completed || this.websocket?.readyState === WebSocket.CLOSED) finish()
        }, 40)
        const timeout = window.setTimeout(finish, 1200)
      })
    }
    this.websocket?.close()
    this.websocket = undefined
    this.handlers.onState('paused')
  }

  private connectWebSocket(credentials: SpeechCredentials): Promise<void> {
    return new Promise((resolve, reject) => {
      this.taskId = randomId()
      const separator = credentials.gateway.includes('?') ? '&' : '?'
      const socket = new WebSocket(
        credentials.gateway + separator + 'token=' + encodeURIComponent(credentials.token),
      )
      this.websocket = socket
      let started = false
      let failed = false
      const fail = (error: Error) => {
        if (failed) return
        failed = true
        window.clearTimeout(timeout)
        reject(error)
        if (started && !this.stopRequested) {
          void this.releaseAudio()
          this.handlers.onState('error')
          this.handlers.onError(error.message)
        }
        socket.close()
      }
      const timeout = window.setTimeout(() => {
        fail(new DOMException('NLS connection timeout', 'AbortError'))
      }, 10_000)

      socket.onopen = () => {
        socket.send(
          JSON.stringify({
            header: {
              appkey: credentials.appkey,
              namespace: 'SpeechTranscriber',
              name: 'StartTranscription',
              task_id: this.taskId,
              message_id: randomId(),
            },
            payload: {
              format: 'pcm',
              sample_rate: TARGET_SAMPLE_RATE,
              enable_intermediate_result: true,
              enable_punctuation_prediction: true,
              enable_inverse_text_normalization: true,
              ...(credentials.vocabulary_id ? { vocabulary_id: credentials.vocabulary_id } : {}),
            },
          }),
        )
      }

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(String(event.data))
          const header = message.header || {}
          if (header.status && header.status !== SUCCESS_STATUS) {
            fail(new Error(header.status_message || '语音识别服务返回错误'))
            return
          }
          if (header.name === 'TranscriptionStarted') {
            started = true
            window.clearTimeout(timeout)
            resolve()
            return
          }
          if (header.name === 'TranscriptionCompleted') {
            this.completed = true
            return
          }
          if (
            header.name === 'TranscriptionResultChanged'
            || header.name === 'SentenceEnd'
          ) {
            const payload = message.payload || {}
            if (typeof payload.result === 'string' && Number.isInteger(payload.index)) {
              this.handlers.onTranscript({
                index: payload.index,
                text: payload.result,
                isFinal: header.name === 'SentenceEnd',
                beginTime: payload.begin_time,
                endTime: payload.time,
              })
            }
          }
        } catch (reason) {
          this.handlers.onError(readableError(reason))
        }
      }

      socket.onerror = () => {
        fail(new Error('无法连接实时语音识别服务'))
      }
      socket.onclose = () => {
        window.clearTimeout(timeout)
        if (!started) reject(new Error('语音连接在建立前已断开，请重试'))
        if (failed) return
        if (!this.stopRequested && !this.completed) {
          void this.releaseAudio()
          this.handlers.onState('error')
          this.handlers.onError('语音连接已断开，已识别文字不会丢失，请点击继续录音')
        }
      }
    })
  }

  private async connectAudioCapture(): Promise<void> {
    if (!this.audioContext || !this.sourceNode) return
    const context = this.audioContext
    const handleAudio = (samples: Float32Array) => {
      if (this.websocket?.readyState !== WebSocket.OPEN || this.stopRequested) return
      const downsampled = downsampleTo16k(samples, context.sampleRate)
      const pcm = floatTo16BitPcm(downsampled)
      this.handlers.onAudio?.(pcm)
      this.websocket.send(pcm)
    }

    if (context.audioWorklet && typeof AudioWorkletNode !== 'undefined') {
      await context.audioWorklet.addModule('/pcm-recorder.worklet.js')
      const worklet = new AudioWorkletNode(context, 'pcm-recorder')
      worklet.port.onmessage = (event: MessageEvent<Float32Array>) => handleAudio(event.data)
      this.captureNode = worklet
    } else {
      const processor = context.createScriptProcessor(4096, 1, 1)
      processor.onaudioprocess = (event) => handleAudio(event.inputBuffer.getChannelData(0))
      this.captureNode = processor
    }

    this.silentGain = context.createGain()
    this.silentGain.gain.value = 0
    this.sourceNode.connect(this.captureNode)
    this.captureNode.connect(this.silentGain)
    this.silentGain.connect(context.destination)
  }

  private async releaseAudio(): Promise<void> {
    const captureNode = this.captureNode
    if (captureNode && 'port' in captureNode) {
      captureNode.port.onmessage = null
    } else if (captureNode) {
      captureNode.onaudioprocess = null
    }
    this.sourceNode?.disconnect()
    this.captureNode?.disconnect()
    this.silentGain?.disconnect()
    this.mediaStream?.getTracks().forEach((track) => track.stop())
    if (this.audioContext && this.audioContext.state !== 'closed') {
      await this.audioContext.close()
    }
    this.captureNode = undefined
    this.sourceNode = undefined
    this.silentGain = undefined
    this.mediaStream = undefined
    this.audioContext = undefined
  }
}
