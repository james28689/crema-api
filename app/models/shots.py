"""
Pydantic models for the /v1/shots endpoints.

ShotCreate    — request body for POST /v1/shots.
                Required: bean_id (UUID), dose_g (positive), yield_g (positive),
                time_sec (positive int).
                Optional: grinder_setting, rating (1–10), taste_tags (list[str]),
                notes, pulled_at (datetime, defaults to now()).

BeanSummary   — nested bean name included in ShotResponse (null-safe for deleted beans).

ShotResponse  — response shape for all shot endpoints.
                Includes computed read-only fields: ratio (float), days_off_roast_at_pull
                (int | None), bean (BeanSummary | None), pulled_at, created_at.

ShotListResponse — wraps a list of ShotResponse with next_cursor (UUID | None) for
                   cursor-based pagination.
"""
