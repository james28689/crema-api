# Crema — DB Schema Plan
> Increment 1 reference document. Last updated: 2026-04-28

---

## Stack

- **Database:** PostgreSQL (via Supabase)
- **Auth:** Supabase Auth (Google Sign-in → JWT). Identity is managed entirely by Supabase's built-in `auth.users` table — no custom `users` table.
- **Row-level security:** Supabase RLS — all tables enforce `user_id = auth.uid()`

---

## Tables

> There is no custom `users` table. Supabase Auth owns identity (email, provider, UID) in its internal `auth.users` table. The `user_id` columns in `beans` and `shots` reference `auth.users(id)` directly. A `profiles` table can be added in a later increment if app-specific user data (e.g. display name preferences) is needed.

---

### `beans`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `uuid` | PK, default `gen_random_uuid()` | |
| `user_id` | `uuid` | FK → `auth.users(id)`, ON DELETE CASCADE | Indexed |
| `name` | `text` | not null | Bean / blend name |
| `roaster` | `text` | nullable | |
| `origin` | `text` | nullable | Country or region |
| `process` | `text` | nullable | `'washed'` / `'natural'` / `'honey'` |
| `roast_level` | `text` | nullable | `'light'` / `'medium'` / `'dark'` |
| `roast_date` | `date` | nullable | Used to compute `days_off_roast` |
| `is_active` | `boolean` | default `true` | False = archived bag |
| `created_at` | `timestamptz` | default `now()` | |

**Indexes:** `beans(user_id)`, `beans(user_id, is_active)`

---

### `shots`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `uuid` | PK, default `gen_random_uuid()` | |
| `user_id` | `uuid` | FK → `auth.users(id)` | Indexed |
| `bean_id` | `uuid` | FK → `beans.id`, ON DELETE SET NULL | Indexed — SET NULL so deleting a bean doesn't destroy history |
| `dose_g` | `numeric(5,1)` | not null | e.g. `18.0` |
| `yield_g` | `numeric(5,1)` | not null | e.g. `41.0` |
| `time_sec` | `integer` | not null | Extraction time in seconds |
| `grinder_setting` | `text` | nullable | Freeform: `"3.5"`, `"fine"`, etc. |
| `rating` | `smallint` | CHECK (`rating` BETWEEN 1 AND 10) | 1–10 |
| `taste_tags` | `text[]` | nullable | e.g. `'{sour, bright}'` |
| `notes` | `text` | nullable | Freeform tasting notes |
| `pulled_at` | `timestamptz` | not null, default `now()` | When the shot was pulled |
| `created_at` | `timestamptz` | default `now()` | Row creation time |

**Indexes:** `shots(user_id)`, `shots(bean_id)`, `shots(user_id, pulled_at DESC)`

---

## Computed fields (never stored)

| Field | Derived from | Where computed |
|---|---|---|
| `ratio` | `yield_g / dose_g` | SQL query / API layer |
| `days_off_roast` | `CURRENT_DATE - beans.roast_date` | SQL query / API layer |

**Rule:** Do not add these as columns. They are returned by the API as computed values.

---

## Future tables (not in Increment 1)

| Table | Added in | Purpose |
|---|---|---|
| `profiles` | Increment 2 | App-specific user data (display name, preferences). PK references `auth.users(id)`. Auto-created via trigger on new sign-up. |
| `taste_tags` (lookup) | Increment 2 | Normalise tag vocabulary |
| `bean_attributes` | Increment 5 | Structured columns for similarity matching |

---

## Key schema decisions

1. **No custom `users` table** — Supabase Auth manages identity. `auth.users` is the source of truth for user identity; `user_id` in app tables is the same UUID as `auth.uid()` in the JWT.
2. **`ratio` is computed** — `yield_g / dose_g` at query time. Storing it would create a derived-data consistency problem.
3. **`days_off_roast` is computed** — `now() - beans.roast_date` so it's always accurate, even for historical shots.
4. **`bean_id` uses SET NULL** — archiving or deleting a bean must not destroy shot history.
5. **`taste_tags` as `text[]`** — sufficient for Increment 1. Migrate to a junction table in Increment 2 when the tag vocabulary is normalised.
6. **`pulled_at` separate from `created_at`** — users may log shots retroactively; `pulled_at` is the espresso timestamp, `created_at` is the database row timestamp.
7. **RLS on all tables** — Supabase RLS policy: `USING (user_id = auth.uid())` on SELECT, INSERT, UPDATE, DELETE for both `beans` and `shots`.

---

## Migration (Increment 1 baseline)

```sql
-- Beans
CREATE TABLE beans (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name        text NOT NULL,
  roaster     text,
  origin      text,
  process     text CHECK (process IN ('washed','natural','honey')),
  roast_level text CHECK (roast_level IN ('light','medium','dark')),
  roast_date  date,
  is_active   boolean DEFAULT true,
  created_at  timestamptz DEFAULT now()
);
CREATE INDEX ON beans(user_id);
CREATE INDEX ON beans(user_id, is_active);

-- Shots
CREATE TABLE shots (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id),
  bean_id         uuid REFERENCES beans(id) ON DELETE SET NULL,
  dose_g          numeric(5,1) NOT NULL,
  yield_g         numeric(5,1) NOT NULL,
  time_sec        integer NOT NULL,
  grinder_setting text,
  rating          smallint CHECK (rating BETWEEN 1 AND 10),
  taste_tags      text[],
  notes           text,
  pulled_at       timestamptz NOT NULL DEFAULT now(),
  created_at      timestamptz DEFAULT now()
);
CREATE INDEX ON shots(user_id);
CREATE INDEX ON shots(bean_id);
CREATE INDEX ON shots(user_id, pulled_at DESC);

-- RLS
ALTER TABLE beans ENABLE ROW LEVEL SECURITY;
ALTER TABLE shots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users own their beans" ON beans
  USING (user_id = auth.uid());
CREATE POLICY "users own their shots" ON shots
  USING (user_id = auth.uid());
```

---

## Done state for Increment 1

A shot can be inserted via `POST /v1/shots` and confirmed in the `shots` table with a valid `bean_id` FK, `user_id` matching the authed user (from the Supabase JWT), and `ratio` returned computed from `yield_g / dose_g`.