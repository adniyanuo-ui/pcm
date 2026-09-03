import { describe, expect, it } from 'vitest'
import { downsampleTo16k, floatTo16BitPcm } from './aliyunNls'


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
