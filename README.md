# ONS Flask Auth Template

A containerised Flask starter app for Cloud Run prototypes that need an ONS Design System UI and a lightweight password-gated landing page.

This template borrows the useful parts of `ONSdigital/theme-analysis-ui`:

- Flask application factory with `template_folder="app_templates"`
- Jinja configured with `ChainableUndefined` for ONS/Nunjucks-style templates
- downloaded ONS Design System `components/` and `layout/` templates loaded through a Jinja `ChoiceLoader`
- session-based login flow using Werkzeug password hashes
- `scripts/` utilities for fetching ONS templates and provisioning users

It deliberately separates authentication into an `auth` package so the template can be reused across small services.

## What this is suitable for

Use this for low-risk prototypes, internal demos, and short-lived Cloud Run services where a simple password gate is enough.

For production, sensitive, or externally exposed services, prefer organisation-managed authentication such as IAP, SSO, or another centrally managed identity service. This template stores password hashes only, but it is still not a replacement for enterprise identity management.

## Requirements

- Python 3.12
- Poetry 2.1.3
- Docker, if building the container locally
- Google Cloud SDK credentials, if uploading the users file to GCS

## Install locally

```bash
poetry install
```

## Fetch the ONS Design System templates

The ONS Design System uses Nunjucks templates. The ONS guidance for Jinja apps is to use `ChainableUndefined`, and when using the release zip, copy the `components` and `layout` folders into the Flask templates path.

Run:

```bash
poetry run python scripts/fetch_ons_templates.py
```

or:

```bash
make templates
```

The script reads `.design-system-version`. By default it is set to `latest`. To pin a release, replace the file contents with a tag such as:

```text
v72.0.0
```

The downloaded folders are ignored by git:

```text
src/ons_flask_auth_template/templates/components/
src/ons_flask_auth_template/templates/layout/
```

## Provision a local user file

Create a local `users.json` with one or more hashed users:

```bash
poetry run python scripts/provision_users.py \
  --user "user@example.com:change-me" \
  --output users.json
```

You can provide `--user` more than once:

```bash
poetry run python scripts/provision_users.py \
  --user "user1@example.com:password-one" \
  --user "user2@example.com:password-two" \
  --output users.json
```

If you omit `--user`, the script prompts for an email address and password.

The generated file has this shape:

```json
{
  "users": [
    {
      "username": "user@example.com",
      "password_hash": "scrypt:..."  # pragma: allowlist secret
    }
  ]
}
```

## Run locally

Create a `.env` from the example:

```bash
cp .env.example .env
```

For local development, keep:

```text
AUTH_MODE=local
LOCAL_USERS_FILE=users.json
SESSION_COOKIE_SECURE=false
```

**Note:** if running in a **container locally** use the make commands and ensure ```LOCAL_USERS_FILE=/app/users.json```

Then run:

```bash
poetry run flask --app 'ons_flask_auth_template.app:create_app()' run --debug --port 8000
```

Open:

```text
http://localhost:8000
```

You should be redirected to `/login`.

## Use a GCS users file

The app can load `users.json` from GCS when deployed to Cloud Run.

First create and upload the file:

```bash
poetry run python scripts/provision_users.py \
  --user "user@example.com:change-me" \
  --output users.json \
  --bucket "YOUR_AUTH_BUCKET" \
  --blob "users.json"
```

For an encrypted auth file using a customer-managed Cloud KMS key, add:

```bash
  --kms-key-name "projects/PROJECT_ID/locations/LOCATION/keyRings/KEY_RING/cryptoKeys/KEY_NAME"  # pragma: allowlist secret
```

Cloud Storage encrypts data at rest by default; using `--kms-key-name` makes the object use your customer-managed key.

Set these Cloud Run environment variables:

```text
AUTH_MODE=gcs
GCP_AUTH_BUCKET_NAME=YOUR_AUTH_BUCKET
GCP_AUTH_BLOB_NAME=users.json
SESSION_COOKIE_SECURE=true
```

The Cloud Run service account needs permission to read the object, for example `roles/storage.objectViewer` scoped to the bucket.

## Flask secret key

Set a strong `FLASK_SECRET_KEY` in local `.env` and use Secret Manager for Cloud Run rather than baking the secret into the container image.

## Build and run with Docker

```bash
docker build -t ons-flask-auth-template .
docker run --rm -p 8000:8000 --env-file .env -v "$PWD/users.json:/app/users.json:ro" ons-flask-auth-template
```

## Build and run with Podman

```bash
make podman-build
make podman-run
```

## Deploy to Cloud Run

Example:

```bash
gcloud run deploy ons-flask-auth-template \
  --source . \
  --region europe-west2 \
  --allow-unauthenticated \
  --set-env-vars AUTH_MODE=gcs,GCP_AUTH_BUCKET_NAME=YOUR_AUTH_BUCKET,GCP_AUTH_BLOB_NAME=users.json,SESSION_COOKIE_SECURE=true,SERVICE_NAME="Your Service Name"
```

Prefer supplying `FLASK_SECRET_KEY` from Secret Manager.

## Routes

| Route | Purpose |
|---|---|
| `/` | Protected landing page |
| `/login` | Sign-in page |
| `/check-login` | Login form POST endpoint |
| `/logout` | Clears the session |
| `/health` | Health check endpoint |
| `/cookies` | Placeholder cookies page |
| `/accessibility` | Placeholder accessibility statement |
| `/privacy` | Placeholder privacy notice |

## Development checks

```bash
make test
make lint
```

## Extending the template

Replace `src/ons_flask_auth_template/app_templates/index.html` and add new blueprints under `src/ons_flask_auth_template/routes/`.

Use the `@login_required` decorator for routes that should only be available after sign-in.
