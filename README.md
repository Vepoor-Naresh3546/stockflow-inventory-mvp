# stockflow-inventory-mvp

## Deploying on Render

Create a Render Web Service and attach a PostgreSQL database. Set the `SECRET_KEY`
environment variable to a newly generated secret; Render supplies `DATABASE_URL`
and `RENDER_EXTERNAL_HOSTNAME`. Do not use the local development secret in
production.

- **Build command:** `bash build.sh`
- **Start command:** `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

The build script installs `requirements.txt`, collects static files, and applies
database migrations. Locally, the project uses SQLite when `DATABASE_URL` is not
set.