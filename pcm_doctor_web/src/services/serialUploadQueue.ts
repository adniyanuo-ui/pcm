// A drain waits for every item, including enqueues in the previous task's final microtask.
export class SerialUploadQueue<T> {
  private items: T[] = []
  private task: Promise<void> | undefined
  constructor(private send: (item: T) => Promise<unknown>, private changed: (size: number) => void) {}
  enqueue(item: T) { this.items.push(item); this.changed(this.items.length) }
  private async flush() {
    while (this.items.length) {
      await this.send(this.items[0])
      this.items.shift(); this.changed(this.items.length)
    }
  }
  async drain(): Promise<void> {
    while (this.task || this.items.length) {
      if (!this.task) this.task = this.flush().finally(() => { this.task = undefined })
      await this.task
    }
  }
}
