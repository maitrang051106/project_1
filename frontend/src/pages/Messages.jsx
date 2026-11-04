import { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { apiFetch, buildWsUrl } from "../lib/api";
import { useAuthStore } from "../store/auth";
import { DEFAULT_AVATAR } from "../lib/constants";

export default function Messages() {
  const [searchParams] = useSearchParams();
  const targetFriendId = parseInt(searchParams.get("friendId") || "0", 10);
  const currentUser = useAuthStore((state) => state.user);

  // Friends list & pagination state (Bất cập 4)
  const [friends, setFriends] = useState([]);
  const [activeFriend, setActiveFriend] = useState(null);
  const [loadingFriends, setLoadingFriends] = useState(true);
  const [hasMoreFriends, setHasMoreFriends] = useState(false);
  const [loadingMoreFriends, setLoadingMoreFriends] = useState(false);

  // Messages & pagination state (Bất cập 4)
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [loadingOlderMessages, setLoadingOlderMessages] = useState(false);

  const socketRef = useRef(null);
  const scrollRef = useRef(null);
  const messagesFeedRef = useRef(null);
  const friendsListRef = useRef(null);
  const isPrependingRef = useRef(false);

  // ── 1. Fetch friends list (paginated, Bất cập 4) ──────────────────────────
  const fetchFriends = useCallback(async () => {
    try {
      setLoadingFriends(true);
      const res = await apiFetch("/friends?limit=20&offset=0");
      if (res.ok) {
        const data = await res.json();
        const list = Array.isArray(data) ? data : data.friends || [];
        setFriends(list);
        setHasMoreFriends(Array.isArray(data) ? false : Boolean(data.has_more));
      }
    } catch (err) {
      console.error("Error loading friends:", err);
    } finally {
      setLoadingFriends(false);
    }
  }, []);

  useEffect(() => {
    fetchFriends();
  }, [fetchFriends]);

  // Infinite scroll down for friends list
  const handleFriendsScroll = async () => {
    const el = friendsListRef.current;
    if (!el || loadingMoreFriends || !hasMoreFriends) return;

    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 30) {
      setLoadingMoreFriends(true);
      try {
        const res = await apiFetch(`/friends?limit=20&offset=${friends.length}`);
        if (res.ok) {
          const data = await res.json();
          const nextFriends = Array.isArray(data) ? data : data.friends || [];
          setHasMoreFriends(Array.isArray(data) ? false : Boolean(data.has_more));
          setFriends((prev) => {
            const existingIds = new Set(prev.map((f) => f.id));
            const uniqueNext = nextFriends.filter((f) => !existingIds.has(f.id));
            return [...prev, ...uniqueNext];
          });
        }
      } catch (err) {
        console.error("Error loading more friends:", err);
      } finally {
        setLoadingMoreFriends(false);
      }
    }
  };

  // ── 2. Auto-select friend based on targetFriendId or first friend ─────────
  useEffect(() => {
    if (friends.length === 0) return;
    if (targetFriendId) {
      const target = friends.find((f) => f.id === targetFriendId);
      if (target) {
        setActiveFriend(target);
        return;
      }
    }
    if (!activeFriend) {
      setActiveFriend(friends[0]);
    }
  }, [friends, targetFriendId, activeFriend]);

  // ── 3. Fetch messages for active friend (Cursor-based, Bất cập 4) ──────────
  useEffect(() => {
    if (!activeFriend) return;

    setLoadingMessages(true);
    setMessages([]);
    setHasMoreMessages(false);

    apiFetch(`/messages/${activeFriend.id}?limit=20`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) return;
        const msgList = Array.isArray(data) ? data : data.messages || [];
        setMessages(msgList);
        setHasMoreMessages(Array.isArray(data) ? false : Boolean(data.has_more));
      })
      .catch((err) => console.error("Error loading direct messages:", err))
      .finally(() => setLoadingMessages(false));

    // Connect to Direct WebSocket via shared helper (proxies /ws in local dev)
    const wsUrl = buildWsUrl(`/ws/direct/${activeFriend.id}`);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "direct_message") {
          setMessages((prev) => {
            if (prev.some((m) => m.id === data.id)) return prev;
            return [...prev, data];
          });
          // Update last message in friends list
          setFriends((prevFriends) =>
            prevFriends.map((f) =>
              f.id === activeFriend.id
                ? { ...f, last_message: data.content, last_message_at: data.created_at }
                : f
            )
          );
        }
      } catch (err) {
        console.error("Error reading direct message:", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [activeFriend?.id]);

  // Auto scroll to bottom when receiving or sending message
  useEffect(() => {
    if (isPrependingRef.current) {
      isPrependingRef.current = false;
      return;
    }
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Infinite scroll up for older direct messages (Cursor-based, Bất cập 4)
  const handleMessagesScroll = async () => {
    const el = messagesFeedRef.current;
    if (!el || loadingOlderMessages || !hasMoreMessages || el.scrollTop > 30) return;

    const earliestMsg = messages.find((m) => typeof m.id === "number");
    if (!earliestMsg) return;

    setLoadingOlderMessages(true);
    const prevScrollHeight = el.scrollHeight;

    try {
      const res = await apiFetch(
        `/messages/${activeFriend.id}?limit=20&before_id=${earliestMsg.id}`
      );
      if (res.ok) {
        const data = await res.json();
        const older = Array.isArray(data) ? data : data.messages || [];
        setHasMoreMessages(Array.isArray(data) ? false : Boolean(data.has_more));

        if (older.length > 0) {
          isPrependingRef.current = true;
          setMessages((prev) => {
            const existingIds = new Set(prev.map((m) => m.id));
            const uniqueOlder = older.filter((m) => !existingIds.has(m.id));
            return [...uniqueOlder, ...prev];
          });

          requestAnimationFrame(() => {
            if (messagesFeedRef.current) {
              messagesFeedRef.current.scrollTop =
                messagesFeedRef.current.scrollHeight - prevScrollHeight;
            }
          });
        }
      }
    } catch (err) {
      console.error("Error loading older messages:", err);
    } finally {
      setLoadingOlderMessages(false);
    }
  };

  // ── 4. Send Message via WebSocket only (Bất cập 3) ────────────────────────
  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputText.trim() || !activeFriend || !socketRef.current) return;

    socketRef.current.send(inputText.trim());
    setInputText("");
  };

  return (
    <div className="mx-auto flex h-[82vh] max-w-5xl rounded-2xl bg-white shadow-sm border border-slate-200 overflow-hidden">
      {/* Left Column: Friends List with Infinite Scroll (Bất cập 4) */}
      <div className="w-80 border-r border-slate-200 flex flex-col bg-slate-50/50">
        <div className="p-4 border-b border-slate-200 bg-white">
          <h2 className="text-base font-bold text-slate-900">Direct Messages</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {friends.length} {friends.length === 1 ? "friend" : "friends"} connected
          </p>
        </div>

        <div
          ref={friendsListRef}
          onScroll={handleFriendsScroll}
          className="flex-1 overflow-y-auto divide-y divide-slate-100"
        >
          {loadingFriends ? (
            <div className="p-5 text-center text-xs text-slate-400">Loading friends...</div>
          ) : friends.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              <span className="text-2xl block mb-2">🤝</span>
              No friends yet.<br />
              Match anonymously and click <strong>Add Friend</strong> to connect!
            </div>
          ) : (
            <>
              {friends.map((friend) => (
                <button
                  key={friend.id}
                  onClick={() => setActiveFriend(friend)}
                  className={`w-full p-3.5 text-left flex items-start gap-3 transition ${
                    activeFriend?.id === friend.id
                      ? "bg-red-50/80 border-r-2 border-red-700"
                      : "hover:bg-slate-100/70"
                  }`}
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-200 text-lg">
                    {friend.avatar || DEFAULT_AVATAR}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-slate-900 truncate">
                        {friend.nickname}
                      </span>
                      {friend.last_message_at && (
                        <span className="text-[10px] text-slate-400 shrink-0">
                          {new Date(friend.last_message_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-500 truncate mt-0.5">
                      {friend.last_message || friend.email}
                    </div>
                  </div>
                </button>
              ))}
              {loadingMoreFriends && (
                <div className="p-2 text-center text-xs text-slate-400 animate-pulse">
                  Loading more friends...
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Right Column: Direct Chat Pane */}
      <div className="flex-1 flex flex-col bg-white">
        {activeFriend ? (
          <>
            {/* Top Bar */}
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3.5 bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 text-xl shadow-inner">
                  {activeFriend.avatar || DEFAULT_AVATAR}
                </div>
                <div>
                  <div className="font-semibold text-slate-900 text-sm">
                    {activeFriend.nickname}
                  </div>
                  <div className="text-xs text-slate-500 flex items-center gap-1">
                    <span>✉️</span>
                    <span>{activeFriend.email}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Message Feed with Infinite Scroll Up (Bất cập 4) */}
            <div
              ref={messagesFeedRef}
              onScroll={handleMessagesScroll}
              className="flex-1 overflow-y-auto p-5 space-y-3 bg-slate-50/30"
            >
              {loadingOlderMessages && (
                <div className="text-center text-xs text-slate-400 py-1 animate-pulse">
                  Loading older messages...
                </div>
              )}

              {loadingMessages ? (
                <div className="text-center text-xs text-slate-400 py-6">
                  Loading message history...
                </div>
              ) : messages.length === 0 ? (
                <div className="text-center text-xs text-slate-400 py-10">
                  Say hi to your new friend! 👋
                </div>
              ) : (
                messages.map((msg, index) => {
                  const isMe = msg.sender_id === currentUser?.id;
                  return (
                    <div
                      key={msg.id || index}
                      className={`flex items-end gap-2 ${
                        isMe ? "justify-end" : "justify-start"
                      }`}
                    >
                      {!isMe && (
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-200 text-sm">
                          {activeFriend.avatar || DEFAULT_AVATAR}
                        </div>
                      )}
                      <div
                        className={`max-w-[70%] rounded-2xl px-4 py-2 text-sm shadow-sm ${
                          isMe
                            ? "bg-red-700 text-white rounded-br-none"
                            : "bg-white text-slate-900 border border-slate-200 rounded-bl-none"
                        }`}
                      >
                        <p className="whitespace-pre-wrap break-words leading-relaxed">
                          {msg.content}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={scrollRef} />
            </div>

            {/* Input Bar (via WebSocket only) */}
            <form
              onSubmit={handleSendMessage}
              className="flex items-center gap-2 border-t border-slate-100 bg-white p-3.5"
            >
              <input
                type="text"
                placeholder="Type a message to your friend..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
              />
              <button
                type="submit"
                disabled={!inputText.trim()}
                className="rounded-xl bg-red-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-red-800 disabled:opacity-50 transition"
              >
                Send
              </button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
            <span className="text-4xl mb-3">💬</span>
            <h3 className="font-semibold text-slate-700 text-sm">Select a Conversation</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-xs">
              Choose a friend from the list on the left to start direct messaging
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
