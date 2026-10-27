import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { useAuthStore } from "../store/auth";
import {
  AVATAR_OPTIONS,
  COHORTS,
  DEFAULT_AVATAR,
  DEFAULT_COHORT,
  GENDER_OPTIONS,
} from "../lib/constants";

export default function Onboarding() {
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();

  const [nickname, setNickname] = useState(user?.anon_name || "");
  const [avatar, setAvatar] = useState(user?.avatar || DEFAULT_AVATAR);
  const [gender, setGender] = useState(GENDER_OPTIONS[0].value);
  const [majorCode, setMajorCode] = useState("");
  const [cohort, setCohort] = useState(DEFAULT_COHORT);
  const [catalog, setCatalog] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
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
      setError("Please select your major");
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
          anon_name: nickname.trim() || undefined,
          avatar,
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Unable to save profile");
      }

      // Update auth store
      if (user) {
        setUser({
          ...user,
          anon_name: nickname.trim() || user.anon_name,
          avatar: avatar || user.avatar,
        });
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
          Setup Profile
        </span>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
          Your Profile & Matching Info
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Personalize your appearance and let our engine match you with the right HUST peers
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 border border-red-200">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Nickname & Avatar */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Your Nickname
            </label>
            <input
              type="text"
              placeholder="e.g. Midnight Coder"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Pick Your Avatar Emoji
            </label>
            <div className="flex flex-wrap gap-2">
              {AVATAR_OPTIONS.map((emoji) => (
                <button
                  key={emoji}
                  type="button"
                  onClick={() => setAvatar(emoji)}
                  className={`h-9 w-9 rounded-xl text-lg flex items-center justify-center border transition ${
                    avatar === emoji
                      ? "border-red-700 bg-red-100 scale-110 shadow-sm"
                      : "border-slate-200 bg-white hover:bg-slate-100"
                  }`}
                >
                  {emoji}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Question 1: Gender */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">
            1. Your Gender
          </label>
          <div className="grid grid-cols-2 gap-3">
            {GENDER_OPTIONS.map((g) => (
              <button
                key={g.value}
                type="button"
                onClick={() => setGender(g.value)}
                className={`flex items-center justify-center gap-2 rounded-xl border p-3.5 text-sm font-medium transition ${
                  gender === g.value
                    ? "border-red-700 bg-red-50/50 text-red-700 font-semibold"
                    : "border-slate-200 text-slate-700 hover:bg-slate-50"
                }`}
              >
                <span>{g.icon}</span>
                <span>{g.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Question 2: Major */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1">
            2. Your Major (HUST)
          </label>
          <p className="text-xs text-slate-500 mb-2">
            Choose from 68 official majors across HUST schools and institutes
          </p>

          <input
            type="text"
            placeholder="Type to search major (e.g. IT1, EE2, Computer Science)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mb-2 w-full rounded-xl border border-slate-200 px-3.5 py-2 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
          />

          <div className="max-h-48 overflow-y-auto rounded-xl border border-slate-200 divide-y divide-slate-100 bg-white">
            {filteredMajors.length === 0 ? (
              <div className="p-3 text-center text-xs text-slate-500">
                No matching majors found
              </div>
            ) : (
              filteredMajors.map((m) => (
                <button
                  type="button"
                  key={m.major_code}
                  onClick={() => setMajorCode(m.major_code)}
                  className={`w-full text-left p-3 text-xs transition flex items-center justify-between ${
                    majorCode === m.major_code
                      ? "bg-red-50/70 font-semibold text-red-800"
                      : "hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <div>
                    <span className="font-bold mr-2 text-red-700">[{m.major_code}]</span>
                    <span>{m.major_name}</span>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    {m.faculty_name}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Question 3: Cohort */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1">
            3. Your Cohort (K63 - K71)
          </label>
          <p className="text-xs text-slate-500 mb-2">
            Select your academic batch from K63 to K71
          </p>

          <div className="grid grid-cols-5 gap-2">
            {COHORTS.map((c) => (
              <button
                type="button"
                key={c}
                onClick={() => setCohort(c)}
                className={`rounded-xl border py-2.5 text-xs font-semibold transition ${
                  cohort === c
                    ? "border-red-700 bg-red-700 text-white shadow-sm"
                    : "border-slate-200 text-slate-700 hover:bg-slate-50"
                }`}
              >
                K{c}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !majorCode}
          className="w-full rounded-xl bg-red-700 py-3 text-sm font-semibold text-white shadow-sm hover:bg-red-800 disabled:opacity-50 transition"
        >
          {loading ? "Saving Profile..." : "Complete Profile & Start Matching"}
        </button>
      </form>
    </div>
  );
}
