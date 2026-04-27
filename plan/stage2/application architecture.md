# Stage 2. Application Architecture

## Scope

**In scope for stage 2:**
- FastAPI backend serving the kanji study API.
- Flutter client targeting web and mobile (iOS + Android) from a single codebase.
- Postgres for user-owned state (reviews, mnemonics, settings).
- Stage-1 kanji data (`kanji/kanji.json`) loaded read-only from disk, not stored in Postgres.
- FSRS-based spaced repetition for meaning and reading cards.
- Single-user deployment via Docker Compose.

**Deferred:**
- Image generation for mnemonics → stage 4.
- Multi-user / public hosting, quotas, OAuth providers, email verification, password reset.
- Shared community mnemonic library.
- Offline-first mobile with local DB sync (mobile will require network to the backend).

**Out of scope entirely:**
- Kanji content editing through the app. Content lives in git; edits go through the stage-1 Markdown workflow.

## Architecture Overview

```
            ┌──────────────────┐        ┌──────────────────┐
            │  Flutter (web)   │        │ Flutter (mobile) │
            └────────┬─────────┘        └────────┬─────────┘
                     │   HTTPS + JSON            │
                     └────────────┬──────────────┘
                                  ▼
                     ┌────────────────────────────┐
                     │       FastAPI app          │
                     │  ┌──────────────────────┐  │
                     │  │ auth · reviews ·     │  │
                     │  │ mnemonics · progress │  │
                     │  │ kanji (read-only)    │  │
                     │  └──────────┬───────────┘  │
                     │             │              │
                     │  ┌──────────▼───────────┐  │
                     │  │ FSRS scheduler       │  │
                     │  └──────────────────────┘  │
                     └──────┬───────────────┬─────┘
                            │               │
                            ▼               ▼
                    ┌──────────────┐  ┌──────────────┐
                    │  Postgres    │  │ kanji.json   │
                    │ (user data)  │  │ (in-memory)  │
                    └──────────────┘  └──────────────┘
```

- Kanji reference data is loaded once at backend boot into an in-memory index keyed by character. No `kanji` table in Postgres.
- Postgres stores only user-owned data. This keeps content updates to a `git pull + restart` with zero migration cost.
- Flutter is the single client codebase. The web build is served as static assets by a reverse proxy (nginx); mobile builds are packaged native apps.

## Technology Choices

| Concern | Choice | Rationale |
|---|---|---|
| Backend | Python 3.12 + FastAPI + uvicorn | Matches existing stage-1 Python tooling. Strong async + OpenAPI story. |
| ORM | SQLAlchemy 2.x (async) + Alembic | Boring, production-proven, plays well with FastAPI. |
| DB | Postgres 16 | User state only; small volume. |
| Frontend | Flutter (stable channel) | Single codebase for web + iOS + Android. |
| API client | Generated Dart client from FastAPI OpenAPI spec | Keeps client/server types in lock-step. |
| SRS algorithm | [FSRS](https://github.com/open-spaced-repetition) via `py-fsrs` | Better retention curves than SM-2; open parameter model; easy to swap. |
| Auth | Password + JWT in httpOnly cookie (web) / secure storage (mobile) | Minimal surface for single-user; no external IdP needed. |
| Packaging | Docker Compose | Matches stated deployment. One `compose.yaml` + `compose.prod.yaml` override. |

## Repository Layout (after stage 2)

```
kanji-learn/
├── kanji/                 # stage 1 data (unchanged)
├── scripts/               # stage 1 scripts (unchanged)
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # pydantic-settings
│   │   ├── kanji_index.py       # loads kanji.json at startup
│   │   ├── db.py                # async engine + session
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # pydantic request/response
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── kanji.py
│   │   │   ├── reviews.py
│   │   │   ├── mnemonics.py
│   │   │   └── progress.py
│   │   ├── services/
│   │   │   ├── scheduler.py     # FSRS wrapper
│   │   │   └── progress.py      # aggregation queries
│   │   └── security.py
│   ├── alembic/
│   └── tests/
├── frontend/
│   ├── pubspec.yaml
│   ├── lib/
│   │   ├── main.dart
│   │   ├── api/                 # generated client + auth interceptor
│   │   ├── models/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── study/           # review queue, card UI
│   │   │   ├── browse/          # kanji explorer by level
│   │   │   ├── mnemonics/
│   │   │   └── progress/
│   │   └── widgets/
│   └── test/
├── deploy/
│   ├── compose.yaml
│   ├── compose.prod.yaml
│   └── nginx/
└── plan/
```

## Data Architecture

### Kanji reference data (read-only, in-memory)

At backend startup, `kanji_index.py` loads `kanji/kanji.json` into a dict keyed by the kanji character. Each entry is the stage-1 JSON record (meanings, readings, radicals, examples, notes, level).

Endpoints never mutate this index. A `/kanji/version` endpoint returns a hash of the file so clients can invalidate cached lists when the content changes.

### User state (Postgres)

All user state is scoped by `user_id`. Single-user deployments will have exactly one row in `users`, but the schema is multi-user-shaped so the constraint can be relaxed later without migration.

## Database Schema

```sql
-- Users ------------------------------------------------------------
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-user settings ------------------------------------------------
CREATE TABLE user_settings (
    user_id             BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    active_levels       TEXT[] NOT NULL DEFAULT ARRAY['N5'],   -- subset of {N5,N4,N3,N2}
    daily_new_limit     INT    NOT NULL DEFAULT 10,            -- 5–15 from vision.md
    daily_review_limit  INT    NOT NULL DEFAULT 200,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Private mnemonics ------------------------------------------------
CREATE TABLE mnemonics (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kanji           TEXT   NOT NULL,                -- the character itself
    body            TEXT   NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, kanji)
);

-- SRS state: one row per (user, kanji, card_type) -----------------
-- card_type drives which face of the kanji is being trained.
-- 'meaning'  → prompt kanji, answer English meaning
-- 'reading'  → prompt kanji, answer reading (on or kun)
CREATE TYPE card_type AS ENUM ('meaning', 'reading');
CREATE TYPE card_state AS ENUM ('new', 'learning', 'review', 'relearning');

CREATE TABLE review_cards (
    user_id         BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kanji           TEXT        NOT NULL,
    card_type       card_type   NOT NULL,
    level           TEXT        NOT NULL,   -- denormalized from kanji.json for SQL-side progress queries

    -- FSRS state (mirrors py-fsrs Card fields)
    state           card_state  NOT NULL DEFAULT 'new',
    due             TIMESTAMPTZ NOT NULL DEFAULT now(),
    stability       DOUBLE PRECISION NOT NULL DEFAULT 0,
    difficulty      DOUBLE PRECISION NOT NULL DEFAULT 0,
    elapsed_days    INT         NOT NULL DEFAULT 0,
    scheduled_days  INT         NOT NULL DEFAULT 0,
    reps            INT         NOT NULL DEFAULT 0,
    lapses          INT         NOT NULL DEFAULT 0,
    last_review     TIMESTAMPTZ,

    introduced_at   TIMESTAMPTZ,    -- set when card leaves 'new'
    PRIMARY KEY (user_id, kanji, card_type)
);

CREATE INDEX review_cards_due_idx
    ON review_cards (user_id, due)
    WHERE state <> 'new';

-- Review history: one row per answer ------------------------------
CREATE TYPE review_rating AS ENUM ('again', 'hard', 'good', 'easy');

CREATE TABLE review_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kanji           TEXT        NOT NULL,
    card_type       card_type   NOT NULL,
    level           TEXT        NOT NULL,   -- denormalized for time-series-by-level queries

    rating          review_rating NOT NULL,
    correct         BOOLEAN     NOT NULL,   -- rating != 'again'; precomputed for retention queries
    -- Raw answer for typed/MCQ audit + grading-rule tuning. NULL for timed fast-taps where UI sends only rating.
    user_answer     TEXT,

    -- State snapshot BEFORE this review, for FSRS re-optimization
    state_before    card_state  NOT NULL,
    stability_before   DOUBLE PRECISION NOT NULL,
    difficulty_before  DOUBLE PRECISION NOT NULL,
    elapsed_days    INT         NOT NULL,
    scheduled_days  INT         NOT NULL,
    -- For "speed round" / automaticity analysis (vision.md)
    answered_in_ms  INT,
    -- Presentation mode the card was shown in
    presentation    TEXT        NOT NULL,  -- 'multiple_choice' | 'typed' | 'timed'

    reviewed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX review_log_user_time_idx
    ON review_log (user_id, reviewed_at DESC);
```

### Schema notes

- **Kanji identity.** `kanji` is stored as its Unicode string and used directly as a reference. The character is stable, unique, and short; an integer surrogate key adds a join without value.
- **Card types.** Only `meaning` and `reading` are persisted SRS states. The three test *formats* from `vision.md` — MCQ, typed recall, timed speed — are presentation modes recorded on `review_log.presentation`, not separate scheduler streams. Format can be picked by the client based on card maturity (MCQ while learning, typed once reviewing).
- **Radicals.** Not a separate review target in stage 2; they're shown as scaffolding on kanji cards, pulled from `kanji.json`.
- **review_log retention.** Keep all rows — FSRS parameter optimization needs the full history. Volume is trivial (thousands of rows per year per user).

## API Surface

All endpoints under `/api/v1`. Auth-required endpoints marked with 🔒.

```
POST  /auth/login           → issue JWT cookie
POST  /auth/logout          → clear cookie
GET   /auth/me          🔒  → current user info

GET   /kanji                → list metadata (counts, version hash)
GET   /kanji/{level}        → kanji for a JLPT level
GET   /kanji/char/{kanji}   → full record for one kanji

GET   /reviews/queue    🔒  → next N cards due (new + review, merged per FSRS + user limits)
POST  /reviews/answer   🔒  → submit rating; returns updated card + next due
GET   /reviews/stats    🔒  → due today, learned, retention rate

GET   /mnemonics/{kanji}      🔒  → get user's mnemonic for a kanji
PUT   /mnemonics/{kanji}      🔒  → create/replace
DELETE /mnemonics/{kanji}     🔒

GET   /progress             🔒  → per-level mastery tier counts (see Progress Model)
GET   /progress/history     🔒  → pace: bucketed time-series
GET   /progress/forecast    🔒  → forecast: upcoming daily review load
GET   /progress/automaticity 🔒 → cards known but slow
GET   /settings             🔒
PUT   /settings             🔒
```

Single-user deployment: **no `/auth/register` endpoint**. The initial account is created by a one-shot CLI command (`python -m app.cli create_user ...`) run once on install.

## Review Scheduler Flow

1. Client calls `GET /reviews/queue`.
2. Backend fetches due cards (`state<>'new' AND due <= now()`) up to `daily_review_limit`. Reviews are served first (vision requirement).
3. If capacity remains, promote up to `daily_new_limit` new cards for the user's `active_levels`, ordered by JLPT level ascending then kanji index. Promotion flips `state` to `'learning'` and sets `introduced_at`.
4. Client shows a card, records `answered_in_ms`, posts `POST /reviews/answer` with `{kanji, card_type, rating, presentation}`.
5. Backend:
   - Appends a row to `review_log` with the pre-review snapshot.
   - Runs `py-fsrs` to compute new state.
   - Updates the `review_cards` row.
   - Returns the new state so the client can update its local queue.

## Test Logic & Grading

Three presentation modes map onto two scheduler card types (`meaning`, `reading`). The scheduler only cares about the final `rating`; presentation mode drives *how* the rating is produced.

### 1. Recognition (multiple choice)

**When shown:** Default for `new` and `learning` cards, and for the first few `review` repetitions — low friction keeps the introduction phase moving.

**Question payload** (`GET /reviews/queue` returns one of these per card):
```json
{
  "kanji": "日",
  "card_type": "meaning",
  "presentation": "multiple_choice",
  "prompt": "日",
  "choices": ["day / sun", "moon", "fire", "bright"],
  "correct_index": 0
}
```
The client self-grades (knows `correct_index`), so the answer round-trip is just `{rating, answered_in_ms}`. Distractors are chosen server-side and included verbatim in `review_log.user_answer` (as the chosen string, for audit).

**Rating mapping:**
- correct → `good`
- incorrect → `again`
- No `hard` or `easy` — MCQ doesn't give enough signal.

**Distractor selection** (`services/distractors.py`):

Build a candidate pool from the in-memory kanji index, then score and pick top 3. Rules differ per `card_type`:

- **Meaning MCQ distractors** — want visually/semantically close *meanings*:
  1. Candidates share ≥1 radical with the prompt kanji (pulls from `radical_symbols`).
  2. Among those, prefer same JLPT level (keeps difficulty calibrated).
  3. Reject candidates whose meaning list overlaps the correct meanings (no ambiguous gotchas).
  4. Fallback if <3 candidates: drop the shared-radical rule, keep same-level.

- **Reading MCQ distractors** — want phonetically close *readings*:
  1. Candidates where any reading shares a ≥2-mora prefix with a correct reading (e.g. ニチ ↔ ニン, ニュウ).
  2. Prefer kanji sharing a phonetic component with the prompt (same-radical heuristic is a decent proxy).
  3. Fallback: random same-level readings filtered by "not equal to any correct reading".

Distractors are computed per request, not stored. Seeded RNG from `(user_id, kanji, reviewed_at_date)` so a card refreshed within a session doesn't change its options (prevents accidental re-roll cheating).

### 2. Recall (typed)

**When shown:** Once a card reaches `review` state with non-trivial stability, or whenever the user opts into typed mode in settings.

**Question payload:**
```json
{
  "kanji": "日",
  "card_type": "reading",
  "presentation": "typed",
  "prompt": "日",
  "accepted_readings_count": 5
}
```
(The backend does not leak accepted answers in the prompt.)

**Answer round-trip:** Client posts `{rating?, user_answer, answered_in_ms}`. Backend grades, overrides rating if client omitted it, returns `{correct, rating, accepted_answers}` so the UI can show a reveal screen.

**Grading — meaning:**
1. Normalize: lowercase, trim, strip leading `to `/`a `/`the `, strip parenthetical notes, collapse internal whitespace.
2. Exact match against any entry in `meanings[]` normalized the same way.
3. If exact match fails, Levenshtein distance ≤ 1 per word → **"close, not counted"** — surfaced in UI as "did you mean…?" so the user can self-override to `good` or confirm `again`. Distance-1 typos are not auto-accepted (too risky with short English words).

**Grading — reading:**
1. Normalize user input: convert romaji to hiragana via a standard table (`tsu` → つ, `shi` → し, long vowels `aa/ii/uu/ee/oo/ou` → ー etc.); normalize katakana ↔ hiragana for comparison; strip `ー` vs doubled-vowel variants; ignore leading/trailing hyphens used to mark okurigana slots in the dataset (`-び`, `-か`).
2. Accept if normalized user input equals any normalized `readings.on` **or** `readings.kun` entry (either reading type satisfies — see open-question default below).
3. No fuzzy matching on readings — kana is unambiguous, and near-matches are real mistakes.

**Rating mapping** (for typed):
- incorrect → `again`
- correct, `answered_in_ms` > 8000 → `hard`
- correct, normal → `good`
- correct + explicit user-tapped "easy" button → `easy`

### 3. Timed Speed Round

**When shown:** Separate launched session (not auto-scheduled). User picks a level and a card count; only cards with `state='review' AND stability >= 14` are eligible — speed testing brand-new cards just measures typing speed, not recall.

**Flow:** Cards flash with a hard 4-second ceiling. The UI is MCQ-style (2 choices, not 4 — fewer to read in the time budget). No `hard`/`easy` buttons.

**Rating mapping:**
- incorrect or timed out → `again`
- correct, `answered_in_ms` ≥ 2500 → `hard` (hesitation penalty — see `vision.md`: "a kanji you hesitate on but answer correctly is actually weaker than SRS signals suggest")
- correct, `answered_in_ms` < 2500 → `good`

The hesitation penalty is the whole point of this mode. It feeds FSRS a weaker signal on cards that look mature but aren't automatic yet, pulling their scheduled intervals back.

### Grading rule location

All grading lives in `services/grading.py` on the backend — single source of truth, unit-testable, identical across web/mobile clients. Client-side only handles MCQ self-grading (pure `correct_index` comparison, no rules to drift).

## Progress Model

Progress has three distinct dimensions the UI should expose separately — they answer different questions.

### Dimension 1: Mastery (state of knowledge, right now)

Each (`kanji`, `card_type`) pair sits in one of five tiers, derived from `review_cards.state` and `stability`:

| Tier | Definition |
|---|---|
| **Unknown** | no row in `review_cards`, or `state='new'` |
| **Learning** | `state IN ('learning','relearning')` |
| **Familiar** | `state='review' AND stability < 30` |
| **Proficient** | `state='review' AND stability >= 30 AND stability < 90` |
| **Mastered** | `state='review' AND stability >= 90` |

A kanji's overall tier = `min(meaning_tier, reading_tier)` — weakest face wins. This matters because a kanji you can read but can't translate isn't actually learned.

`GET /progress` returns per-level counts in each tier:

```json
{
  "levels": {
    "N5": {"total": 80, "unknown": 12, "learning": 10, "familiar": 35, "proficient": 18, "mastered": 5},
    "N4": {...},
    "N3": {...},
    "N2": {...}
  }
}
```

The UI renders this as a stacked bar per level — the "how much of N3 have I actually learned" glance that `vision.md` asks for.

### Dimension 2: Pace (are we moving)

`GET /progress/history?from=…&to=…&bucket=day|week`:

```json
{
  "buckets": [
    {"date": "2026-04-22", "reviews": 142, "correct": 118, "retention": 0.83, "new_introduced": 8, "cumulative_mastered": 94}
  ]
}
```

Source queries:
- `reviews`, `correct`, `retention` — aggregates from `review_log` grouped by bucket.
- `new_introduced` — count of `review_cards.introduced_at` in the bucket.
- `cumulative_mastered` — running count of cards that reached `stability >= 90` on or before the bucket end (computable by scanning `review_log` for the first log row per card with post-review stability crossing 90; cacheable if it gets slow).

UI uses this to render:
- Reviews/day bar chart with a target line (`daily_review_limit` or user-set goal).
- Retention % line chart — if it drops under ~85%, FSRS says you're being too ambitious and the user should lower `daily_new_limit`.
- "Current streak" and "longest streak" computed trivially from consecutive non-zero bucket days.

### Dimension 3: Forecast (what's coming)

`GET /progress/forecast?days=14`:

```json
{
  "by_day": [
    {"date": "2026-04-24", "due_reviews": 87, "projected_new": 10}
  ]
}
```

- `due_reviews`: `SELECT date_trunc('day', due), count(*) FROM review_cards WHERE user_id=? AND state<>'new' AND due < now()+interval '14 days' GROUP BY 1`.
- `projected_new`: just `daily_new_limit` capped by unknown cards remaining in `active_levels`.

This is what lets the user "check the learning pace himself" — they see "tomorrow = 140 reviews, next Tuesday = 200" and can adjust `daily_new_limit` before a backlog builds.

### Dimension 4 (per-card): Automaticity

Shown in a card-detail view, not on the dashboard. For a given (kanji, card_type):

- **Median correct response time** over the last N=10 correct log rows.
- **Automaticity flag**: `true` if median < 2500ms AND recent retention ≥ 90%. Otherwise "knows it, but not automatic."

This exposes the gap `vision.md` calls out — cards the SRS *thinks* are mature because of consecutive correct answers, but where the user is still reasoning their way to the answer. The UI can surface a list of "known but slow" kanji as a suggested speed-round deck.

### Progress endpoints summary

Replaces the earlier `/progress` sketch with the three-dimension split:

```
GET /progress                🔒  → Mastery (per-level tier counts)
GET /progress/history        🔒  → Pace (bucketed time-series)
GET /progress/forecast       🔒  → Forecast (upcoming load)
GET /progress/automaticity   🔒  → Cards marked "known but slow"
```

## Authentication

- Password hashing: `argon2-cffi`.
- JWT: HS256, 30-day expiry, refreshed on use.
- Web: httpOnly, Secure, SameSite=Lax cookie. CSRF mitigated by SameSite + same-origin reverse proxy.
- Mobile: JWT stored in `flutter_secure_storage`; sent as `Authorization: Bearer ...`.
- Single-user stance: no rate limits on `/auth/login` needed for personal deployment, but add a 5-attempts-per-minute limiter anyway — the cost is negligible and it prevents a misconfigured public exposure from being trivially brute-forced.

## Deployment

`deploy/compose.yaml` (dev):

```
services:
  db:      postgres:16-alpine    # named volume
  api:     build ../backend; depends_on db; mounts ../kanji read-only
  web:     build ../frontend --target web; serves Flutter web build via nginx
```

`deploy/compose.prod.yaml` overrides:
- nginx in front of `api` + `web` on one public port, terminates TLS (Let's Encrypt via certbot sidecar or Caddy — pick one, don't handroll).
- `api` and `db` not exposed to host.
- Env vars from `.env` file, not committed.

Mobile clients connect to the same public hostname as the web build. API base URL is compile-time configurable (`--dart-define=API_BASE_URL=...`).

## Stage 2 Work Breakdown

Suggested order — each step independently shippable behind a login wall:

1. **Backend skeleton.** FastAPI app, config, health endpoint, Postgres wired up, Alembic baseline.
2. **Auth.** `users`, `user_settings`, `/auth/*`, CLI `create_user` command.
3. **Kanji read API.** In-memory index loader, `/kanji/*` endpoints, version hash.
4. **SRS core.** `review_cards`, `review_log`, `py-fsrs` integration, `/reviews/*` endpoints. Unit tests with a frozen clock.
5. **Mnemonics + settings.** CRUD endpoints.
6. **Progress queries.** Aggregation endpoints for dashboards.
7. **Flutter skeleton.** App shell, auth flow, generated API client wired in.
8. **Flutter study flow.** Review queue UI, MCQ + typed + timed presentations.
9. **Flutter browse + progress.** Kanji explorer by level, progress dashboard.
10. **Flutter mnemonics.** Per-kanji mnemonic editor.
11. **Deployment.** Dev compose, prod compose + TLS, build-and-release scripts for mobile.

## Open Questions to Resolve During Stage 2

- **Reading prompt specificity.** Default: any reading (on *or* kun) satisfies the prompt. Alternative: tag the prompt with which reading class is expected — harder but closer to real JLPT behavior. Start permissive, tighten if retention is suspiciously high.
- **"Introduce radicals before the kanji that uses them."** Stage 1 has radical data per kanji but no standalone radical entries. Do radicals get their own preview step before a kanji is introduced, or just inline on the card? Default: inline, revisit if retention is poor.
- **FSRS parameter optimization.** Ship with default weights; add an admin endpoint later to re-optimize from `review_log` once there's enough history (FSRS recommends ~1000 reviews minimum).
- **Typo leniency on meaning recall.** Default above is "distance-1 is flagged, not auto-accepted." If this proves too strict in practice, switch to auto-accept for distance-1 on words longer than 4 characters.
- **Distractor pool sizing.** If the shared-radical-plus-same-level rule yields fewer than 3 candidates for rare kanji, we fall back to same-level-only. Verify pool sizes empirically once the distractor service is built.
