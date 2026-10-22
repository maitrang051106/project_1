import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";
import { useChatStore } from "./chat.js";

describe("chat store", () => {
  beforeEach(() => {
    useChatStore.setState({ roomId: null, messages: [] });
  });

  it("stores the active room id in memory", () => {
    useChatStore.getState().setRoomId("room-123");

    assert.equal(useChatStore.getState().roomId, "room-123");
  });
});
