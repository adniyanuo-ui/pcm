import { describe, expect, it } from 'vitest'
import { AUDIO_CHUNK_SAMPLES, PcmChunker, pcmWav, toBase64 } from './audioChunks'

describe('private audio segmentation', () => {
  it('writes a 16kHz mono little endian WAV', () => {
    const wav = pcmWav(new Int16Array([-32768, 0, 32767]))
    const view = new DataView(wav)
    expect(new TextDecoder().decode(wav.slice(0, 4))).toBe('RIFF')
    expect(view.getUint32(24, true)).toBe(16000)
    expect(view.getUint16(22, true)).toBe(1)
    expect(view.getInt16(44, true)).toBe(-32768)
    expect(view.getInt16(48, true)).toBe(32767)
    expect(atob(toBase64(wav)).length).toBe(50)
  })
  it('preserves samples exactly across worklet and ten-second boundaries', () => {
    const chunks: ArrayBuffer[] = []
    const chunker = new PcmChunker(wav => chunks.push(wav))
    const samples = new Int16Array(AUDIO_CHUNK_SAMPLES + 143)
    samples.forEach((_, i) => { samples[i] = i % 20000 })
    chunker.push(samples.slice(0, 1024).buffer)
    chunker.push(samples.slice(1024).buffer)
    expect(chunks).toHaveLength(1)
    chunker.flush(); chunker.flush()
    expect(chunks).toHaveLength(2)
    expect(chunker.totalSamples).toBe(samples.length)
    expect([...new Int16Array(chunks[0].slice(44)), ...new Int16Array(chunks[1].slice(44))]).toEqual([...samples])
  })
})
