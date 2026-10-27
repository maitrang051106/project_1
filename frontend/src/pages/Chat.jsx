import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { useAuthStore } from "../store/auth";
import { DEFAULT_AVATAR } from "../lib/constants";

export default function Chat() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.user);

  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [connected, setConnected] = useState(false);
  const [isEnded, setIsEnded] = useState(false);

  // Opponent & Friendship states
  const [opponent, setOpponent] = useState({
    id: null,
    anon_name: "Anonymous Partner",
    avatar: DEFAULT_AVATAR,
    email: null,
  });
  const [isFriend, setIsFriend] = useState(false);
  const [friendRequestPending, setFriendRequestPending] = useState(false);
  const [receivedFriendRequest, setReceivedFriendRequest] = useState(null);
  const [friendSuccessMsg, setFriendSuccessMsg] = useState("");

  const socketRef = useRef(null);
  const scrollRef = useRef(null);

  // Scroll to latest message
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // WebSocket connection
  useEffect(() => {
    let baseWsUrl = import.meta.env.VITE_WS_URL;
    if (!baseWsUrl) {
      const loc = window.location;
      baseWsUrl =
        (loc.protocol === "https:" ? "wss://" : "ws://") +
        (loc.hostname === "localhost" ? "localhost:8000" : loc.host);
    }
    const wsUrl = `${baseWsUrl.replace(/\/$/, "")}/ws/${roomId}`;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "room_info") {
          if (data.opponent) {
            setOpponent(data.opponent);
          }
          if (data.is_friend) {
            setIsFriend(true);
          }
        } else if (data.type === "ended") {
          setIsEnded(true);
          setMessages((prev) => [...prev, data]);
        } else if (data.type === "friend_request_received") {
          if (data.from_user_id !== currentUser?.id) {
            setReceivedFriendRequest(data);
          }
        } else if (data.type === "friend_accepted") {
          setIsFriend(true);
          setFriendRequestPending(false);
          setReceivedFriendRequest(null);

          // Identify opponent email
          const oppData =
            data.user_a?.id === currentUser?.id ? data.user_b : data.user_a;
          if (oppData) {
            setOpponent((prev) => ({
              ...prev,
              anon_name: oppData.anon_name || prev.anon_name,
              avatar: oppData.avatar || prev.avatar,
              email: oppData.email,
            }));
          }
          setFriendSuccessMsg(
            `You are now friends! Real email revealed: ${oppData?.email || "verified"}`
          );
        } else if (data.type === "friend_declined") {
          setFriendRequestPending(false);
          setReceivedFriendRequest(null);
        } else {
          setMessages((prev) => [...prev, data]);
        }
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = (err) => {
      console.error("WebSocket connection error:", err);
    };

    return () => {
      ws.close();
    };
  }, [roomId, currentUser?.id]);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputText.trim() || !socketRef.current || !connected || isEnded) return;

    socketRef.current.send(inputText.trim());
    setInputText("");
  };

  const handleSendFriendRequest = () => {
    if (!socketRef.current || !connected || isEnded || isFriend) return;
    socketRef.current.send(JSON.stringify({ type: "friend_request" }));
    setFriendRequestPending(true);
  };

  const handleFriendResponse = (accepted) => {
    if (!socketRef.current || !connected) return;
    socketRef.current.send(
      JSON.stringify({ type: "friend_response", accepted })
    );
    setReceivedFriendRequest(null);
  };

  const handleEndChat = async () => {
    if (window.confirm("Are you sure you want to end this conversation?")) {
      try {
        await apiFetch(`/conversations/${roomId}/end`, { method: "POST" });
        setIsEnded(true);
      } catch (err) {
        console.error("Error ending chat:", err);
      }
    }
  };

  return (
    <div className="mx-auto flex h-[82vh] max-w-2xl flex-col rounded-2xl bg-white shadow-sm border border-slate-200 overflow-hidden">
      {/* Chat Header */}
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/70 px-5 py-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 text-xl shadow-inner">
            {opponent.avatar || "🎭"}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 text-sm">
                {opponent.anon_name || "Anonymous Partner"}
              </span>
              {isFriend && opponent.email && (
                <span className="rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-semibold text-green-800">
                  ✉️ {opponent.email}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <span
                className={`h-2 w-2 rounded-full ${
                  connected && !isEnded ? "bg-green-500 animate-pulse" : "bg-slate-400"
                }`}
              />
              <span>
                {isEnded ? "Ended" : connected ? "Connected" : "Reconnecting..."}
              </span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {!isFriend && !isEnded && (
            <button
              onClick={handleSendFriendRequest}
              disabled={friendRequestPending}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                friendRequestPending
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                  : "bg-red-50 text-red-700 hover:bg-red-100 border border-red-200"
              }`}
            >
              {friendRequestPending ? "Request Sent..." : "🤝 Add Friend"}
            </button>
          )}

          {!isEnded ? (
            <button
              onClick={handleEndChat}
              className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
            >
              End Chat
            </button>
          ) : (
            <button
              onClick={() => navigate("/matching")}
              className="rounded-xl bg-red-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-800 transition"
            >
              New Match
            </button>
          )}
        </div>
      </div>

      {/* Received Friend Request Banner */}
      {receivedFriendRequest && !isEnded && (
        <div className="bg-amber-50 border-b border-amber-200 px-5 py-2.5 flex items-center justify-between text-xs text-amber-900">
          <div className="flex items-center gap-2">
            <span className="text-base">{receivedFriendRequest.from_avatar || "🤝"}</span>
            <span>
              <strong>{receivedFriendRequest.from_name}</strong> wants to add you as friend and reveal real emails.
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleFriendResponse(true)}
              className="rounded-lg bg-green-600 px-3 py-1 text-xs font-semibold text-white hover:bg-green-700 transition"
            >
              Accept
            </button>
            <button
              onClick={() => handleFriendResponse(false)}
              className="rounded-lg bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-300 transition"
            >
              Decline
            </button>
          </div>
        </div>
      )}

      {/* Friend Success Banner */}
      {friendSuccessMsg && (
        <div className="bg-green-50 border-b border-green-200 px-5 py-2 text-xs text-green-800 flex items-center justify-between">
          <span>🎉 {friendSuccessMsg}</span>
          <button
            onClick={() => setFriendSuccessMsg("")}
            className="text-green-600 hover:text-green-900 font-bold ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Message Feed */}
      <div className="flex-1 overflow-y-auto p-5 space-y-3.5 bg-slate-50/40">
        {messages.map((msg, index) => {
          if (msg.type === "system" || msg.type === "ended") {
            return (
              <div key={index} className="flex justify-center my-2">
                <span className="rounded-full bg-slate-200/80 px-3 py-1 text-[11px] font-medium text-slate-600">
                  {msg.content}
                </span>
              </div>
            );
          }

          const isMe = msg.sender_id === currentUser?.id;
          return (
            <div
              key={index}
              className={`flex items-end gap-2 ${isMe ? "justify-end" : "justify-start"}`}
            >
              {!isMe && (
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-200 text-sm">
                  {msg.sender_avatar || opponent.avatar || DEFAULT_AVATAR}
                </div>
              )}
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                  isMe
                    ? "bg-red-700 text-white rounded-br-none"
                    : "bg-white text-slate-900 border border-slate-200 rounded-bl-none"
                }`}
              >
                {!isMe && (
                  <div className="text-[10px] font-bold text-slate-400 mb-0.5">
                    {msg.sender_name || opponent.anon_name}
                  </div>
                )}
                <p className="whitespace-pre-wrap break-words leading-relaxed">
                  {msg.content}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={scrollRef} />
      </div>

      {/* Input Area */}
      <form
        onSubmit={handleSendMessage}
        className="flex items-center gap-2 border-t border-slate-100 bg-white p-3.5"
      >
        <input
          type="text"
          disabled={isEnded || !connected}
          placeholder={
            isEnded
              ? "This conversation has ended"
              : "Type a message... (Press Enter to send)"
          }
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100 disabled:bg-slate-50"
        />
        <button
          type="submit"
          disabled={isEnded || !connected || !inputText.trim()}
          className="rounded-xl bg-red-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-red-800 disabled:opacity-50 transition"
        >
          Send
        </button>
      </form>
    </div>
  );
}
