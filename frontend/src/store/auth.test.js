import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "./auth";

describe("auth store", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null });
  });

  it("stores the current user in memory", () => {
    const user = { anonName: "Anonymous_Fox" };

    useAuthStore.getState().setUser(user);

    expect(useAuthStore.getState().user).toEqual(user);
  });

  it("clears the current user", () => {
    useAuthStore.setState({ user: { anonName: "Anonymous_Fox" } });

    useAuthStore.getState().clearUser();

    expect(useAuthStore.getState().user).toBeNull();
  });
});
