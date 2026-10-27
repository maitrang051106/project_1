import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { useAuthStore } from "../store/auth";

export default function Login() {
  const navigate = useNavigate();
  const setUser = useAuthStore((state) => state.setUser);

  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState(1); // 1: nhập email, 2: nhập OTP
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    let timer;
    if (cooldown > 0) {
      timer = setInterval(() => setCooldown((prev) => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [cooldown]);

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail.endsWith("@hust.edu.vn") && !trimmedEmail.endsWith("@sis.hust.edu.vn")) {
      setError("Vui lòng nhập đúng email HUST (@hust.edu.vn hoặc @sis.hust.edu.vn)");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch("/auth/request-otp", {
        method: "POST",
        body: JSON.stringify({ email: trimmedEmail }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Không thể gửi mã OTP. Vui lòng thử lại.");
      }

      setMessage(data.message || "Mã OTP đã được gửi đến email của bạn.");
      setStep(2);
      setCooldown(data.cooldown_seconds || 60);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (!otp.trim() || otp.trim().length !== 6) {
      setError("Mã OTP phải gồm đúng 6 chữ số");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch("/auth/verify-otp", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase(), otp: otp.trim() }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Mã OTP không đúng hoặc đã hết hạn.");
      }

      setUser(data.user);

      if (data.has_profile) {
        navigate("/matching");
      } else {
        navigate("/onboarding");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md rounded-2xl bg-white p-8 shadow-sm border border-slate-100">
      <div className="text-center mb-6">
        <span className="inline-block rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-700">
          HUST Chatbox
        </span>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
          Đăng nhập ẩn danh
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Chỉ dành riêng cho sinh viên & cán bộ Đại học Bách khoa Hà Nội
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 border border-red-200">
          {error}
        </div>
      )}

      {message && (
        <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700 border border-green-200">
          {message}
        </div>
      )}

      {step === 1 ? (
        <form onSubmit={handleRequestOtp} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Email trường (@hust.edu.vn hoặc @sis.hust.edu.vn)
            </label>
            <input
              type="email"
              required
              placeholder="ví dụ: nam.nv210001@sis.hust.edu.vn"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-red-600 focus:outline-none focus:ring-1 focus:ring-red-600"
            />
          </div>

          <button
            type="submit"
            disabled={loading || cooldown > 0}
            className="w-full rounded-xl bg-red-700 py-3 text-sm font-semibold text-white shadow-sm hover:bg-red-800 disabled:opacity-50 transition"
          >
            {loading ? "Đang gửi OTP..." : cooldown > 0 ? `Gửi lại sau ${cooldown}s` : "Nhận mã OTP"}
          </button>
        </form>
      ) : (
        <form onSubmit={handleVerifyOtp} className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="block text-sm font-medium text-slate-700">
                Nhập mã OTP 6 số
              </label>
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs text-red-600 hover:underline"
              >
                Đổi email
              </button>
            </div>
            <input
              type="text"
              maxLength={6}
              required
              placeholder="123456"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              className="w-full rounded-xl border border-slate-300 px-4 py-2.5 text-center text-xl font-mono tracking-widest focus:border-red-600 focus:outline-none focus:ring-1 focus:ring-red-600"
            />
          </div>

          <button
            type="submit"
            disabled={loading || otp.length !== 6}
            className="w-full rounded-xl bg-red-700 py-3 text-sm font-semibold text-white shadow-sm hover:bg-red-800 disabled:opacity-50 transition"
          >
            {loading ? "Đang xác thực..." : "Vào Chatbox"}
          </button>

          <div className="text-center">
            <button
              type="button"
              disabled={cooldown > 0 || loading}
              onClick={handleRequestOtp}
              className="text-xs text-slate-500 hover:text-slate-800 disabled:opacity-40"
            >
              {cooldown > 0 ? `Chưa nhận được? Gửi lại sau ${cooldown}s` : "Gửi lại mã OTP"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
