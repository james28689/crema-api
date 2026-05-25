"""
Application settings loaded from environment variables via pydantic-settings.

Fields:
- SUPABASE_URL: Base URL of the Supabase project
- SUPABASE_JWT_SECRET: Secret used to verify HS256 JWTs issued by Supabase Auth
- DATABASE_URL: asyncpg-compatible PostgreSQL DSN
  (e.g. postgresql://user:pass@host:5432/dbname)

A single `get_settings()` cached function is provided for use as a FastAPI
dependency, ensuring the environment is only parsed once.
"""
