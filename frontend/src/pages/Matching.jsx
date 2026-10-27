import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";

export default function Matching() {
  const navigate = useNavigate();

  const [targetGender, setTargetGender] = useState("bat_ki");
  const [targetMajorFaculty, setTargetMajorFaculty] = useState("bat_ki");
  const [targetCohort, setTargetCohort] = useState("bat_ki");

  const [isSearching, setIsSearching] = useState(false);
  const [searchTimer, setSearchTimer] = useState(0);
  const [error, setError] = useState("");

  // Polling trạng thái khi đang ở hàng đợi
  useEffect(() => {
    let interval;
    if (isSearching) {
      interval = setInterval(async () => {
        try {
          const res = await apiFetch("/match/status");
          if (res.ok) {
            const data = await res.json();
            if (data.status === "matched" && data.room_id) {
              setIsSearching(false);
              navigate(`/chat/${data.room_id}`);
            }
          }
        } catch (err) {
          console.error("Error polling match status:", err);
        }
      }, 2500);
    }
    return () => clearInterval(interval);
  }, [isSearching, navigate]);

  // Bộ đếm thời gian tìm kiếm
  useEffect(() => {
    let t;
    if (isSearching) {
      t = setInterval(() => setSearchTimer((prev) => prev + 1), 1000);
    } else {
      setSearchTimer(0);
    }
    return () => clearInterval(t);
  }, [isSearching]);

  const handleStartMatch = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const res = await apiFetch("/match/join", {
        method: "POST",
        body: JSON.stringify({
          target_gender: targetGender,
          target_major_faculty: targetMajorFaculty,
          target_cohort: targetCohort,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Không thể tham gia hàng đợi");
      }

      if (data.status === "matched" && data.room_id) {
        navigate(`/chat/${data.room_id}`);
      } else {
        setIsSearching(true);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCancelMatch = async () => {
    try {
      await apiFetch("/match/leave", { method: "POST" });
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg rounded-2xl bg-white p-8 shadow-sm border border-slate-100">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Ghép cặp trò chuyện ẩn danh
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Chọn 3 tiêu chí bạn mong muốn ở đối phương
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 border border-red-200">
          {error}
        </div>
      )}

      {isSearching ? (
        <div className="py-12 text-center space-y-6">
          <div className="relative mx-auto flex h-24 w-24 items-center justify-center">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75"></span>
            <div className="relative inline-flex h-20 w-20 items-center justify-center rounded-full bg-red-700 text-3xl text-white shadow-lg">
              🔍
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-slate-900">
              Đang tìm kiếm người phù hợp...
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              Thời gian chờ: <span className="font-mono font-bold text-red-700">{searchTimer}s</span>
            </p>
          </div>

          <button
            onClick={handleCancelMatch}
            type="button"
            className="rounded-xl border border-slate-300 px-6 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
          >
            Hủy tìm kiếm
          </button>
        </div>
      ) : (
        <form onSubmit={handleStartMatch} className="space-y-6">
          {/* Tiêu chí 1: Giới tính */}
          <div>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              1. Giới tính mong muốn
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: "bat_ki", label: "✨ Bất kì" },
                { id: "nam", label: "👨 Nam" },
                { id: "nu", label: "👩 Nữ" },
              ].map((opt) => (
                <button
                  type="button"
                  key={opt.id}
                  onClick={() => setTargetGender(opt.id)}
                  className={`rounded-xl border py-2.5 text-center text-sm font-medium transition ${
                    targetGender === opt.id
                      ? "border-red-600 bg-red-50 text-red-700 ring-2 ring-red-600"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tiêu chí 2: Ngành / Trường */}
          <div>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              2. Tiêu chí Ngành / Trường
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: "bat_ki", label: "🌐 Bất kì" },
                { id: "cung_nganh", label: "🎯 Cùng ngành" },
                { id: "cung_truong_khac_nganh", label: "🏫 Cùng trường (khác ngành)" },
                { id: "khac_truong", label: "🚀 Khác trường/viện" },
              ].map((opt) => (
                <button
                  type="button"
                  key={opt.id}
                  onClick={() => setTargetMajorFaculty(opt.id)}
                  className={`rounded-xl border p-3 text-left text-xs font-medium transition ${
                    targetMajorFaculty === opt.id
                      ? "border-red-600 bg-red-50 text-red-700 ring-2 ring-red-600"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tiêu chí 3: Khóa */}
          <div>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              3. Tiêu chí Khóa học
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: "bat_ki", label: "🎲 Bất kì" },
                { id: "cung_khoa", label: "🤝 Cùng khóa" },
                { id: "khoa_tren", label: "🎓 Khóa trên (Tiền bối)" },
                { id: "khoa_duoi", label: "🌱 Khóa dưới (Hậu bối)" },
              ].map((opt) => (
                <button
                  type="button"
                  key={opt.id}
                  onClick={() => setTargetCohort(opt.id)}
                  className={`rounded-xl border p-3 text-left text-xs font-medium transition ${
                    targetCohort === opt.id
                      ? "border-red-600 bg-red-50 text-red-700 ring-2 ring-red-600"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            className="w-full rounded-xl bg-red-700 py-3.5 text-sm font-semibold text-white shadow-md hover:bg-red-800 transition"
          >
            Bắt đầu tìm kiếm đối phương
          </button>
        </form>
      )}
    </div>
  );
}
