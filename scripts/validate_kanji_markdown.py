#!/usr/bin/env python3
"""Validate the Stage 1 kanji Markdown database."""

from __future__ import annotations

import argparse
from pathlib import Path


EXPECTED_COLUMNS = [
    "#",
    "Kanji",
    "Level",
    "Meanings",
    "Radicals",
    "On'yomi",
    "Kun'yomi",
    "Examples",
    "Notes",
]
EXPECTED_COUNTS = {
    "N5": 80,
    "N4": 167,
    "N3": 370,
    "N2": 374,
}


def is_kanji(character: str) -> bool:
    return ("\u4e00" <= character <= "\u9fff") or ("\u3400" <= character <= "\u4dbf")


def parse_markdown_table(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = f"| {' | '.join(EXPECTED_COLUMNS)} |"

    if header not in lines:
        raise ValueError(f"{path}: missing exact table header: {header}")

    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(lines, 1):
        if not line.startswith("| "):
            continue
        if line.startswith("| #") or line.startswith("|---"):
            continue

        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(EXPECTED_COLUMNS):
            raise ValueError(
                f"{path}:{line_number}: expected {len(EXPECTED_COLUMNS)} columns, got {len(cells)}"
            )

        row = dict(zip(EXPECTED_COLUMNS, cells))
        row["_line"] = str(line_number)
        rows.append(row)

    return rows


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    seen_kanji: dict[str, str] = {}

    for level, expected_count in EXPECTED_COUNTS.items():
        path = root / "kanji" / level / f"{level}.md"
        if not path.exists():
            errors.append(f"{path}: file does not exist")
            continue

        try:
            rows = parse_markdown_table(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if len(rows) != expected_count:
            errors.append(f"{path}: expected {expected_count} rows, got {len(rows)}")

        for index, row in enumerate(rows, 1):
            location = f"{path}:{row['_line']}"
            kanji = row["Kanji"]

            if row["#"] != str(index):
                errors.append(f"{location}: expected row number {index}, got {row['#']!r}")
            if len(kanji) != 1 or not is_kanji(kanji):
                errors.append(f"{location}: Kanji must be exactly one kanji character, got {kanji!r}")
            if kanji in seen_kanji:
                errors.append(f"{location}: duplicate kanji also found at {seen_kanji[kanji]}")
            seen_kanji[kanji] = location
            if row["Level"] != level:
                errors.append(f"{location}: expected Level {level}, got {row['Level']!r}")
            if not row["Meanings"]:
                errors.append(f"{location}: Meanings is empty")
            if not row["Radicals"]:
                errors.append(f"{location}: Radicals is empty")
            elif any(not radical.strip() for radical in row["Radicals"].split(",")):
                errors.append(f"{location}: Radicals contains an empty entry")
            if not row["On'yomi"] and not row["Kun'yomi"]:
                errors.append(f"{location}: both On'yomi and Kun'yomi are empty")
            if not row["Examples"]:
                errors.append(f"{location}: Examples is empty")
            if not row["Notes"]:
                errors.append(f"{location}: Notes is empty")

    expected_total = sum(EXPECTED_COUNTS.values())
    if len(seen_kanji) != expected_total:
        errors.append(f"expected {expected_total} unique kanji, got {len(seen_kanji)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root. Defaults to the parent of scripts/.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    errors = validate(root)
    if errors:
        print("Kanji Markdown validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Kanji Markdown validation passed.")
    for level, count in EXPECTED_COUNTS.items():
        print(f"- {level}: {count} rows")
    print(f"- Total unique kanji: {sum(EXPECTED_COUNTS.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
