import { beforeEach, describe, expect, it } from "vitest";
import { useChatStore } from "./chat";

describe("chat store", () => {
  beforeEach(() => {
    useChatStore.setState({ roomId: null, messages: [] });
  });

  it("stores the active room id in memory", () => {
    useChatStore.getState().setRoomId("room-123");

    expect(useChatStore.getState().roomId).toBe("room-123");
  });
});
