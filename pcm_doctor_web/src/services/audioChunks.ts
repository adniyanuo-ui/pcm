export const AUDIO_CHUNK_SAMPLES = 160000

export function pcmWav(pcm: Int16Array): ArrayBuffer {
  const result = new ArrayBuffer(44 + pcm.length * 2)
  const view = new DataView(result)
  const word = (at: number, text: string) => [...text].forEach((c, i) => view.setUint8(at + i, c.charCodeAt(0)))
  word(0, 'RIFF'); view.setUint32(4, result.byteLength - 8, true); word(8, 'WAVE')
  word(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true)
  view.setUint16(22, 1, true); view.setUint32(24, 16000, true); view.setUint32(28, 32000, true)
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); word(36, 'data')
  view.setUint32(40, pcm.length * 2, true)
  pcm.forEach((sample, i) => view.setInt16(44 + i * 2, sample, true))
  return result
}

export function toBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192))
  return btoa(binary)
}

/** Bound memory and retain exact offsets across worklet buffer boundaries. */
export class PcmChunker {
  private buffer = new Int16Array(AUDIO_CHUNK_SAMPLES)
  private used = 0
  totalSamples = 0
  constructor(private emit: (wav: ArrayBuffer) => void) {}
  push(raw: ArrayBuffer) {
    const pcm = new Int16Array(raw)
    this.totalSamples += pcm.length
    for (let offset = 0; offset < pcm.length;) {
      const size = Math.min(this.buffer.length - this.used, pcm.length - offset)
      this.buffer.set(pcm.subarray(offset, offset + size), this.used)
      this.used += size; offset += size
      if (this.used === this.buffer.length) this.flush()
    }
  }
  flush() {
    if (!this.used) return
    this.emit(pcmWav(this.buffer.subarray(0, this.used)))
    this.used = 0
  }
}
