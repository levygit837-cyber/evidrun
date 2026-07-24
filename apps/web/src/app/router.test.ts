import { describe, expect, it } from "vitest";
import { router } from "./router";

describe("desktop routes", () => {
  it.each(["/laboratory", "/create", "/observability"] as const)(
    "navigates to %s through the hash history",
    async (path) => {
      await router.navigate({ to: path });
      expect(router.state.location.pathname).toBe(path);
    },
  );
});
