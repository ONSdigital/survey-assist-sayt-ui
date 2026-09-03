# Survey Assist SAYT UI

A containerised Flask app for implementing a Search As You Type (SAYT) user interface to test Survey Assist Smart SAYT.

## Requirements

- Python 3.12
- Poetry 2.1.3
- Docker or Podman if building the container locally
- Google Cloud SDK credentials, if uploading the users file to GCS

## Install locally

```bash
poetry install
```

## Fetch the ONS Design System templates

The ONS Design System uses Nunjucks templates. The ONS guidance for Jinja apps is to use `ChainableUndefined` (which this application does), and when using the release zip, copy the `components` and `layout` folders into the Flask templates path.

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
src/survey_assist_sayt_ui/templates/components/
src/survey_assist_sayt_ui/templates/layout/
```

## Manage local users

Authentication users are stored in `users.json`. The management script can add,
update, or delete individual users while preserving all other user records.

### Add a user

```bash
poetry run python scripts/provision_users.py add \
  --username "user@example.com" \
  --output users.json
```
You will be prompted for the user's password. The password is hashed before being
written to `users.json`.

If `users.json` does not exist, it will be created.

Attempting to add a username that already exists will fail. Use `update` to change
an existing user's password.

### Change a user password

```bash
poetry run python scripts/provision_users.py update \
  --username "user@example.com" \
  --output users.json
```

### Delete a user

```bash
poetry run python scripts/provision_users.py delete \
  --username "user@example.com" \
  --output users.json
```

### Users.json

The generated file has this shape:

```json
{
  "users": [
    {
      "username": "user@example.com",
      "password_hash": "scrypt:..." # pragma: allowlist secret
    }
  ]
}
```

Passwords can also be supplied with `--password`, although interactive entry is
preferred because it avoids storing the plaintext password in shell history.

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

**Note:** if running in a **container locally** use the make commands and ensure `LOCAL_USERS_FILE=/app/users.json`

Then run:

```bash
poetry run flask --app 'survey_assist_sayt_ui.app:create_app()' run --debug --port 8000
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
poetry run python scripts/provision_users.py add \
  --username "user@example.com" \
  --output users.json \
  --bucket "YOUR_AUTH_BUCKET" \
  --blob "users.json"
```

**Warning:** When using the script to connect to GCS, ensure the local `users.json` contains the current contents of the GCS object before making changes. The complete local file is uploaded after the requested change.

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
docker build -t survey-assist-sayt-ui .
docker run --rm -p 8000:8000 --env-file .env -v "$PWD/users.json:/app/users.json:ro" survey-assist-sayt-ui
```

## Build and run with Podman

```bash
make podman-build
make podman-run
```

## Deploy to Cloud Run

Example:

```bash
gcloud run deploy survey-assist-sayt-ui \
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
| `/__meta` | UI build information |


## Development checks

```bash
make all-tests
make check-python
```

## Extending the code

Replace `src/survey_assist_sayt_ui/app_templates/index.html` and add new blueprints under `src/survey_assist_sayt_ui/routes/`.

Use the `@login_required` decorator for routes that should only be available after sign-in.
