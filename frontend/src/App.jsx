import { useEffect } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import Chat from "./pages/Chat";
import Login from "./pages/Login";
import Matching from "./pages/Matching";
import Onboarding from "./pages/Onboarding";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuthStore } from "./store/auth";
import { apiFetch } from "./lib/api";

export default function App() {
  const navigate = useNavigate();
  const { user, setUser, clearUser } = useAuthStore();

  // Khôi phục phiên đăng nhập khi load trang
  useEffect(() => {
    apiFetch("/auth/me")
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error("Chưa đăng nhập");
      })
      .then((data) => {
        setUser(data.user);
      })
      .catch(() => {
        clearUser();
      });
  }, [setUser, clearUser]);

  const handleLogout = async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch (e) {
      console.error(e);
    } finally {
      clearUser();
      navigate("/login");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-50">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl">🦅</span>
            <span className="font-bold text-slate-900 tracking-tight">HUST Chatbox</span>
          </Link>

          <nav aria-label="Điều hướng chính" className="flex items-center gap-4">
            {user ? (
              <>
                <Link
                  className="text-sm font-medium text-slate-600 hover:text-red-700"
                  to="/matching"
                >
                  Ghép cặp
                </Link>
                <Link
                  className="text-sm font-medium text-slate-600 hover:text-red-700"
                  to="/onboarding"
                >
                  Hồ sơ
                </Link>
                <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                  <span className="rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-700">
                    {user.anon_name || "Ẩn danh"}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="text-xs text-slate-500 hover:text-slate-800"
                  >
                    Đăng xuất
                  </button>
                </div>
              </>
            ) : (
              <Link
                className="rounded-lg bg-red-700 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-red-800 transition"
                to="/login"
              >
                Đăng nhập
              </Link>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 py-8">
        <Routes>
          <Route element={<Navigate replace to="/login" />} path="/" />
          <Route element={<Login />} path="/login" />
          <Route
            element={
              <ProtectedRoute>
                <Onboarding />
              </ProtectedRoute>
            }
            path="/onboarding"
          />
          <Route
            element={
              <ProtectedRoute>
                <Matching />
              </ProtectedRoute>
            }
            path="/matching"
          />
          <Route
            element={
              <ProtectedRoute>
                <Chat />
              </ProtectedRoute>
            }
            path="/chat/:roomId"
          />
          <Route
            element={
              <section className="text-center py-12">
                <h1 className="text-2xl font-bold">Không tìm thấy trang</h1>
                <p className="mt-2 text-slate-600">
                  Đường dẫn này chưa có trong ứng dụng.
                </p>
                <Link to="/" className="mt-4 inline-block text-sm text-red-700 font-semibold underline">
                  Quay lại trang chủ
                </Link>
              </section>
            }
            path="*"
          />
        </Routes>
      </main>
    </div>
  );
}
