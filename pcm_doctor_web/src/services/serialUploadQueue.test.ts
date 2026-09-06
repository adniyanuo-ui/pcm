import { describe, expect, it } from 'vitest'
import { SerialUploadQueue } from './serialUploadQueue'

describe('recording finish upload barrier', () => {
  it('drains a last fragment queued while the preceding upload is finishing', async () => {
    const sent: number[] = []
    let appended = false
    const queue = new SerialUploadQueue<number>(async n => { sent.push(n) }, size => {
      if (!size && !appended) {
        appended = true
        queueMicrotask(() => { queue.enqueue(2); void queue.drain() })
      }
    })
    queue.enqueue(1)
    await Promise.all([queue.drain(), queue.drain()])
    expect(sent).toEqual([1, 2])
  })
  it('retains failed fragments for retry without duplicate successful uploads', async () => {
    const sent: number[] = []
    let fail = true
    const queue = new SerialUploadQueue<number>(async n => {
      if (n === 2 && fail) throw Error('fictional network interruption')
      sent.push(n)
    }, () => {})
    queue.enqueue(1); queue.enqueue(2)
    await expect(queue.drain()).rejects.toThrow()
    fail = false; await queue.drain()
    expect(sent).toEqual([1, 2])
  })
})
