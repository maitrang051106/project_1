import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";
import { useAuthStore } from "./auth.js";

describe("auth store", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null });
  });

  it("stores the current user in memory", () => {
    const user = { nickname: "Anonymous_Fox" };

    useAuthStore.getState().setUser(user);

    assert.deepEqual(useAuthStore.getState().user, user);
  });

  it("clears the current user", () => {
    useAuthStore.setState({ user: { nickname: "Anonymous_Fox" } });

    useAuthStore.getState().clearUser();

    assert.equal(useAuthStore.getState().user, null);
  });
});
