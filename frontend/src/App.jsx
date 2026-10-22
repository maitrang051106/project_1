import { Link, Navigate, Route, Routes } from "react-router-dom";
import Chat from "./pages/Chat";
import Login from "./pages/Login";
import Matching from "./pages/Matching";
import Onboarding from "./pages/Onboarding";

const pages = [
  { to: "/login", label: "Đăng nhập" },
  { to: "/onboarding", label: "Hồ sơ" },
  { to: "/matching", label: "Ghép cặp" },
  { to: "/chat/demo", label: "Phòng chat" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <nav
          aria-label="Điều hướng chính"
          className="mx-auto flex max-w-5xl flex-wrap gap-4 px-5 py-4"
        >
          {pages.map((page) => (
            <Link
              className="text-sm font-medium text-slate-600 hover:text-red-700"
              key={page.to}
              to={page.to}
            >
              {page.label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-5 py-10">
        <Routes>
          <Route element={<Navigate replace to="/login" />} path="/" />
          <Route element={<Login />} path="/login" />
          <Route element={<Onboarding />} path="/onboarding" />
          <Route element={<Matching />} path="/matching" />
          <Route element={<Chat />} path="/chat/:roomId" />
          <Route
            element={
              <section>
                <h1 className="text-2xl font-bold">Không tìm thấy trang</h1>
                <p className="mt-2 text-slate-600">
                  Đường dẫn này chưa có trong ứng dụng.
                </p>
              </section>
            }
            path="*"
          />
        </Routes>
      </main>
    </div>
  );
}
