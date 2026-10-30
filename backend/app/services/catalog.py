import csv
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_catalog() -> tuple[list[dict], dict[str, dict]]:
    """Load 68 HUST academic majors from CSV seed file."""
    candidate_paths = [
        Path(__file__).resolve().parents[3] / "db" / "seed" / "hust-68-nganh-2026.csv",
        Path(__file__).resolve().parents[2] / "db" / "seed" / "hust-68-nganh-2026.csv",
        Path.cwd() / "db" / "seed" / "hust-68-nganh-2026.csv",
        Path("/app/db/seed/hust-68-nganh-2026.csv"),
    ]

    catalog_path = next((p for p in candidate_paths if p.exists()), None)
    
    majors = []
    major_map = {}

    if catalog_path and catalog_path.exists():
        with open(catalog_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = {k.strip().lstrip("\ufeff"): v for k, v in raw_row.items() if k}
                major_code = row.get("major_code", "").strip()
                if not major_code:
                    continue
                item = {
                    "major_code": major_code,
                    "major_name": row.get("major_name", "").strip(),
                    "faculty_code": row.get("faculty_code", "").strip(),
                    "faculty_name": row.get("faculty_name", "").strip(),
                    "program_type": row.get("program_type", "Standard").strip(),
                    "is_new_2026": str(row.get("is_new_2026", "FALSE")).strip().upper() == "TRUE",
                }
                majors.append(item)
                major_map[item["major_code"].upper()] = item
                major_map[item["major_code"]] = item

    return majors, major_map


def get_all_majors() -> list[dict]:
    """Retrieve all HUST academic majors."""
    majors, _ = load_catalog()
    return majors


def get_major_by_code(code: str) -> dict | None:
    """Lookup major by code (e.g. 'IT1', 'EE2', 'BF1')."""
    _, major_map = load_catalog()
    return major_map.get(code.strip().upper())

