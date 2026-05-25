"""
Router for /v1/beans — bean / bag management.

Routes (all require JWT via get_current_user dependency):
  GET    /v1/beans           List beans for the authed user, optional ?is_active
                             filter. Computes days_off_roast and shot_count in SQL.
                             Ordered by created_at DESC.
  POST   /v1/beans           Create a new bean. Returns 201 with full bean object.
  GET    /v1/beans/{id}      Fetch a single bean. Returns 404 if not found or not
                             owned by the authed user.
  PATCH  /v1/beans/{id}      Partial update (e.g. archive bag, correct roast_date).
                             Returns 200 with updated bean object.
"""
