import { afterEach, describe, expect, it, vi } from 'vitest'
import { AliyunRealtimeTranscriber, downsampleTo16k, floatTo16BitPcm } from './aliyunNls'
import { getSpeechCredentials } from '../api/speech'

vi.mock('../api/speech', () => ({ getSpeechCredentials: vi.fn() }))

afterEach(() => { vi.unstubAllGlobals(); vi.resetAllMocks(); vi.useRealTimers() })

function audioFixture() {
  const stop = vi.fn()
  vi.stubGlobal('window', globalThis)
  vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) } })
  const node = () => ({ connect: vi.fn(), disconnect: vi.fn() })
  vi.stubGlobal('AudioContext', class {
    state = 'running'
    sampleRate = 16000
    resume = vi.fn().mockResolvedValue(undefined)
    close = vi.fn(async () => { this.state = 'closed' })
    createMediaStreamSource = node
    createScriptProcessor = node
    createGain = () => ({ ...node(), gain: { value: 1 } })
  })
  const handlers = { onState: vi.fn(), onError: vi.fn(), onTranscript: vi.fn() }
  vi.mocked(getSpeechCredentials).mockResolvedValue({ token: 'test', appkey: 'test', gateway: 'wss://example.test', expires_at: '' })
  return { stop, handlers, transcriber: new AliyunRealtimeTranscriber(handlers) }
}

class FakeSocket {
  static OPEN = 1
  static CLOSED = 3
  static instance: FakeSocket
  readyState = 1
  onopen?: () => void
  onclose?: () => void
  onmessage?: (event: { data: string }) => void
  send = vi.fn()
  constructor() { FakeSocket.instance = this }
  close() { this.readyState = 3; this.onclose?.() }
  message(header: object) { this.onmessage?.({ data: JSON.stringify({ header }) }) }
}

describe('Aliyun NLS failure cleanup', () => {
  it('releases microphone when credentials request fails', async () => {
    const { stop, handlers, transcriber } = audioFixture()
    vi.mocked(getSpeechCredentials).mockRejectedValue(new Error('service unavailable'))
    await expect(transcriber.start()).rejects.toThrow('service unavailable')
    expect(stop).toHaveBeenCalledOnce()
    expect(handlers.onState).toHaveBeenLastCalledWith('error')
  })
  it('reports unsupported microphone through the state handler', async () => {
    const { handlers, transcriber } = audioFixture()
    vi.stubGlobal('navigator', {})
    await expect(transcriber.start()).rejects.toThrow('不支持麦克风')
    expect(handlers.onError).toHaveBeenCalled()
  })
  it('rejects a handshake closed before transcription starts', async () => {
    const { transcriber, stop } = audioFixture()
    vi.stubGlobal('WebSocket', FakeSocket)
    const pending = transcriber.start()
    const assertion = expect(pending).rejects.toThrow('建立前已断开')
    await vi.waitFor(() => expect(FakeSocket.instance).toBeDefined())
    FakeSocket.instance.close()
    await assertion
    expect(stop).toHaveBeenCalled()
  })
  it('clears stop polling when completion is not received', async () => {
    vi.useFakeTimers()
    const { transcriber } = audioFixture()
    vi.stubGlobal('WebSocket', FakeSocket)
    const pending = transcriber.start()
    await vi.advanceTimersByTimeAsync(0)
    FakeSocket.instance.message({ name: 'TranscriptionStarted', status: 20000000 })
    await pending
    const stopping = transcriber.stop()
    await vi.advanceTimersByTimeAsync(1300)
    await stopping
    expect(vi.getTimerCount()).toBe(0)
  })
  it('releases recording on a service error after start', async () => {
    vi.useFakeTimers()
    const { transcriber, stop, handlers } = audioFixture()
    vi.stubGlobal('WebSocket', FakeSocket)
    const pending = transcriber.start()
    await vi.advanceTimersByTimeAsync(0)
    FakeSocket.instance.message({ name: 'TranscriptionStarted', status: 20000000 })
    await pending
    FakeSocket.instance.message({ status: 40000000, status_message: 'test service failure' })
    await vi.advanceTimersByTimeAsync(0)
    expect(stop).toHaveBeenCalled()
    expect(handlers.onState).toHaveBeenLastCalledWith('error')
    expect(handlers.onError).toHaveBeenCalledWith('test service failure')
    expect(vi.getTimerCount()).toBe(0)
  })
})


describe('Aliyun NLS audio conversion', () => {
  it('downsamples 48kHz audio to 16kHz', () => {
    const input = new Float32Array(48_000)
    for (let index = 0; index < input.length; index += 1) {
      input[index] = Math.sin(2 * Math.PI * 440 * index / 48_000)
    }
    const output = downsampleTo16k(input, 48_000)
    expect(output).toHaveLength(16_000)
    expect(Math.max(...output)).toBeGreaterThan(0.9)
    expect(Math.min(...output)).toBeLessThan(-0.9)
  })

  it('keeps native 16kHz samples unchanged', () => {
    const input = new Float32Array([0.1, -0.1])
    expect(downsampleTo16k(input, 16_000)).toBe(input)
  })

  it('rejects sample rates below the NLS requirement', () => {
    expect(() => downsampleTo16k(new Float32Array(100), 8_000)).toThrow('低于16kHz')
  })

  it('converts and clamps floating point samples to signed PCM16', () => {
    const buffer = floatTo16BitPcm(new Float32Array([-2, -1, -0.5, 0, 0.5, 1, 2]))
    expect(Array.from(new Int16Array(buffer))).toEqual([
      -32768,
      -32768,
      -16384,
      0,
      16383,
      32767,
      32767,
    ])
  })
})
