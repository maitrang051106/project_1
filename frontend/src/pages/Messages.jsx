import { useState, useEffect, useRef } from "react";
import { apiFetch } from "../lib/api";
import { useAuthStore } from "../store/auth";
import { DEFAULT_AVATAR } from "../lib/constants";

export default function Messages() {
  const currentUser = useAuthStore((state) => state.user);

  const [friends, setFriends] = useState([]);
  const [activeFriend, setActiveFriend] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [loadingFriends, setLoadingFriends] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);

  const socketRef = useRef(null);
  const scrollRef = useRef(null);

  // Fetch friends list on mount
  const fetchFriends = async () => {
    try {
      const res = await apiFetch("/friends");
      if (res.ok) {
        const data = await res.json();
        setFriends(data);
        if (data.length > 0 && !activeFriend) {
          setActiveFriend(data[0]);
        }
      }
    } catch (err) {
      console.error("Error loading friends:", err);
    } finally {
      setLoadingFriends(false);
    }
  };

  useEffect(() => {
    fetchFriends();
  }, []);

  // Fetch messages when activeFriend changes
  useEffect(() => {
    if (!activeFriend) return;

    setLoadingMessages(true);
    apiFetch(`/messages/${activeFriend.id}`)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setMessages(data);
        }
      })
      .catch((err) => console.error("Error loading direct messages:", err))
      .finally(() => setLoadingMessages(false));

    // Connect to Direct WebSocket
    let baseWsUrl = import.meta.env.VITE_WS_URL;
    if (!baseWsUrl) {
      const loc = window.location;
      baseWsUrl =
        (loc.protocol === "https:" ? "wss://" : "ws://") +
        (loc.hostname === "localhost" ? "localhost:8000" : loc.host);
    }
    const wsUrl = `${baseWsUrl.replace(/\/$/, "")}/ws/direct/${activeFriend.id}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "direct_message") {
          setMessages((prev) => {
            // Avoid duplicate by id
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

  // Scroll to bottom on new message
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputText.trim() || !activeFriend || !socketRef.current) return;

    socketRef.current.send(inputText.trim());
    setInputText("");
  };

  return (
    <div className="mx-auto flex h-[82vh] max-w-5xl rounded-2xl bg-white shadow-sm border border-slate-200 overflow-hidden">
      {/* Left Column: Friends List */}
      <div className="w-80 border-r border-slate-200 flex flex-col bg-slate-50/50">
        <div className="p-4 border-b border-slate-200 bg-white">
          <h2 className="text-base font-bold text-slate-900">Direct Messages</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {friends.length} {friends.length === 1 ? "friend" : "friends"} connected
          </p>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {loadingFriends ? (
            <div className="p-5 text-center text-xs text-slate-400">Loading friends...</div>
          ) : friends.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              <span className="text-2xl block mb-2">🤝</span>
              No friends yet.<br />
              Match anonymously and click <strong>Add Friend</strong> to connect!
            </div>
          ) : (
            friends.map((friend) => (
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
            ))
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

            {/* Message Feed */}
            <div className="flex-1 overflow-y-auto p-5 space-y-3 bg-slate-50/30">
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
                      key={index}
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

            {/* Input Bar */}
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

