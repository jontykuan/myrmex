export interface TaskItem {
  readonly taskId: string;
  readonly priority: number;
  readonly createdSeq: number;
  readonly windowStart: number;
  readonly windowEnd: number;
}

export function evalRule(_facts: Record<string, unknown>, _rule: Record<string, unknown>): boolean {
  throw new Error("slice-01-core-eval");
}

export function scheduleNext(_queue: readonly TaskItem[]): TaskItem | null {
  throw new Error("slice-02-priority-queue");
}

export function parseTaskInput(_raw: unknown): TaskItem {
  throw new Error("slice-03-input-parser");
}

export function inWindow(_ts: number, _start: number, _end: number): boolean {
  throw new Error("slice-04-window-bounds");
}
