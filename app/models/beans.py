"""
Pydantic models for the /v1/beans endpoints.

BeanCreate   — request body for POST /v1/beans.
               Required: name (non-empty str).
               Optional: roaster, origin, process (washed|natural|honey),
               roast_level (light|medium|dark), roast_date (date).

BeanUpdate   — request body for PATCH /v1/beans/{id}.
               All fields optional (partial update). Same field constraints as
               BeanCreate where applicable, plus is_active (bool).

BeanResponse — response shape for all bean endpoints.
               Includes computed read-only fields: days_off_roast (int | None),
               shot_count (int), created_at (datetime).
"""
