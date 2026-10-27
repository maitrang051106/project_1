import csv
import re
import unicodedata
from pathlib import Path


PROGRAMS_CSV = Path(__file__).with_name("hust-68-nganh-2026.csv")
SCHOOLS_CSV = Path(__file__).with_name("hust-schools-2026.csv")
REQUIRED_COLUMNS = {
    "major_code",
    "major_name",
    "faculty_code",
    "faculty_name",
    "program_type",
    "is_new_2026",
}


def faculty_code_from_name(name: str) -> str:
    normalized = name.replace("Đ", "D").replace("đ", "d")
    ascii_name = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", ascii_name).strip("-").lower()


def load_programs() -> list[dict[str, str]]:
    with PROGRAMS_CSV.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError("Program CSV is missing required columns")
        rows = list(reader)

    if any(
        not row.get(column, "").strip()
        for row in rows
        for column in REQUIRED_COLUMNS
    ):
        raise ValueError("Program CSV contains an empty required value")

    codes = [row["major_code"] for row in rows]
    faculties = {
        row["faculty_code"]: row["faculty_name"]
        for row in rows
    }
    if len(rows) != 68 or len(set(codes)) != 68 or len(faculties) != 10:
        raise ValueError("Expected 68 unique programs across 10 schools")

    if len({row["faculty_name"] for row in rows}) != len(faculties):
        raise ValueError("Each faculty code must map to one unique school name")
    if any(
        faculty_code_from_name(name) != code
        for code, name in faculties.items()
    ):
        raise ValueError("School names do not map to unique internal faculty codes")

    return rows


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)


def main() -> None:
    programs = load_programs()
    schools = list(
        dict.fromkeys(
            (row["faculty_code"], row["faculty_name"]) for row in programs
        )
    )
    write_csv(
        SCHOOLS_CSV,
        ["faculty_code", "faculty_name"],
        [list(school) for school in schools],
    )
    print(f"Validated {len(programs)} programs; generated {len(schools)} schools.")


if __name__ == "__main__":
    main()
