# Survey Assist SAYT UI

A containerised Flask app for implementing a Search As You Type (SAYT) user interface to test Survey Assist Smart SAYT.

## Requirements

For local development you need:

* Python 3.12
* Poetry 2.1.3
* `make`
* Google Cloud SDK (`gcloud`)
* Access to a Survey Assist API deployment
* Google Application Default Credentials (ADC) with permission to sign JWTs for the service account configured by `SA_EMAIL`

Docker or Podman is only required if you want to build and run the application in a container locally.

Node.js and npm are only required when changing `remote-autosuggest.js` and rebuilding the JavaScript bundle.

### Google Cloud authentication for local development

The UI creates a short-lived JWT for the Survey Assist API when the application starts. Authenticate with Google Cloud Application Default Credentials before running the UI locally:

```bash
gcloud auth application-default login
```

The authenticated identity must have permission to sign JWTs for the service account configured by `SA_EMAIL`.

## Install and run locally

### 1. Install dependencies

```bash
make install
```

### 2. Fetch the ONS Design System templates

```bash
make templates
```

The ONS Design System uses Nunjucks templates. The ONS guidance for Jinja apps is to use `ChainableUndefined` (which this application does), and when using the release zip, copy the `components` and `layout` folders into the Flask templates path.

The template fetch script reads `.design-system-version`. By default it is set to `latest`. To pin a release, replace the file contents with a tag such as:

```text
v72.0.0
```

The downloaded folders are ignored by git:

```text
src/survey_assist_sayt_ui/templates/components/
src/survey_assist_sayt_ui/templates/layout/
```

### 3. Configure the environment

Copy the example environment file:

```bash
cp .env.example .env
```

Update at least the required values:

```text
FLASK_SECRET_KEY=replace-with-a-long-random-secret
SURVEY_ASSIST_API_BASE_URL=https://your-gateway-host/v1/survey-assist
SA_EMAIL=<service-account>@<your-project>.iam.gserviceaccount.com
AUTH_MODE=local
LOCAL_USERS_FILE=users.json
SESSION_COOKIE_SECURE=false
```

`make run` does not load `.env` itself, so export the file into your current shell before starting the application:

```bash
set -a
source .env
set +a
```

See [Environment variables](#environment-variables) for all supported settings and defaults.

### 4. Create a local user

Authentication users are stored in `users.json`. Add a user before signing in locally:

```bash
poetry run python scripts/provision_users.py add \
  --username "user@example.com" \
  --output users.json
```

You will be prompted for the user's password. The password is hashed before being written to `users.json`.

If `users.json` does not exist, it will be created.

### 5. Run the UI

```bash
make run
```

Open:

```text
http://127.0.0.1:5000
```

You should be redirected to `/login`.

## Environment variables

The application configuration is read from environment variables at startup.

| Variable                         | Required                      | Default                                          | Purpose                                                                                                                                                                             |
| -------------------------------- | ----------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SURVEY_ASSIST_API_BASE_URL`     | Yes                           | None                                             | Base URL for the Survey Assist API. The hostname is also used as the JWT audience.                                                                                                  |
| `SA_EMAIL`                       | Yes                           | None                                             | Service account email used as the issuer/subject when signing the Survey Assist API JWT.                                                                                            |
| `FLASK_SECRET_KEY`               | No                            | `dev-only-change-me`                             | Flask session signing key. Set a strong value outside tests/development.                                                                                                            |
| `SERVICE_NAME`                   | No                            | `Survey Assist SAYT UI`                          | Service name displayed by the UI.                                                                                                                                                   |
| `SURVEY_DEFINITION_FILE`         | No                            | Bundled `survey_definitions/example_survey.json` | Path to the JSON survey definition to load.                                                                                                                                         |
| `AUTH_MODE`                      | No                            | `local`                                          | Authentication backend. Use `local` for a local `users.json` file or `gcs` for a GCS-hosted users file.                                                                             |
| `LOCAL_USERS_FILE`               | No                            | `users.json`                                     | Path to the users file when `AUTH_MODE=local`. Use `/app/users.json` when running the supplied local container commands.                                                            |
| `GCP_AUTH_BUCKET_NAME`           | Required when `AUTH_MODE=gcs` | None                                             | GCS bucket containing the users file.                                                                                                                                               |
| `GCP_AUTH_BLOB_NAME`             | No                            | `users.json`                                     | GCS object name containing the users file.                                                                                                                                          |
| `SESSION_COOKIE_SECURE`          | No                            | `false`                                          | Whether the session cookie is HTTPS-only. Use `false` for local HTTP development and `true` in Cloud Run.                                                                           |
| `GOOGLE_APPLICATION_CREDENTIALS` | No                            | Google ADC discovery                             | Optional path to Google credentials. Normally unnecessary locally after `gcloud auth application-default login`; the container Make targets set it when mounting a credential file. |

### Example local environment

A typical local configuration is:

```text
FLASK_SECRET_KEY=replace-with-a-long-random-secret
SERVICE_NAME=Survey Assist SAYT UI
SURVEY_ASSIST_API_BASE_URL=https://your-gateway-host/v1/survey-assist
SA_EMAIL=<service-account>@<your-project>.iam.gserviceaccount.com
AUTH_MODE=local
LOCAL_USERS_FILE=users.json
SESSION_COOKIE_SECURE=false
```

`SURVEY_ASSIST_API_BASE_URL` and `SA_EMAIL` must be replaced with values for an API environment you can access.

## Manage local users

Authentication users are stored in `users.json`. The management script can add, update, or delete individual users while preserving all other user records.

To show the available management commands:

```bash
make manage-users
```

### Add a user

```bash
poetry run python scripts/provision_users.py add \
  --username "user@example.com" \
  --output users.json
```

Attempting to add a username that already exists will fail. Use `update` to change an existing user's password.

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
      "password_hash": "scrypt:..."  # pragma: allowlist secret
    }
  ]
}
```

Passwords can also be supplied with `--password`, although interactive entry is preferred because it avoids storing the plaintext password in shell history.

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

Set a strong `FLASK_SECRET_KEY` in local development and use Secret Manager for Cloud Run rather than baking the secret into the container image.

## Build and run with Docker

The Docker Make targets build the image and run it using `.env`, `users.json`, and the credentials file configured by `CRED_FILE` in the Makefile:

```bash
make docker-build
make docker-run
```

By default `CRED_FILE` is `~/gcp-project-creds-ui.json`. Override it when necessary, for example:

```bash
make docker-run CRED_FILE=/path/to/credentials.json
```

The container is available at:

```text
http://127.0.0.1:8000
```

For local container execution, set:

```text
LOCAL_USERS_FILE=/app/users.json
```

## Build and run with Podman

```bash
make podman-build
make podman-run
```

The Podman target uses the same `.env`, users-file mount, credential-file mount, and port as the Docker target.

## Deploy to Cloud Run

Example:

```bash
gcloud run deploy survey-assist-sayt-ui \
  --source . \
  --region europe-west2 \
  --allow-unauthenticated \
  --set-env-vars AUTH_MODE=gcs,GCP_AUTH_BUCKET_NAME=YOUR_AUTH_BUCKET,GCP_AUTH_BLOB_NAME=users.json,SESSION_COOKIE_SECURE=true,SERVICE_NAME="Your Service Name"
```

Also configure the required `SURVEY_ASSIST_API_BASE_URL` and `SA_EMAIL` values for the deployed environment, and prefer supplying `FLASK_SECRET_KEY` from Secret Manager.

## Routes

| Route            | Purpose                             |
| ---------------- | ----------------------------------- |
| `/`              | Protected landing page              |
| `/login`         | Sign-in page                        |
| `/check-login`   | Login form POST endpoint            |
| `/logout`        | Clears the session                  |
| `/health`        | Health check endpoint               |
| `/cookies`       | Placeholder cookies page            |
| `/accessibility` | Placeholder accessibility statement |
| `/privacy`       | Placeholder privacy notice          |
| `/__meta`        | UI build information                |

## Development checks

Run all tests:

```bash
make all-tests
```

Run formatting, linting, type checking, and security checks:

```bash
make check-python
```

To run the checks without applying Ruff fixes or formatting changes:

```bash
make check-python-nofix
```

## Extending the code

Replace `src/survey_assist_sayt_ui/app_templates/index.html` and add new blueprints under `src/survey_assist_sayt_ui/routes/`.

Use the `@login_required` decorator for routes that should only be available after sign-in.
