import { describe, expect, it } from "vitest";
import type { ExecutorState, Run } from "../../types";
import { issueTone, runProgressIssue } from "./runProgress";

const waiting = { status: "queued" } as Run;
const done = { status: "completed" } as Run;
const ready = { status: "ready" } as ExecutorState;
const dead = { status: "failed" } as ExecutorState;

describe("run progress issue", () => {
  it("stays silent while a Run is progressing normally", () => {
    expect(
      runProgressIssue({ run: waiting, streamState: "open", streamError: null, executor: ready }),
    ).toBeNull();
  });

  it("names the executor rather than the stream when nothing can progress", () => {
    // Reporting a reconnecting stream for a Run nothing is executing would show the symptom and
    // hide the cause.
    const issue = runProgressIssue({
      run: waiting,
      streamState: "reconnecting",
      streamError: "Stream interrompido",
      executor: dead,
    });
    expect(issue?.kind).toBe("executor-down");
    expect(issue?.message).toContain("executor");
  });

  it("treats a reconnecting stream as transient", () => {
    const issue = runProgressIssue({
      run: waiting,
      streamState: "reconnecting",
      streamError: null,
      executor: ready,
    });
    expect(issue?.kind).toBe("stream-reconnecting");
    expect(issueTone(issue!)).toBe("info");
  });

  it("gives a stalled executor the assertive tone", () => {
    const issue = runProgressIssue({
      run: waiting,
      streamState: "open",
      streamError: null,
      executor: dead,
    });
    expect(issueTone(issue!)).toBe("danger");
  });

  it("does not blame the executor for a Run that already finished", () => {
    expect(
      runProgressIssue({ run: done, streamState: "closed", streamError: null, executor: dead }),
    ).toBeNull();
  });

  it("says nothing about an executor in a browser, where none is supervised", () => {
    expect(
      runProgressIssue({ run: waiting, streamState: "open", streamError: null }),
    ).toBeNull();
  });

  it("still surfaces a stream failure that is not the executor's fault", () => {
    const issue = runProgressIssue({
      run: waiting,
      streamState: "closed",
      streamError: "Falha no stream",
      executor: ready,
    });
    expect(issue?.kind).toBe("stream-failed");
    expect(issue?.message).toBe("Falha no stream");
  });
});
