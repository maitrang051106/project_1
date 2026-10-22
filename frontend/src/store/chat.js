import { create } from "zustand";

export const useChatStore = create((set) => ({
  roomId: null,
  messages: [],
  setRoomId: (roomId) => set({ roomId }),
  setMessages: (messages) => set({ messages }),
}));
