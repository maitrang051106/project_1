import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";

const COMMON_COHORTS = [63, 64, 65, 66, 67, 68, 69, 70, 71];

export default function Onboarding() {
  const navigate = useNavigate();

  const [gender, setGender] = useState("nam");
  const [majorCode, setMajorCode] = useState("");
  const [cohort, setCohort] = useState(68);
  const [catalog, setCatalog] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // Tải danh mục ngành từ backend
    apiFetch("/profile/catalog")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setCatalog(data);
          if (data.length > 0 && !majorCode) {
            setMajorCode(data[0].major_code);
          }
        }
      })
      .catch((err) => console.error("Error loading catalog:", err));
  }, []);

  const filteredMajors = catalog.filter((m) => {
    const q = search.toLowerCase();
    return (
      m.major_code.toLowerCase().includes(q) ||
      m.major_name.toLowerCase().includes(q) ||
      m.faculty_name.toLowerCase().includes(q)
    );
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!majorCode) {
      setError("Vui lòng chọn ngành học của bạn");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch("/profile", {
        method: "POST",
        body: JSON.stringify({
          gender,
          major_code: majorCode,
          cohort: Number(cohort),
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Không thể lưu thông tin hồ sơ");
      }

      navigate("/matching");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg rounded-2xl bg-white p-8 shadow-sm border border-slate-100">
      <div className="mb-6">
        <span className="inline-block rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-700">
          Bước 2 / 2
        </span>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
          Hoàn tất hồ sơ ẩn danh
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Thông tin này chỉ dùng để thuật toán ghép cặp tìm bạn chat phù hợp nhất
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 border border-red-200">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Câu hỏi 1: Giới tính */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">
            1. Bạn là?
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setGender("nam")}
              className={`rounded-xl border py-3 px-4 text-center font-medium transition ${
                gender === "nam"
                  ? "border-red-600 bg-red-50 text-red-700 ring-2 ring-red-600"
                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
              }`}
            >
              👨 Nam
            </button>
            <button
              type="button"
              onClick={() => setGender("nu")}
              className={`rounded-xl border py-3 px-4 text-center font-medium transition ${
                gender === "nu"
                  ? "border-red-600 bg-red-50 text-red-700 ring-2 ring-red-600"
                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
              }`}
            >
              👩 Nữ
            </button>
          </div>
        </div>

        {/* Câu hỏi 2: Ngành học */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1">
            2. Ngành học của bạn tại HUST
          </label>
          <input
            type="text"
            placeholder="Tìm theo mã (IT1) hoặc tên ngành..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mb-2 w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs focus:border-red-600 focus:outline-none"
          />
          <div className="max-h-48 overflow-y-auto rounded-xl border border-slate-200 divide-y divide-slate-100">
            {filteredMajors.map((item) => (
              <label
                key={item.major_code}
                className={`flex items-start gap-3 p-3 cursor-pointer transition ${
                  majorCode === item.major_code ? "bg-red-50" : "hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="major"
                  value={item.major_code}
                  checked={majorCode === item.major_code}
                  onChange={() => setMajorCode(item.major_code)}
                  className="mt-1 text-red-600 focus:ring-red-600"
                />
                <div className="text-sm">
                  <div className="font-medium text-slate-900">
                    <span className="font-mono text-red-700 font-bold mr-1">
                      [{item.major_code}]
                    </span>{" "}
                    {item.major_name}
                  </div>
                  <div className="text-xs text-slate-500">{item.faculty_name}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Câu hỏi 3: Khóa */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">
            3. Khóa sinh viên của bạn
          </label>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
            {COMMON_COHORTS.map((c) => (
              <button
                type="button"
                key={c}
                onClick={() => setCohort(c)}
                className={`rounded-xl border py-2 text-center text-sm font-medium transition ${
                  cohort === c
                    ? "border-red-600 bg-red-50 text-red-700 ring-2 ring-red-600"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                }`}
              >
                K{c}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !majorCode}
          className="w-full rounded-xl bg-red-700 py-3 text-sm font-semibold text-white shadow-sm hover:bg-red-800 disabled:opacity-50 transition"
        >
          {loading ? "Đang lưu..." : "Bắt đầu ghép cặp"}
        </button>
      </form>
    </div>
  );
}
