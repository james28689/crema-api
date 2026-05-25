"""
FastAPI application factory.

Responsibilities:
- Create the FastAPI app instance with base path /v1/
- Register middleware: JWT auth, rate limiting (100 req/min per user), standard
  error envelope handler
- Include routers: beans, shots
- Manage asyncpg pool lifecycle (startup/shutdown events)
"""
