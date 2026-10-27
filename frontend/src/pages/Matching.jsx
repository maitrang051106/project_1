import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import {
  TARGET_COHORT_OPTIONS,
  TARGET_GENDER_OPTIONS,
  TARGET_MAJOR_FACULTY_OPTIONS,
} from "../lib/constants";

export default function Matching() {
  const navigate = useNavigate();

  const [targetGender, setTargetGender] = useState(TARGET_GENDER_OPTIONS[0].id);
  const [targetMajorFaculty, setTargetMajorFaculty] = useState(TARGET_MAJOR_FACULTY_OPTIONS[0].id);
  const [targetCohort, setTargetCohort] = useState(TARGET_COHORT_OPTIONS[0].id);

  const [isSearching, setIsSearching] = useState(false);
  const [searchTimer, setSearchTimer] = useState(0);
  const [error, setError] = useState("");

  // Polling queue status
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

  // Search timer
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
        throw new Error(data.detail || "Unable to join matching queue");
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
          Anonymous Match
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Set your 3 mutual preference filters to find a HUST conversation partner
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 border border-red-200">
          {error}
        </div>
      )}

      {!isSearching ? (
        <form onSubmit={handleStartMatch} className="space-y-6">
          {/* Target Gender */}
          <div>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              1. Looking for Gender
            </label>
            <div className="grid grid-cols-3 gap-2">
              {TARGET_GENDER_OPTIONS.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setTargetGender(item.id)}
                  className={`flex flex-col items-center justify-center rounded-xl border p-3 text-xs font-medium transition ${
                    targetGender === item.id
                      ? "border-red-700 bg-red-50/50 text-red-700 font-semibold shadow-sm"
                      : "border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <span className="text-lg mb-1">{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Target Major / Faculty */}
          <div>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              2. Major / School
            </label>
            <div className="grid grid-cols-2 gap-2">
              {TARGET_MAJOR_FACULTY_OPTIONS.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setTargetMajorFaculty(item.id)}
                  className={`rounded-xl border p-3 text-xs font-medium text-left transition ${
                    targetMajorFaculty === item.id
                      ? "border-red-700 bg-red-50/50 text-red-700 font-semibold shadow-sm"
                      : "border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Target Cohort */}
          <div>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              3. Cohort (Batch)
            </label>
            <div className="grid grid-cols-2 gap-2">
              {TARGET_COHORT_OPTIONS.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setTargetCohort(item.id)}
                  className={`rounded-xl border p-3 text-xs font-medium text-left transition ${
                    targetCohort === item.id
                      ? "border-red-700 bg-red-50/50 text-red-700 font-semibold shadow-sm"
                      : "border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            className="w-full rounded-xl bg-red-700 py-3 text-sm font-semibold text-white shadow-sm hover:bg-red-800 transition"
          >
            Start Matching
          </button>
        </form>
      ) : (
        /* Radar Animation Screen */
        <div className="flex flex-col items-center justify-center py-10">
          <div className="relative flex h-36 w-36 items-center justify-center">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-200 opacity-75" />
            <span className="absolute inline-flex h-24 w-24 animate-pulse rounded-full bg-red-100 opacity-75" />
            <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-red-700 text-2xl text-white shadow-md">
              ⚡
            </div>
          </div>

          <h3 className="mt-6 text-lg font-bold text-slate-900">
            Finding a matching peer...
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            Searching for students matching your criteria ({searchTimer}s)
          </p>

          <button
            onClick={handleCancelMatch}
            className="mt-8 rounded-xl border border-slate-200 bg-white px-6 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
          >
            Cancel Search
          </button>
        </div>
      )}
    </div>
  );
}
