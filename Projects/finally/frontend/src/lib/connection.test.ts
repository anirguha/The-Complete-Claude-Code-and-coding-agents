import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextConnectionStatus } from "./connection";
import { connectPriceStream, RECONNECT_TIMEOUT_MS, RETRY_DELAY_MS } from "./priceStream";

const CONNECTING = 0;
const OPEN = 1;
const CLOSED = 2;

describe("nextConnectionStatus", () => {
  it("is connected on open or message", () => {
    expect(nextConnectionStatus("reconnecting", { type: "open" })).toBe("connected");
    expect(nextConnectionStatus("disconnected", { type: "message" })).toBe("connected");
  });

  it("is reconnecting while the browser retries", () => {
    expect(nextConnectionStatus("connected", { type: "error", readyState: CONNECTING })).toBe("reconnecting");
  });

  it("is disconnected when the browser gives up", () => {
    expect(nextConnectionStatus("connected", { type: "error", readyState: CLOSED })).toBe("disconnected");
  });

  it("stays disconnected through failed retries", () => {
    expect(nextConnectionStatus("disconnected", { type: "error", readyState: CONNECTING })).toBe("disconnected");
  });

  it("times out only from reconnecting", () => {
    expect(nextConnectionStatus("reconnecting", { type: "timeout" })).toBe("disconnected");
    expect(nextConnectionStatus("connected", { type: "timeout" })).toBe("connected");
  });
});

class FakeSource {
  readyState = CONNECTING;
  closed = false;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  close() {
    this.closed = true;
    this.readyState = CLOSED;
  }
  open() {
    this.readyState = OPEN;
    this.onopen?.();
  }
  fail(readyState: number) {
    this.readyState = readyState;
    this.onerror?.();
  }
}

describe("connectPriceStream", () => {
  let sources: FakeSource[];
  let statuses: string[];
  let received: unknown[];
  let dispose: () => void;

  beforeEach(() => {
    vi.useFakeTimers();
    sources = [];
    statuses = [];
    received = [];
    dispose = connectPriceStream({
      onStatus: (s) => statuses.push(s),
      onPrices: (p) => received.push(p),
      createSource: () => {
        const source = new FakeSource();
        sources.push(source);
        return source as unknown as EventSource;
      },
    });
  });

  afterEach(() => {
    dispose();
    vi.useRealTimers();
  });

  it("walks connected, reconnecting, connected across a network drop", () => {
    sources[0].open();
    sources[0].fail(CONNECTING);
    sources[0].open();
    expect(statuses).toEqual(["reconnecting", "connected", "reconnecting", "connected"]);
    expect(sources).toHaveLength(1);
  });

  it("goes red if reconnecting takes too long, and recovers", () => {
    sources[0].open();
    sources[0].fail(CONNECTING);
    vi.advanceTimersByTime(RECONNECT_TIMEOUT_MS);
    expect(statuses.at(-1)).toBe("disconnected");
    sources[0].fail(CONNECTING);
    expect(statuses.at(-1)).toBe("disconnected");
    sources[0].open();
    expect(statuses.at(-1)).toBe("connected");
  });

  it("does not time out once recovered", () => {
    sources[0].open();
    sources[0].fail(CONNECTING);
    sources[0].open();
    vi.advanceTimersByTime(RECONNECT_TIMEOUT_MS * 2);
    expect(statuses.at(-1)).toBe("connected");
  });

  it("reopens the stream itself after the browser gives up", () => {
    sources[0].open();
    sources[0].fail(CLOSED);
    expect(statuses.at(-1)).toBe("disconnected");
    expect(sources).toHaveLength(1);
    vi.advanceTimersByTime(RETRY_DELAY_MS);
    expect(sources).toHaveLength(2);
    sources[1].open();
    expect(statuses.at(-1)).toBe("connected");
  });

  it("survives a malformed event", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    sources[0].open();
    sources[0].onmessage?.({ data: "not json" });
    sources[0].onmessage?.({ data: '{"AAPL":{"price":1}}' });
    expect(received).toHaveLength(1);
    expect(warn).toHaveBeenCalledOnce();
    warn.mockRestore();
  });

  it("closes the source and stops retrying when disposed", () => {
    sources[0].fail(CLOSED);
    dispose();
    vi.advanceTimersByTime(RETRY_DELAY_MS * 2);
    expect(sources).toHaveLength(1);
    expect(sources[0].closed).toBe(true);
  });
});
