import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

if (!window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
    dispatchEvent() {
      return false;
    },
  });
}

if (!window.requestAnimationFrame) {
  window.requestAnimationFrame = (callback) => window.setTimeout(callback, 0);
}

afterEach(() => {
  cleanup();
  window.history.replaceState({}, "", "/");
});
