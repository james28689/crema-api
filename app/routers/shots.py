"""
Router for /v1/shots — espresso shot logging.

Routes (all require JWT via get_current_user dependency):
  GET    /v1/shots           Paginated shot history. Supports ?bean_id, ?limit
                             (default 20, max 100), and ?cursor (UUID of last item).
                             Computes ratio and days_off_roast_at_pull in SQL.
                             LEFT JOINs bean name (null-safe — bean may be deleted).
  POST   /v1/shots           Log a new shot. Validates bean_id belongs to authed user.
                             Returns 201 with full shot object including computed ratio
                             and joined bean name.
  GET    /v1/shots/{id}      Fetch a single shot with full detail. Returns 404 if not
                             found or not owned by the authed user.
  DELETE /v1/shots/{id}      Hard-delete a shot. Returns 204 No Content.
"""
