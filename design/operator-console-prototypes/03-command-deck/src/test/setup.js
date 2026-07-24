import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  window.history.replaceState(null, "", `${window.location.pathname}#/lab`);
});
