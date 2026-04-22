# Kanji Learn

Human-readable JLPT study kanji data for levels N5 through N2.

## Data Layout

The Stage 1 database is stored as Markdown tables:

- `kanji/N5/N5.md`
- `kanji/N4/N4.md`
- `kanji/N3/N3.md`
- `kanji/N2/N2.md`

Each table uses this schema:

| # | Kanji | Level | Meanings | On'yomi | Kun'yomi | Examples | Notes |
|---:|:---:|:---:|---|---|---|---|---|

Current row counts:

- N5: 80
- N4: 167
- N3: 370
- N2: 374

JLPT kanji lists are unofficial after the 2010 JLPT change. Level placement here is practical study guidance based on public study lists, not an official exam specification.

## Scripts

Validate the Markdown database:

```sh
python3 scripts/validate_kanji_markdown.py
```

Convert the Markdown database to JSON:

```sh
python3 scripts/convert_kanji_markdown_to_json.py --check
```

By default, conversion writes:

```text
kanji/kanji.json
```

Write JSON somewhere else:

```sh
python3 scripts/convert_kanji_markdown_to_json.py --check --output /tmp/kanji-stage1.json
```

## Generated JSON Shape

The converter emits one object with project metadata and entries grouped by JLPT level:

```json
{
  "metadata": {
    "counts": {
      "N5": 80,
      "N4": 167,
      "N3": 370,
      "N2": 374
    }
  },
  "levels": {
    "N5": [
      {
        "number": 1,
        "kanji": "日",
        "level": "N5",
        "meanings": ["day", "sun", "Japan", "counter for days"],
        "readings": {
          "on": ["ニチ", "ジツ"],
          "kun": ["ひ", "-び", "-か"]
        },
        "examples": [
          {
            "word": "一日",
            "reading": "いちにち",
            "meaning": "one day"
          }
        ],
        "notes": "EDRDG data; level agrees in JLPT Sensei and KanjiQuest."
      }
    ]
  }
}
```

## Attribution

Readings, English meanings, and vocabulary examples are derived from EDRDG KANJIDIC2/JMdict data. See `ATTRIBUTION.md` for source, license, and downstream attribution notes.

