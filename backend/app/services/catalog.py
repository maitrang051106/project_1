import csv
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_catalog() -> tuple[list[dict], dict[str, dict]]:
    """Tải 68 ngành học HUST từ file CSV seed."""
    catalog_path = Path(__file__).resolve().parents[3] / "db" / "seed" / "hust-68-nganh-2026.csv"
    
    majors = []
    major_map = {}

    if catalog_path.exists():
        with open(catalog_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = {
                    "major_code": row["major_code"],
                    "major_name": row["major_name"],
                    "faculty_code": row["faculty_code"],
                    "faculty_name": row["faculty_name"],
                    "program_type": row.get("program_type", "Chuẩn"),
                    "is_new_2026": row.get("is_new_2026", "FALSE").upper() == "TRUE",
                }
                majors.append(item)
                major_map[item["major_code"].upper()] = item
                major_map[item["major_code"]] = item

    return majors, major_map


def get_all_majors() -> list[dict]:
    """Lấy danh sách tất cả ngành học HUST."""
    majors, _ = load_catalog()
    return majors


def get_major_by_code(code: str) -> dict | None:
    """Tra cứu ngành học theo mã (ví dụ: 'IT1', 'EE2', 'BF1')."""
    _, major_map = load_catalog()
    return major_map.get(code.strip().upper())

