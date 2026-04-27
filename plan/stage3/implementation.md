# Stage 3. Milestone Checklist

## Delivery Order

- [ ] Deliver the web-first MVP before mobile packaging work.
- [ ] Treat the stage-2 architecture as fixed for stage 3:
  - [ ] FastAPI backend
  - [ ] Postgres for user state
  - [ ] Flutter client
  - [ ] FSRS scheduling
  - [ ] Read-only `kanji/kanji.json` loaded in memory
  - [ ] Docker Compose deployment

## Fixed Contracts

- [ ] Keep backend routes under `/api/v1`.
- [ ] Ship these route groups:
  - [ ] `auth`
  - [ ] `kanji`
  - [ ] `reviews`
  - [ ] `mnemonics`
  - [ ] `progress`
  - [ ] `settings`
- [ ] Limit persistent user state to:
  - [ ] `users`
  - [ ] `user_settings`
  - [ ] `mnemonics`
  - [ ] `review_cards`
  - [ ] `review_log`
- [ ] Keep database enums fixed:
  - [ ] `card_type`
  - [ ] `card_state`
  - [ ] `review_rating`
- [ ] Support review presentation variants in queue payloads:
  - [ ] `multiple_choice`
  - [ ] `typed`
  - [ ] `timed`
- [ ] Keep grading logic server-side.
- [ ] Use the generated OpenAPI Dart client in Flutter.
- [ ] Keep authentication model fixed:
  - [ ] first user created by CLI
  - [ ] JWT session
  - [ ] httpOnly cookie for web
  - [ ] bearer token from secure storage for mobile

## Milestone 1. Backend Foundation

### Scope

- [ ] Create the FastAPI project skeleton.
- [ ] Add config loading with explicit environment handling.
- [ ] Add async DB session management.
- [ ] Add health and readiness endpoints.
- [ ] Add Alembic setup.
- [ ] Wire startup and shutdown lifecycle hooks.
- [ ] Implement kanji index loading:
  - [ ] read `kanji/kanji.json` once at boot
  - [ ] build lookup structures by character
  - [ ] build lookup structures by level
  - [ ] compute version-hash value for the API
- [ ] Define local development conventions:
  - [ ] environment variables
  - [ ] database URL shape
  - [ ] test settings
  - [ ] shared error-response format

### Exit Criteria

- [ ] Backend boots locally with config validation.
- [ ] Health and readiness endpoints respond correctly.
- [ ] Kanji data loads once and is available from application state.
- [ ] Alembic environment is ready for the first migration.

## Milestone 2. Authentication and Settings

### Scope

- [ ] Implement `users` and `user_settings` schema.
- [ ] Create the initial migration.
- [ ] Add password hashing with Argon2.
- [ ] Add JWT issue, refresh, and clear flow.
- [ ] Add current-user dependency wiring.
- [ ] Add one-shot `create_user` CLI command.
- [ ] Implement:
  - [ ] `POST /auth/login`
  - [ ] `POST /auth/logout`
  - [ ] `GET /auth/me`
  - [ ] `GET /settings`
  - [ ] `PUT /settings`

### Exit Criteria

- [ ] A first user can be created from the CLI.
- [ ] Web session login and logout works through cookies.
- [ ] Authenticated settings reads and writes persist correctly.
- [ ] The rest of the API can assume authenticated access and active-level limits.

## Milestone 3. Read-Only Kanji API

### Scope

- [ ] Implement:
  - [ ] `GET /kanji`
  - [ ] `GET /kanji/{level}`
  - [ ] `GET /kanji/char/{kanji}`
  - [ ] `GET /kanji/version`
- [ ] Return normalized records directly from the in-memory index.
- [ ] Do not mirror kanji content into Postgres.
- [ ] Freeze response shapes for downstream client generation.

### Exit Criteria

- [ ] Kanji list, level, char, and version endpoints are stable.
- [ ] Response models are ready to become generated Dart types.
- [ ] No kanji content persistence exists in Postgres.

## Milestone 4. SRS Domain and Review Persistence

### Scope

- [ ] Implement `review_cards` and `review_log` schema.
- [ ] Add migrations and SQLAlchemy models.
- [ ] Add the FSRS service wrapper.
- [ ] Implement queue assembly rules:
  - [ ] reviews first
  - [ ] then promotion of new cards within `daily_new_limit`
  - [ ] filter by `active_levels`
  - [ ] set `introduced_at` on first promotion
- [ ] Implement:
  - [ ] `GET /reviews/queue`
  - [ ] `POST /reviews/answer`
  - [ ] `GET /reviews/stats`
- [ ] Add a frozen-clock test harness for deterministic due-date behavior.

### Exit Criteria

- [ ] Review queue ordering matches stage-2 rules.
- [ ] Answer submission updates scheduler state and writes review logs.
- [ ] Review stats are available from persisted review state.
- [ ] Scheduler tests are deterministic.

## Milestone 5. Grading and Distractor Services

### Scope

- [ ] Build backend-only grading for meaning recall.
- [ ] Build backend-only grading for reading recall.
- [ ] Implement normalization rules.
- [ ] Implement accepted-answer handling.
- [ ] Implement rating mapping for typed mode.
- [ ] Implement rating mapping for timed mode.
- [ ] Build deterministic multiple-choice distractor generation using:
  - [ ] level heuristics
  - [ ] radical heuristics
  - [ ] reading-prefix heuristics
- [ ] Seed distractor generation so options stay stable within a day or session.
- [ ] Keep presentation mode separate from scheduler `card_type`.

### Exit Criteria

- [ ] Grading behavior is consistent across request types.
- [ ] Meaning and reading grading stay server-owned.
- [ ] Multiple-choice options are plausible and deterministic.
- [ ] Only `meaning` and `reading` drive FSRS state.

## Milestone 6. Mnemonics and Progress Analytics

### Scope

- [ ] Implement mnemonic CRUD keyed by `(user, kanji)`.
- [ ] Implement:
  - [ ] `GET /progress`
  - [ ] `GET /progress/history`
  - [ ] `GET /progress/forecast`
  - [ ] `GET /progress/automaticity`
- [ ] Use SQL aggregation over persisted user state.
- [ ] Use denormalized kanji level metadata already stored on review rows.
- [ ] Keep mastery-tier thresholds fixed to the stage-2 definitions.

### Exit Criteria

- [ ] Users can create, update, fetch, and delete mnemonics.
- [ ] Progress endpoints expose separate mastery, pace, forecast, and automaticity views.
- [ ] Frontend can use these outputs without additional interpretation logic.

## Milestone 7. Flutter App Shell and Generated Client

### Scope

- [ ] Initialize the Flutter app structure.
- [ ] Add environment configuration.
- [ ] Add generated API client workflow.
- [ ] Add auth and session state.
- [ ] Add route structure.
- [ ] Add shared app scaffold.
- [ ] Support web-first session bootstrapping:
  - [ ] same-origin cookie auth
  - [ ] guarded routes
  - [ ] bootstrapping from `/auth/me`
  - [ ] clean logged-out flow
  - [ ] clean login flow
- [ ] Keep mobile token-storage support in the architecture.

### Exit Criteria

- [ ] Flutter web app boots against the backend.
- [ ] Protected routes redirect correctly.
- [ ] Session bootstrap works after reload.
- [ ] The generated client is the primary API integration path.

## Milestone 8. Study Flow UI

### Scope

- [ ] Implement review queue screen.
- [ ] Implement card presenter.
- [ ] Implement answer flow.
- [ ] Implement reveal flow.
- [ ] Implement rating flow.
- [ ] Implement session summary.
- [ ] Support all three presentation modes in the UI:
  - [ ] multiple choice
  - [ ] typed
  - [ ] timed
- [ ] Keep grading source of truth on the backend.
- [ ] Add inline mnemonic display and editing inside the study flow.

### Exit Criteria

- [ ] A user can complete a full review session in the web app.
- [ ] All three presentation modes render and submit correctly.
- [ ] Mnemonic editing is available where recall friction happens.

## Milestone 9. Browse, Progress, and Settings UI

### Scope

- [ ] Implement level-based kanji explorer.
- [ ] Implement per-kanji detail view.
- [ ] Implement mnemonic editing outside review flow.
- [ ] Implement progress dashboard.
- [ ] Implement settings controls for:
  - [ ] active levels
  - [ ] daily limits
- [ ] Keep mastery, pace, forecast, and automaticity as separate views or panels.

### Exit Criteria

- [ ] Users can browse kanji by level.
- [ ] Users can inspect a single kanji in detail.
- [ ] Users can manage mnemonics outside study flow.
- [ ] Progress views remain distinct and readable.
- [ ] Settings changes round-trip through the backend.

## Milestone 10. Integration, Deployment, and Mobile Finish

### Scope

- [ ] Add local Docker Compose for DB, API, and web.
- [ ] Add production Compose with reverse proxy and TLS.
- [ ] Use Caddy for production TLS automation.
- [ ] Add smoke checks for:
  - [ ] local stack startup
  - [ ] API availability
  - [ ] DB migration on boot
  - [ ] Flutter web asset serving
- [ ] After the web MVP is stable, finish:
  - [ ] mobile-specific auth storage
  - [ ] API base-URL configuration
  - [ ] iOS packaging
  - [ ] Android packaging

### Exit Criteria

- [ ] Local stack boots from empty volumes.
- [ ] Migrations run successfully on startup.
- [ ] API is reachable through the reverse proxy.
- [ ] Flutter web is served correctly.
- [ ] Production Caddy config validates.
- [ ] Mobile builds can authenticate against the same backend.

## Test Checklist

### Backend Unit Tests

- [ ] Kanji index loading
- [ ] Version hashing
- [ ] Auth and session behavior
- [ ] Grading normalization
- [ ] Distractor selection
- [ ] FSRS transitions
- [ ] Queue ordering

### Backend Integration Tests

- [ ] Migrations
- [ ] Login and logout
- [ ] Settings persistence
- [ ] Review answer logging
- [ ] Mnemonic CRUD
- [ ] Progress endpoint aggregates

### Frontend Widget and Integration Tests

- [ ] Login flow
- [ ] Protected-route bootstrap
- [ ] Queue rendering
- [ ] Multiple-choice answer flow
- [ ] Typed answer flow
- [ ] Timed answer flow
- [ ] Progress dashboard rendering
- [ ] Mnemonic editing

### End-to-End Smoke Flow

- [ ] Create user
- [ ] Log in on web
- [ ] Complete reviews
- [ ] Confirm progress updates
- [ ] Edit mnemonic
- [ ] Restart stack
- [ ] Verify persisted user state
- [ ] Verify kanji content remains unchanged

### Deployment Validation

- [ ] `compose up` from empty volume
- [ ] Alembic migration success
- [ ] API reachable through reverse proxy
- [ ] Flutter web served correctly
- [ ] Caddy config valid

## Assumptions and Defaults

- [ ] `plan/stage3/implementation.md` is the canonical stage-3 implementation document.
- [ ] Web-first delivery remains the priority.
- [ ] Mobile packaging is not a blocker for the first usable release.
- [ ] No public registration flow is added.
- [ ] The first account is created by CLI only.
- [ ] Reading recall accepts either on or kun readings.
- [ ] Radicals stay inline rather than becoming their own learning objects.
- [ ] FSRS ships with default parameters.
- [ ] Meaning typos at edit distance 1 are flagged but not auto-accepted.
- [ ] The backend remains the source of truth for grading, queue composition, and progress calculations.
- [ ] The client stays thin and generated-client driven.
