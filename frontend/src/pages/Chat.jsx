import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { useAuthStore } from "../store/auth";

export default function Chat() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.user);

  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [connected, setConnected] = useState(false);
  const [isEnded, setIsEnded] = useState(false);
  const socketRef = useRef(null);
  const scrollRef = useRef(null);

  // Cuộn xuống tin nhắn mới nhất
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Khởi tạo kết nối WebSocket
  useEffect(() => {
    let baseWsUrl = import.meta.env.VITE_WS_URL;
    if (!baseWsUrl) {
      const loc = window.location;
      baseWsUrl = (loc.protocol === "https:" ? "wss://" : "ws://") + (loc.hostname === "localhost" ? "localhost:8000" : loc.host);
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
        if (data.type === "ended") {
          setIsEnded(true);
        }
        setMessages((prev) => [...prev, data]);
      } catch (err) {
        console.error("Lỗi đọc tin nhắn WebSocket:", err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = (err) => {
      console.error("Lỗi kết nối WebSocket:", err);
    };

    return () => {
      ws.close();
    };
  }, [roomId]);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputText.trim() || !socketRef.current || !connected || isEnded) return;

    socketRef.current.send(inputText.trim());
    setInputText("");
  };

  const handleEndChat = async () => {
    if (window.confirm("Bạn có chắc chắn muốn kết thúc cuộc trò chuyện này?")) {
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
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-5 py-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 text-lg">
            🎭
          </div>
          <div>
            <div className="font-semibold text-slate-900 text-sm">
              Bạn Chat Ẩn Danh
            </div>
            <div className="flex items-center gap-1.5 text-xs">
              <span
                className={`h-2 w-2 rounded-full ${
                  connected && !isEnded ? "bg-green-500 animate-pulse" : "bg-slate-400"
                }`}
              />
              <span className="text-slate-500">
                {isEnded ? "Đã kết thúc" : connected ? "Đang trực tuyến" : "Mất kết nối..."}
              </span>
            </div>
          </div>
        </div>

        <div>
          {!isEnded ? (
            <button
              onClick={handleEndChat}
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 transition"
            >
              Kết thúc chat
            </button>
          ) : (
            <button
              onClick={() => navigate("/matching")}
              className="rounded-lg bg-red-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-800 transition"
            >
              Tìm bạn mới
            </button>
          )}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/30">
        <div className="text-center my-2">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] text-slate-500">
            Cuộc hội thoại được mã hóa và ẩn danh 1-1
          </span>
        </div>

        {messages.map((msg, index) => {
          if (msg.type === "system" || msg.type === "ended") {
            return (
              <div key={index} className="text-center my-2">
                <span className="rounded-full bg-slate-100/80 px-2.5 py-0.5 text-xs text-slate-500 italic">
                  {msg.content}
                </span>
              </div>
            );
          }

          const isMe = currentUser && msg.sender_id === currentUser.id;

          return (
            <div
              key={index}
              className={`flex flex-col ${isMe ? "items-end" : "items-start"}`}
            >
              <span className="text-[10px] text-slate-400 mb-0.5 px-1">
                {isMe ? "Tôi" : msg.sender_name || "Đối phương"}
              </span>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed shadow-sm break-words ${
                  isMe
                    ? "bg-red-700 text-white rounded-tr-none"
                    : "bg-white text-slate-800 border border-slate-200/80 rounded-tl-none"
                }`}
              >
                {msg.content}
              </div>
            </div>
          );
        })}
        <div ref={scrollRef} />
      </div>

      {/* Input Message Area */}
      <form
        onSubmit={handleSendMessage}
        className="border-t border-slate-200 bg-white p-3 flex gap-2 items-center"
      >
        <input
          type="text"
          disabled={isEnded || !connected}
          placeholder={
            isEnded
              ? "Cuộc hội thoại đã kết thúc"
              : !connected
              ? "Đang kết nối lại..."
              : "Nhập tin nhắn (Enter để gửi)..."
          }
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:border-red-600 focus:outline-none focus:ring-1 focus:ring-red-600 disabled:bg-slate-100 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || isEnded || !connected}
          className="rounded-xl bg-red-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-800 disabled:opacity-40 transition shadow-sm"
        >
          Gửi
        </button>
      </form>
    </div>
  );
}
