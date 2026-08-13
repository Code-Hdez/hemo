export interface SseEvent {
  event: string;
  data: unknown;
}

const inlineCitationPattern =
  /\[\s*(?:S\s*\d+(?:\s*,\s*S\s*\d+)*|refs?|references?|source\s*\d*|fuente\s*\d*)\s*\]/gi;

export function cleanVisibleAssistantText(text: string, options: { trim?: boolean } = {}): string {
  const cleaned = text
    .replace(inlineCitationPattern, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\s+([.,;:])/g, "$1")
    .replace(/\(\s*\)/g, "");
  return options.trim === false ? cleaned : cleaned.trim();
}

export class SseParser {
  private buffer = "";
  private pendingCarriageReturn = false;

  push(chunk: string): SseEvent[] {
    this.appendNormalized(chunk);
    return this.drain(false);
  }

  finish(): SseEvent[] {
    if (this.pendingCarriageReturn) {
      this.buffer += "\n";
      this.pendingCarriageReturn = false;
    }
    return this.drain(true);
  }

  private appendNormalized(chunk: string): void {
    for (const character of chunk) {
      if (this.pendingCarriageReturn) {
        this.buffer += "\n";
        this.pendingCarriageReturn = false;
        if (character === "\n") continue;
      }
      if (character === "\r") {
        this.pendingCarriageReturn = true;
      } else {
        this.buffer += character;
      }
    }
  }

  private drain(flush: boolean): SseEvent[] {
    const blocks = this.buffer.split("\n\n");
    this.buffer = blocks.pop() ?? "";
    if (flush && this.buffer) {
      blocks.push(this.buffer);
      this.buffer = "";
    }
    return blocks.flatMap((block) => this.parseBlock(block));
  }

  private parseBlock(block: string): SseEvent[] {
    const lines = block.split("\n");
    if (lines.length === 0 || lines.every((line) => line.startsWith(":"))) return [];
    const event = lines
      .filter((line) => line.startsWith("event:"))
      .at(-1)
      ?.slice(6)
      .trim();
    const dataLines = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart());
    if (!event || dataLines.length === 0) return [];
    try {
      return [{ event, data: JSON.parse(dataLines.join("\n")) as unknown }];
    } catch {
      throw new Error("Evento SSE inválido");
    }
  }
}
