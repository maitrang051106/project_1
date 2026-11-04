import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiFetch, buildWsUrl } from "../lib/api";
import { useAuthStore } from "../store/auth";
import { DEFAULT_AVATAR } from "../lib/constants";

// ─── helpers ─────────────────────────────────────────────────────────────────

/** Format a Unix timestamp (seconds) into HH:MM */
function formatTime(ts) {
  if (!ts) return "";
  const d = new Date(typeof ts === "number" ? ts * 1000 : ts);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

/**
 * Derive the human-readable label for an "ended" event.
 * Presentation logic owned by frontend.
 */
function endedLabel(endedBy, currentUserId) {
  if (!endedBy) return "This conversation has ended.";
  return endedBy === currentUserId
    ? "You ended this conversation."
    : "Your partner ended this conversation.";
}

/**
 * Composite dedup key for a message to prevent duplicates on reconnect/pagination.
 */
function msgKey(m) {
  return `${m.type}-${m.sender_id ?? "sys"}-${String(m.timestamp)}`;
}

// ─── sub-components ───────────────────────────────────────────────────────────

function Avatar({ emoji, size = "md" }) {
  const cls = size === "sm" ? "h-7 w-7 text-sm" : "h-10 w-10 text-xl";
  return (
    <div
      className={`flex flex-shrink-0 items-center justify-center rounded-full bg-red-100 shadow-inner ${cls}`}
    >
      {emoji || "🎭"}
    </div>
  );
}

function SystemMessage({ content }) {
  return (
    <div className="flex justify-center my-2 select-none">
      <span className="rounded-full bg-slate-200/80 px-3 py-1 text-xs font-medium text-slate-500">
        {content}
      </span>
    </div>
  );
}

function ChatBubble({ msg, isMe, opponentAvatar, opponentNick }) {
  return (
    <div className={`flex items-end gap-2 ${isMe ? "justify-end" : "justify-start"}`}>
      {!isMe && <Avatar emoji={msg.sender_avatar || opponentAvatar} size="sm" />}
      <div className={`flex max-w-[72%] flex-col gap-0.5 ${isMe ? "items-end" : "items-start"}`}>
        {!isMe && (
          <span className="ml-1 text-xs font-semibold text-slate-400">
            {msg.sender_name || opponentNick}
          </span>
        )}
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
            isMe
              ? "rounded-br-none bg-red-700 text-white"
              : "rounded-bl-none border border-slate-200 bg-white text-slate-900"
          }`}
        >
          <p className="whitespace-pre-wrap break-words leading-relaxed">{msg.content}</p>
        </div>
        <span className="px-1 text-xs text-slate-400">{formatTime(msg.timestamp)}</span>
      </div>
    </div>
  );
}

function FriendRequestBanner({ req, onAccept, onDecline }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-5 py-2.5">
      <div className="flex min-w-0 items-center gap-2 text-sm text-amber-900">
        <span className="flex-shrink-0 text-base">{req.from_avatar || "🤝"}</span>
        <span className="truncate">
          <strong>{req.from_name}</strong> wants to add you as a friend and share real emails.
        </span>
      </div>
      <div className="flex flex-shrink-0 items-center gap-2">
        <button
          onClick={onAccept}
          className="rounded-lg bg-green-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-green-700"
        >
          Accept
        </button>
        <button
          onClick={onDecline}
          className="rounded-lg bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-300"
        >
          Decline
        </button>
      </div>
    </div>
  );
}

function FriendAcceptedBanner({ countdown, onOpenMessages, message }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-green-200 bg-green-50 px-5 py-2.5">
      <div className="flex min-w-0 items-center gap-2 text-sm text-green-800">
        <span>🎉</span>
        <span className="truncate">
          {message || "You are now friends!"} Redirecting to private messages in{" "}
          <strong className="text-green-900 font-bold">{countdown}s</strong>...
        </span>
      </div>
      <div className="flex flex-shrink-0 items-center gap-2">
        <button
          onClick={onOpenMessages}
          className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-green-700"
        >
          Go to Messages Now →
        </button>
      </div>
    </div>
  );
}

// ─── main component ───────────────────────────────────────────────────────────

export default function Chat() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.user);

  // Core chat state
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [connected, setConnected] = useState(false);
  const [isEnded, setIsEnded] = useState(false);
  const [metaLoaded, setMetaLoaded] = useState(false);

  // Pagination state (Bất cập 4)
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  // Opponent & Social state
  const [opponent, setOpponent] = useState({
    id: null,
    nickname: "Anonymous Partner",
    avatar: DEFAULT_AVATAR,
    email: null,
  });
  const [friendRequestPending, setFriendRequestPending] = useState(false);
  const [receivedFriendRequest, setReceivedFriendRequest] = useState(null);

  // Auto-redirect countdown state (Bất cập 1)
  const [friendAcceptedInfo, setFriendAcceptedInfo] = useState(null);
  const [redirectCountdown, setRedirectCountdown] = useState(2);

  const socketRef = useRef(null);
  const scrollRef = useRef(null);
  const feedRef = useRef(null);
  const isInitialLoadRef = useRef(true);
  const isPrependingRef = useRef(false);

  // Auto-scroll to bottom on new incoming messages
  useEffect(() => {
    if (isPrependingRef.current) {
      isPrependingRef.current = false;
      return;
    }
    if (isInitialLoadRef.current && messages.length > 0) {
      scrollRef.current?.scrollIntoView({ behavior: "auto" });
      isInitialLoadRef.current = false;
    } else {
      scrollRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Handle 2s redirect countdown when friend request is accepted (Bất cập 1)
  useEffect(() => {
    if (!friendAcceptedInfo) return;

    if (redirectCountdown <= 0) {
      navigate(`/messages?friendId=${friendAcceptedInfo.id}`);
      return;
    }

    const timer = setTimeout(() => {
      setRedirectCountdown((prev) => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [friendAcceptedInfo, redirectCountdown, navigate]);

  // ── 1. Single round-trip initialization via /conversations/{roomId}/init ──
  useEffect(() => {
    const fetchInitData = async () => {
      try {
        const initRes = await apiFetch(`/conversations/${roomId}/init?limit=20`);
        if (initRes.ok) {
          const initData = await initRes.json();
          if (initData?.meta && Array.isArray(initData?.history)) {
            return {
              meta: initData.meta,
              history: initData.history,
              hasMore: Boolean(initData.has_more),
            };
          }
        }
      } catch (e) {
        console.warn("Init endpoint failed, falling back to meta+history:", e);
      }

      // Fallback: fetch meta and history in parallel
      const [meta, history] = await Promise.all([
        apiFetch(`/conversations/${roomId}/meta`)
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
        apiFetch(`/conversations/${roomId}/history?limit=20`)
          .then((r) => (r.ok ? r.json() : []))
          .catch(() => []),
      ]);
      const historyList = Array.isArray(history) ? history : history?.messages || [];
      const hasMoreFlag = Array.isArray(history) ? false : Boolean(history?.has_more);
      return { meta, history: historyList, hasMore: hasMoreFlag };
    };

    fetchInitData().then(({ meta, history, hasMore: moreFlag }) => {
      if (meta) {
        if (meta.opponent) {
          setOpponent((prev) => ({
            ...prev,
            id: meta.opponent.id ?? prev.id,
            nickname: meta.opponent.nickname || prev.nickname,
            avatar: meta.opponent.avatar || prev.avatar,
            email: meta.opponent.email ?? prev.email,
          }));
        }
      }

      const msgs = Array.isArray(history) ? history : [];
      const enriched = msgs.map((msg) => {
        if (msg.type === "ended") {
          return {
            ...msg,
            content: endedLabel(msg.ended_by, currentUser?.id),
          };
        }
        return msg;
      });
      setMessages(enriched);
      setHasMore(moreFlag);

      const endedFromMeta = !!meta?.ended_at;
      const endedFromHistory = msgs.some((m) => m.type === "ended");
      setIsEnded(endedFromMeta || endedFromHistory);
    }).finally(() => setMetaLoaded(true));
  }, [roomId, currentUser?.id]);

  // ── 2. Infinite Scroll Up: Load older messages (Bất cập 4) ────────────────
  const handleScrollFeed = async () => {
    const el = feedRef.current;
    if (!el || loadingMore || !hasMore || el.scrollTop > 30) return;

    const earliestMsg = messages.find((m) => typeof m.timestamp === "number");
    if (!earliestMsg) return;

    setLoadingMore(true);
    const prevScrollHeight = el.scrollHeight;

    try {
      const res = await apiFetch(
        `/conversations/${roomId}/history?limit=20&before_timestamp=${earliestMsg.timestamp}`
      );
      if (res.ok) {
        const data = await res.json();
        const older = Array.isArray(data) ? data : data.messages || [];
        const hasMoreNext = Array.isArray(data) ? false : Boolean(data.has_more);
        setHasMore(hasMoreNext);

        if (older.length > 0) {
          isPrependingRef.current = true;
          const enrichedOlder = older.map((msg) => {
            if (msg.type === "ended") {
              return { ...msg, content: endedLabel(msg.ended_by, currentUser?.id) };
            }
            return msg;
          });

          setMessages((prev) => {
            const existingKeys = new Set(prev.map(msgKey));
            const uniqueOlder = enrichedOlder.filter((m) => !existingKeys.has(msgKey(m)));
            return [...uniqueOlder, ...prev];
          });

          requestAnimationFrame(() => {
            if (feedRef.current) {
              feedRef.current.scrollTop = feedRef.current.scrollHeight - prevScrollHeight;
            }
          });
        }
      }
    } catch (err) {
      console.error("Error loading older messages:", err);
    } finally {
      setLoadingMore(false);
    }
  };

  // ── 3. WebSocket — only connect when room is active ───────────────────────
  useEffect(() => {
    if (!metaLoaded || isEnded) {
      socketRef.current?.close();
      socketRef.current = null;
      setConnected(false);
      return;
    }

    const wsUrl = buildWsUrl(`/ws/${roomId}`);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = ({ data: raw }) => {
      try {
        const data = JSON.parse(raw);

        switch (data.type) {
          case "room_info":
            if (data.opponent) {
              setOpponent((prev) => ({
                ...prev,
                id: data.opponent.id ?? prev.id,
                nickname: data.opponent.nickname || prev.nickname,
                avatar: data.opponent.avatar || prev.avatar,
                email: data.opponent.email ?? prev.email,
              }));
            }
            break;

          case "message":
            setMessages((prev) => {
              const existingKeys = new Set(prev.map(msgKey));
              return existingKeys.has(msgKey(data)) ? prev : [...prev, data];
            });
            break;

          case "ended":
            setIsEnded(true);
            setMessages((prev) => {
              const enriched = {
                ...data,
                content: endedLabel(data.ended_by, currentUser?.id),
              };
              const existingKeys = new Set(prev.map(msgKey));
              return existingKeys.has(msgKey(enriched)) ? prev : [...prev, enriched];
            });
            break;

          case "friend_request_received":
            if (data.from_user_id !== currentUser?.id) {
              setReceivedFriendRequest(data);
            }
            break;

          case "friend_accepted": {
            // Friend accepted -> trigger 2s auto-redirect to /messages
            setFriendRequestPending(false);
            setReceivedFriendRequest(null);
            setIsEnded(true);

            const oppData =
              data.user_a?.id === currentUser?.id ? data.user_b : data.user_a;
            if (oppData) {
              setOpponent((prev) => ({
                ...prev,
                id: oppData.id ?? prev.id,
                nickname: oppData.nickname || prev.nickname,
                avatar: oppData.avatar || prev.avatar,
                email: oppData.email ?? prev.email,
              }));
              setFriendAcceptedInfo({
                ...oppData,
                bannerMessage: data.message,
              });
              setRedirectCountdown(2);
            }
            break;
          }

          case "friend_declined":
            setFriendRequestPending(false);
            setReceivedFriendRequest(null);
            break;

          case "system":
            setMessages((prev) => {
              const existingKeys = new Set(prev.map(msgKey));
              return existingKeys.has(msgKey(data)) ? prev : [...prev, data];
            });
            break;

          default:
            break;
        }
      } catch (err) {
        console.error("WS parse error:", err);
      }
    };

    ws.onclose = () => setConnected(false);
    ws.onerror = (err) => console.error("WS error:", err);

    return () => ws.close();
  }, [roomId, currentUser?.id, metaLoaded, isEnded]);

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleSendMessage = useCallback(
    (e) => {
      e.preventDefault();
      if (!inputText.trim() || !socketRef.current || !connected || isEnded) return;
      socketRef.current.send(inputText.trim());
      setInputText("");
    },
    [inputText, connected, isEnded]
  );

  const handleSendFriendRequest = useCallback(() => {
    if (!socketRef.current || !connected || isEnded) return;
    socketRef.current.send(JSON.stringify({ type: "friend_request" }));
    setFriendRequestPending(true);
  }, [connected, isEnded]);

  const handleFriendResponse = useCallback(
    (accepted) => {
      if (!socketRef.current || !connected) return;
      socketRef.current.send(JSON.stringify({ type: "friend_response", accepted }));
      setReceivedFriendRequest(null);
    },
    [connected]
  );

  const handleEndChat = useCallback(async () => {
    if (!window.confirm("Are you sure you want to end this conversation?")) return;
    try {
      await apiFetch(`/conversations/${roomId}/end`, { method: "POST" });
      if (!connected) {
        setIsEnded(true);
        setMessages((prev) => {
          const entry = {
            type: "ended",
            ended_by: currentUser?.id,
            content: "You ended this conversation.",
            timestamp: Date.now() / 1000,
          };
          const existingKeys = new Set(prev.map(msgKey));
          return existingKeys.has(msgKey(entry)) ? prev : [...prev, entry];
        });
      }
    } catch (err) {
      console.error("Error ending chat:", err);
    }
  }, [roomId, connected, currentUser?.id]);

  // ── Derived display values ────────────────────────────────────────────────

  const connectionIndicatorClass = isEnded
    ? "bg-slate-400"
    : connected
    ? "bg-green-500 animate-pulse"
    : "bg-amber-400 animate-pulse";

  const connectionLabel = isEnded
    ? "Ended"
    : connected
    ? "Connected"
    : "Reconnecting…";

  const inputDisabled = isEnded || !connected;
  const inputPlaceholder = isEnded
    ? "This conversation has ended"
    : !connected
    ? "Reconnecting…"
    : "Type a message… (Enter to send)";

  return (
    <div className="mx-auto flex h-[84vh] max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 bg-slate-50/80 px-5 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <Avatar emoji={opponent.avatar} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="truncate text-sm font-semibold text-slate-900">
                {opponent.nickname}
              </span>
            </div>
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className={`h-2 w-2 flex-shrink-0 rounded-full ${connectionIndicatorClass}`} />
              <span className="text-xs text-slate-500">{connectionLabel}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-shrink-0 items-center gap-2">
          {!isEnded && (
            <button
              onClick={handleSendFriendRequest}
              disabled={friendRequestPending}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                friendRequestPending
                  ? "cursor-not-allowed bg-slate-100 text-slate-400"
                  : "border border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
              }`}
            >
              {friendRequestPending ? "Request sent…" : "🤝 Add Friend"}
            </button>
          )}

          {!isEnded ? (
            <button
              onClick={handleEndChat}
              className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              End Chat
            </button>
          ) : (
            <button
              onClick={() => navigate("/matching")}
              className="rounded-xl bg-red-700 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-red-800"
            >
              ⚡ New Match
            </button>
          )}
        </div>
      </div>

      {/* ── Friend request banner ────────────────────────────────────────────── */}
      {receivedFriendRequest && !isEnded && (
        <FriendRequestBanner
          req={receivedFriendRequest}
          onAccept={() => handleFriendResponse(true)}
          onDecline={() => handleFriendResponse(false)}
        />
      )}

      {/* ── Friend accepted countdown banner (Bất cập 1) ─────────────────────── */}
      {friendAcceptedInfo && (
        <FriendAcceptedBanner
          countdown={redirectCountdown}
          message={friendAcceptedInfo.bannerMessage}
          onOpenMessages={() => navigate(`/messages?friendId=${friendAcceptedInfo.id}`)}
        />
      )}

      {/* ── Message feed with infinite scroll up (Bất cập 4) ─────────────────── */}
      <div
        ref={feedRef}
        onScroll={handleScrollFeed}
        className="flex-1 space-y-3.5 overflow-y-auto bg-slate-50/40 p-5"
      >
        {loadingMore && (
          <div className="flex justify-center py-1">
            <span className="text-xs text-slate-400 animate-pulse">Loading older messages...</span>
          </div>
        )}

        {messages.length === 0 && metaLoaded && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-slate-400 select-none">
            <span className="text-4xl">💬</span>
            <p className="text-sm font-medium">No messages yet.</p>
            <p className="text-xs">Say hello and start the conversation!</p>
          </div>
        )}

        {messages.map((msg, index) => {
          if (msg.type === "system" || msg.type === "ended") {
            return <SystemMessage key={index} content={msg.content} />;
          }
          const isMe = msg.sender_id === currentUser?.id;
          return (
            <ChatBubble
              key={index}
              msg={msg}
              isMe={isMe}
              opponentAvatar={opponent.avatar}
              opponentNick={opponent.nickname}
            />
          );
        })}

        <div ref={scrollRef} />
      </div>

      {/* ── Input area ──────────────────────────────────────────────────────── */}
      <form
        onSubmit={handleSendMessage}
        className="flex items-center gap-2 border-t border-slate-100 bg-white px-4 py-3"
      >
        <input
          type="text"
          disabled={inputDisabled}
          placeholder={inputPlaceholder}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100 disabled:bg-slate-50 disabled:text-slate-400"
        />
        <button
          type="submit"
          disabled={inputDisabled || !inputText.trim()}
          className="rounded-xl bg-red-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-red-800 disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}
