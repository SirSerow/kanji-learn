#!/usr/bin/env python3
"""Convert the Stage 1 kanji Markdown database to JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from .radical_metadata import parse_radicals
    from .validate_kanji_markdown import EXPECTED_COUNTS, parse_markdown_table, validate
except ImportError:
    from radical_metadata import parse_radicals
    from validate_kanji_markdown import EXPECTED_COUNTS, parse_markdown_table, validate


EXAMPLE_PATTERN = re.compile(r"^(?P<word>.+?) \((?P<reading>.+?)\) (?P<meaning>.+)$")


def split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_examples(value: str) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue

        match = EXAMPLE_PATTERN.match(item)
        if match:
            examples.append(match.groupdict())
        else:
            examples.append({"word": item, "reading": "", "meaning": ""})

    return examples


def convert(root: Path) -> dict[str, object]:
    levels: dict[str, list[dict[str, object]]] = {}

    for level in EXPECTED_COUNTS:
        path = root / "kanji" / level / f"{level}.md"
        entries: list[dict[str, object]] = []

        for row in parse_markdown_table(path):
            radicals = parse_radicals(row["Radicals"])
            entries.append(
                {
                    "number": int(row["#"]),
                    "kanji": row["Kanji"],
                    "level": row["Level"],
                    "meanings": split_list(row["Meanings"]),
                    "radicals": radicals,
                    "radical_symbols": [radical["symbol"] for radical in radicals],
                    "readings": {
                        "on": split_list(row["On'yomi"]),
                        "kun": split_list(row["Kun'yomi"]),
                    },
                    "examples": parse_examples(row["Examples"]),
                    "notes": row["Notes"],
                }
            )

        levels[level] = entries

    return {
        "metadata": {
            "description": "JLPT study kanji converted from the Stage 1 Markdown database.",
            "jlpt_notice": (
                "JLPT kanji lists are unofficial after the 2010 JLPT change; "
                "level placement is practical study guidance, not an official exam specification."
            ),
            "source_notice": (
                "Readings, English meanings, vocabulary examples, and radical/component "
                "lists are derived from EDRDG KANJIDIC2/JMdict/KRADFILE data under the "
                "EDRDG license and CC BY-SA 4.0-compatible terms."
            ),
            "counts": {level: len(entries) for level, entries in levels.items()},
        },
        "levels": levels,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root. Defaults to the parent of scripts/.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON output path. Defaults to <root>/kanji/kanji.json.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate Markdown input before converting.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if args.check:
        errors = validate(root)
        if errors:
            print("Input validation failed; JSON was not written:")
            for error in errors:
                print(f"- {error}")
            return 1

    output = args.output if args.output is not None else root / "kanji" / "kanji.json"
    if not output.is_absolute():
        output = root / output

    data = convert(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    total = sum(data["metadata"]["counts"].values())
    print(f"Wrote {total} kanji entries to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
