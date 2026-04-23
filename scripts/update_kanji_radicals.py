#!/usr/bin/env python3
"""Populate Markdown kanji tables with KRADFILE radical/component data."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path


LEVELS = ("N5", "N4", "N3", "N2")
OLD_COLUMNS = [
    "#",
    "Kanji",
    "Level",
    "Meanings",
    "On'yomi",
    "Kun'yomi",
    "Examples",
    "Notes",
]
NEW_COLUMNS = [
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
ALIGNMENT = "|---:|:---:|:---:|---|---|---|---|---|---|"
KRAD_NORMALIZATION = {
    "化": "⺅",
    "个": "𠆢",
    "并": "丷",
    "刈": "⺉",
    "込": "⻌",
    "尚": "⺌",
    "忙": "⺖",
    "扎": "⺘",
    "汁": "⺡",
    "犯": "⺨",
    "艾": "⺾",
    "邦": "⻏",
    "阡": "⻖",
    "老": "⺹",
    "杰": "⺣",
    "礼": "⺭",
    "疔": "⽧",
    "禹": "⽱",
    "初": "⻂",
    "買": "⺲",
    "滴": "啇",
    "乞": "𠂉",
}


def normalize_radical(radical: str) -> str:
    return KRAD_NORMALIZATION.get(radical, radical)


def parse_kradfile(path: Path) -> dict[str, list[str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    radicals: dict[str, list[str]] = {}

    with opener(path, "rt", encoding="euc_jp") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or " : " not in line:
                continue

            kanji, components = line.split(" : ", 1)
            radicals[kanji] = [normalize_radical(component) for component in components.split()]

    return radicals


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def format_row(cells: list[str]) -> str:
    return f"| {' | '.join(cells)} |"


def update_file(path: Path, krad: dict[str, list[str]]) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    changed_rows = 0
    output: list[str] = []

    for line in lines:
        if line == format_row(OLD_COLUMNS) or line == format_row(NEW_COLUMNS):
            output.append(format_row(NEW_COLUMNS))
            continue

        if line.startswith("|---"):
            cells = split_row(line)
            if len(cells) in {len(OLD_COLUMNS), len(NEW_COLUMNS)}:
                output.append(ALIGNMENT)
                continue

        if not line.startswith("| ") or line.startswith("| #"):
            output.append(line)
            continue

        cells = split_row(line)
        if len(cells) == len(OLD_COLUMNS):
            row = dict(zip(OLD_COLUMNS, cells))
        elif len(cells) == len(NEW_COLUMNS):
            row = dict(zip(NEW_COLUMNS, cells))
        else:
            output.append(line)
            continue

        kanji = row["Kanji"]
        if kanji not in krad:
            raise KeyError(f"{path}: no KRADFILE entry for {kanji}")

        row["Radicals"] = ", ".join(krad[kanji])
        output.append(format_row([row[column] for column in NEW_COLUMNS]))
        changed_rows += 1

    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    return changed_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kradfile", type=Path, help="Path to kradfile or kradfile.gz.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root. Defaults to the parent of scripts/.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    krad = parse_kradfile(args.kradfile)
    total = 0

    for level in LEVELS:
        path = root / "kanji" / level / f"{level}.md"
        total += update_file(path, krad)

    print(f"Updated radicals for {total} kanji entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
