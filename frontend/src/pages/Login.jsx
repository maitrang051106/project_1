import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { useAuthStore } from "../store/auth";
import { STUDENT_EMAIL_DOMAIN } from "../lib/constants";

function EyeIcon({ show }) {
  return show ? (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
    </svg>
  ) : (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  );
}

export default function Login() {
  const navigate = useNavigate();
  const setUser = useAuthStore((state) => state.setUser);

  // Modes: 'login' | 'register' | 'forgot'
  const [mode, setMode] = useState("login");

  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Flow states
  const [otpSent, setOtpSent] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const switchMode = (newMode) => {
    setMode(newMode);
    setError("");
    setMessage("");
    setOtpSent(false);
    setPassword("");
    setConfirmPassword("");
    setOtp("");
    setShowPassword(false);
    setShowConfirmPassword(false);
  };

  const handleSendOtp = async (endpoint, successMsg) => {
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail.endsWith(STUDENT_EMAIL_DOMAIN)) {
      setError(`Please use your official HUST student email (${STUDENT_EMAIL_DOMAIN})`);
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const res = await apiFetch(endpoint, {
        method: "POST",
        body: JSON.stringify({ email: trimmedEmail }),
      });
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || "Unable to reach server. Please ensure backend is running.");
      }

      setOtpSent(true);
      setCooldown(data.cooldown_seconds || 60);
      setMessage(successMsg || "Verification code sent to your email!");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail.endsWith(STUDENT_EMAIL_DOMAIN)) {
      setError(`Only ${STUDENT_EMAIL_DOMAIN} student emails are accepted.`);
      return;
    }
    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const res = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: trimmedEmail, password }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(data?.detail || "Unable to reach server or invalid credentials.");
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

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!otp.trim()) {
      setError("Please enter the 6-digit verification code.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const res = await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otp.trim(),
          password,
        }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(data?.detail || "Registration failed. Please check your connection.");
      }

      setUser(data.user);
      navigate("/onboarding");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!otp.trim()) {
      setError("Please enter the verification code.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const res = await apiFetch("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otp.trim(),
          new_password: password,
        }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(data?.detail || "Password reset failed. Please check your connection.");
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
    <div className="mx-auto max-w-md py-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        {/* Header Tabs */}
        <div className="mb-6 flex border-b border-slate-100 pb-3">
          <button
            type="button"
            onClick={() => switchMode("login")}
            className={`flex-1 py-1 text-center text-sm font-semibold transition ${
              mode === "login"
                ? "border-b-2 border-red-700 text-red-700"
                : "text-slate-400 hover:text-slate-700"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => switchMode("register")}
            className={`flex-1 py-1 text-center text-sm font-semibold transition ${
              mode === "register"
                ? "border-b-2 border-red-700 text-red-700"
                : "text-slate-400 hover:text-slate-700"
            }`}
          >
            Sign Up
          </button>
          <button
            type="button"
            onClick={() => switchMode("forgot")}
            className={`flex-1 py-1 text-center text-sm font-semibold transition ${
              mode === "forgot"
                ? "border-b-2 border-red-700 text-red-700"
                : "text-slate-400 hover:text-slate-700"
            }`}
          >
            Reset
          </button>
        </div>

        {/* Title */}
        <div className="mb-5 text-center">
          <span className="text-3xl">🦅</span>
          <h1 className="mt-2 text-xl font-bold tracking-tight text-slate-900">
            {mode === "login" && "Welcome Back"}
            {mode === "register" && "Create HUST Account"}
            {mode === "forgot" && "Reset Password"}
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            {mode === "login" && "Enter your @sis.hust.edu.vn credentials to continue"}
            {mode === "register" && "Verify with your @sis.hust.edu.vn email to start chatting"}
            {mode === "forgot" && "Verify email OTP to set a new password"}
          </p>
        </div>

        {/* Alerts */}
        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            {error}
          </div>
        )}
        {message && (
          <div className="mb-4 rounded-xl border border-green-200 bg-green-50 p-3 text-xs text-green-700">
            {message}
          </div>
        )}

        {/* Mode: LOGIN */}
        {mode === "login" && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Student Email
              </label>
              <input
                type="email"
                required
                placeholder="nam.nv210000@sis.hust.edu.vn"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-slate-700">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => switchMode("forgot")}
                  className="text-xs text-red-700 hover:underline"
                >
                  Forgot?
                </button>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 pr-10 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  <EyeIcon show={showPassword} />
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-red-700 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-red-800 disabled:opacity-50 transition"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>

            <div className="text-center pt-2">
              <span className="text-xs text-slate-500">Don't have an account? </span>
              <button
                type="button"
                onClick={() => switchMode("register")}
                className="text-xs font-semibold text-red-700 hover:underline"
              >
                Sign Up
              </button>
            </div>
          </form>
        )}

        {/* Mode: REGISTER */}
        {mode === "register" && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Student Email (@sis.hust.edu.vn)
              </label>
              <div className="flex gap-2">
                <input
                  type="email"
                  disabled={otpSent}
                  placeholder="nam.nv210000@sis.hust.edu.vn"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="flex-1 rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100 disabled:bg-slate-50"
                />
                {!otpSent ? (
                  <button
                    type="button"
                    disabled={loading || !email}
                    onClick={() => handleSendOtp("/auth/request-register-otp", "Verification code sent!")}
                    className="rounded-xl bg-red-700 px-3 py-2.5 text-xs font-semibold text-white hover:bg-red-800 disabled:opacity-50 transition whitespace-nowrap"
                  >
                    {loading ? "Sending..." : "Send Code"}
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={loading || cooldown > 0}
                    onClick={() => handleSendOtp("/auth/request-register-otp", "New code sent!")}
                    className="rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition whitespace-nowrap"
                  >
                    {cooldown > 0 ? `${cooldown}s` : "Resend"}
                  </button>
                )}
              </div>
            </div>

            {otpSent && (
              <form onSubmit={handleRegister} className="space-y-4 pt-2 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    6-Digit Verification Code
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    required
                    placeholder="123456"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                    className="w-full text-center tracking-widest text-lg font-bold rounded-xl border border-slate-200 px-3.5 py-2 outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      placeholder="At least 6 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-3.5 py-2 pr-10 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                      tabIndex={-1}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      <EyeIcon show={showPassword} />
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      placeholder="Re-type password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-3.5 py-2 pr-10 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                      tabIndex={-1}
                      aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                    >
                      <EyeIcon show={showConfirmPassword} />
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl bg-red-700 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-red-800 disabled:opacity-50 transition"
                >
                  {loading ? "Creating Account..." : "Create Account"}
                </button>
              </form>
            )}

            <div className="text-center pt-2">
              <span className="text-xs text-slate-500">Already have an account? </span>
              <button
                type="button"
                onClick={() => switchMode("login")}
                className="text-xs font-semibold text-red-700 hover:underline"
              >
                Sign In
              </button>
            </div>
          </div>
        )}

        {/* Mode: FORGOT PASSWORD */}
        {mode === "forgot" && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Your Student Email (@sis.hust.edu.vn)
              </label>
              <div className="flex gap-2">
                <input
                  type="email"
                  disabled={otpSent}
                  placeholder="nam.nv210000@sis.hust.edu.vn"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="flex-1 rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100 disabled:bg-slate-50"
                />
                {!otpSent ? (
                  <button
                    type="button"
                    disabled={loading || !email}
                    onClick={() => handleSendOtp("/auth/request-reset-otp", "Reset code sent to your email!")}
                    className="rounded-xl bg-red-700 px-3 py-2.5 text-xs font-semibold text-white hover:bg-red-800 disabled:opacity-50 transition whitespace-nowrap"
                  >
                    {loading ? "Sending..." : "Send Code"}
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={loading || cooldown > 0}
                    onClick={() => handleSendOtp("/auth/request-reset-otp", "New reset code sent!")}
                    className="rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition whitespace-nowrap"
                  >
                    {cooldown > 0 ? `${cooldown}s` : "Resend"}
                  </button>
                )}
              </div>
            </div>

            {otpSent && (
              <form onSubmit={handleResetPassword} className="space-y-4 pt-2 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    6-Digit Verification Code
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    required
                    placeholder="123456"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                    className="w-full text-center tracking-widest text-lg font-bold rounded-xl border border-slate-200 px-3.5 py-2 outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      placeholder="At least 6 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-3.5 py-2 pr-10 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                      tabIndex={-1}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      <EyeIcon show={showPassword} />
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      placeholder="Re-type new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-3.5 py-2 pr-10 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                      tabIndex={-1}
                      aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                    >
                      <EyeIcon show={showConfirmPassword} />
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl bg-red-700 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-red-800 disabled:opacity-50 transition"
                >
                  {loading ? "Updating..." : "Reset Password & Sign In"}
                </button>
              </form>
            )}

            <div className="text-center pt-2">
              <button
                type="button"
                onClick={() => switchMode("login")}
                className="text-xs font-semibold text-slate-600 hover:underline"
              >
                ← Back to Sign In
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
