# Deployment notes
Local: backend with Uvicorn and frontend with Next dev server. Docker Compose provides PostgreSQL, backend container and frontend dev container.
Production baseline (future): frontend on Vercel or container platform; FastAPI on Render/Fly.io/AWS ECS; managed PostgreSQL (Neon, Supabase, RDS). Configure CORS to exact origins and use HTTPS.
Set DATABASE_URL, CORS_ORIGINS, NEXT_PUBLIC_API_URL and database credentials through platform secrets. Apply schema migrations (Alembic is planned; currently SQLAlchemy create_all is used at startup). CI should run backend pytest and frontend npm build. Add structured logs, metrics, uptime checks, error reporting and DB backups. Do not use the compose fallback password in production.
