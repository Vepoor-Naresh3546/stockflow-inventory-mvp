# stockflow-inventory-mvp

## Inventory features

StockFlow provides an organization-scoped inventory dashboard and product
catalog. Each account owns one organization. Product thresholds can be set per
item; when left blank, the organization default is used. Update the organization
name and default threshold from **Settings** after signing in.

Run locally with SQLite when `DATABASE_URL` is unset:

```shell
python manage.py migrate
python manage.py runserver
```

## Deploying on Render

Create a Render Web Service and attach a PostgreSQL database. Set the `SECRET_KEY`
environment variable to a newly generated secret; Render supplies `DATABASE_URL`
and `RENDER_EXTERNAL_HOSTNAME`. Do not use the local development secret in
production. If you use a Render environment group, link it to the service in the
Render dashboard and verify its required variables there.

- **Build command:** `bash build.sh`
- **Start command:** `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

The build script installs `requirements.txt`, collects static files, and applies
database migrations. Locally, the project uses SQLite when `DATABASE_URL` is not
set.