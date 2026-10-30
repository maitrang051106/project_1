import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { useAuthStore } from "../store/auth";
import { HUST_CATALOG } from "../lib/hustCatalog";
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

  const [nickname, setNickname] = useState(user?.nickname || "");
  const [avatar, setAvatar] = useState(user?.avatar || DEFAULT_AVATAR);
  const [gender, setGender] = useState(GENDER_OPTIONS[0].value);
  const [selectedFaculty, setSelectedFaculty] = useState("");
  const [majorCode, setMajorCode] = useState("");
  const [cohort, setCohort] = useState(DEFAULT_COHORT);
  const [catalog, setCatalog] = useState(HUST_CATALOG);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/profile/catalog")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setCatalog(data);
        }
      })
      .catch((err) => console.error("Error loading catalog:", err));

    apiFetch("/profile/me")
      .then((res) => (res.ok ? res.json() : null))
      .then((prof) => {
        if (prof) {
          if (prof.gender) setGender(prof.gender);
          if (prof.cohort) setCohort(prof.cohort);
          if (prof.major_code) setMajorCode(prof.major_code);
          if (prof.faculty_code) setSelectedFaculty(prof.faculty_code);
        }
      })
      .catch(() => {});
  }, []);

  // Sync selectedFaculty when majorCode is set from existing profile or initial load
  useEffect(() => {
    if (majorCode && catalog.length > 0 && !selectedFaculty) {
      const match = catalog.find(
        (m) => m.major_code.toUpperCase() === majorCode.toUpperCase()
      );
      if (match) {
        setSelectedFaculty(match.faculty_code);
      }
    }
  }, [majorCode, catalog, selectedFaculty]);

  // Extract distinct faculties (Trường/Viện/Khoa)
  const faculties = useMemo(() => {
    const map = new Map();
    for (const item of catalog) {
      if (!map.has(item.faculty_code)) {
        map.set(item.faculty_code, {
          code: item.faculty_code,
          name: item.faculty_name,
        });
      }
    }
    return Array.from(map.values());
  }, [catalog]);

  // Majors in the selected faculty
  const availableMajors = useMemo(() => {
    if (!selectedFaculty) return [];
    return catalog.filter((m) => m.faculty_code === selectedFaculty);
  }, [catalog, selectedFaculty]);

  // Selected major info for preview
  const selectedMajorInfo = useMemo(() => {
    if (!majorCode || catalog.length === 0) return null;
    return (
      catalog.find(
        (m) => m.major_code.toUpperCase() === majorCode.toUpperCase()
      ) || null
    );
  }, [catalog, majorCode]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!majorCode) {
      setError("Please select your School/Faculty and Academic Major");
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
          nickname: nickname.trim() || undefined,
          avatar,
        }),
      });

      let data = {};
      try {
        data = await res.json();
      } catch {
        // Not a JSON response
      }

      if (!res.ok) {
        throw new Error(data?.detail || "Unable to save profile");
      }

      // Update auth store
      if (user) {
        setUser({
          ...user,
          nickname: nickname.trim() || user.nickname,
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
        {/* Step 1: Nickname */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-0.5">
            1. Your Nickname
          </label>
          <p className="text-xs text-slate-500 mb-2">
            Your name for anonymous conversations
          </p>
          <input
            type="text"
            placeholder="e.g. Midnight Owl"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100"
          />
        </div>

        {/* Avatar Selection */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1">
            Choose Avatar Emoji
          </label>
          <p className="text-xs text-slate-500 mb-2">
            Pick an animal icon that represents your profile
          </p>
          <div className="flex flex-wrap gap-2">
            {AVATAR_OPTIONS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                onClick={() => setAvatar(emoji)}
                className={`h-10 w-10 rounded-xl text-xl flex items-center justify-center border transition ${
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

        {/* Step 2: Gender */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-2">
            2. Your Gender
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

        {/* Step 3: School/Faculty -> Major */}
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-semibold text-slate-900 mb-0.5">
              3. School / Faculty / Institute & Academic Major (HUST)
            </label>
            <p className="text-xs text-slate-500">
              Select your School / Faculty / Institute first, then choose your academic major
            </p>
          </div>

          <div className="space-y-3">
            {/* School / Faculty / Institute */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                School / Faculty / Institute
              </label>
              <div className="relative">
                <select
                  value={selectedFaculty}
                  onChange={(e) => {
                    setSelectedFaculty(e.target.value);
                    setMajorCode("");
                  }}
                  className="w-full appearance-none rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 pr-10 text-sm text-slate-800 outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100 cursor-pointer"
                >
                  <option value="">-- Select School / Faculty / Institute --</option>
                  {faculties.map((f) => (
                    <option key={f.code} value={f.code}>
                      {f.name}
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3.5 text-slate-400">
                  <svg className="w-4 h-4 fill-current" viewBox="0 0 20 20">
                    <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Academic Major */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Academic Major
              </label>
              <div className="relative">
                <select
                  value={majorCode}
                  onChange={(e) => setMajorCode(e.target.value)}
                  disabled={!selectedFaculty}
                  className="w-full appearance-none rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 pr-10 text-sm text-slate-800 outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-100 disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed cursor-pointer"
                >
                  <option value="">
                    {selectedFaculty
                      ? `-- Select Academic Major (${availableMajors.length} majors) --`
                      : "-- Please select School / Faculty / Institute first --"}
                  </option>
                  {availableMajors.map((m) => (
                    <option key={m.major_code} value={m.major_code}>
                      [{m.major_code}] {m.major_name} ({m.program_type})
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3.5 text-slate-400">
                  <svg className="w-4 h-4 fill-current" viewBox="0 0 20 20">
                    <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          {/* Selected major badge / info card */}
          {selectedMajorInfo && (
            <div className="rounded-xl border border-red-200 bg-red-50/70 p-3 text-xs text-slate-800 flex items-start gap-2.5 transition animate-fadeIn">
              <span className="inline-block rounded-md bg-red-700 px-2 py-0.5 text-xs font-bold text-white shrink-0">
                {selectedMajorInfo.major_code}
              </span>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-slate-900">
                  {selectedMajorInfo.major_name}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Faculty: {selectedMajorInfo.faculty_name} &bull; Program: {selectedMajorInfo.program_type}
                  {selectedMajorInfo.is_new_2026 && (
                    <span className="ml-1.5 font-semibold text-red-600">
                      (New 2026)
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Step 4: Cohort */}
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-1">
            4. Your Cohort (K63 - K71)
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
          {loading ? "Saving Profile..." : "Save Profile & Continue"}
        </button>
      </form>
    </div>
  );
}
