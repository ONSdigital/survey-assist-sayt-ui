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

**This step is required for both local and containerized development.**

The UI creates a short-lived JWT for the Survey Assist API when the application starts. Authenticate with Google Cloud Application Default Credentials before running the UI locally:

```bash
gcloud auth application-default login
```

The credentials used by the UI need permission to sign JWTs for the API service account. The signed identity also needs access to the Survey Assist API.

## Install and run locally

### 1. Install dependencies

```bash
poetry install
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

Complete [Google Cloud authentication](#google-cloud-authentication-for-local-development) first.

Copy the example environment file:

```bash
cp .env.example .env
```

Generate a strong secret key for Flask:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Update at least the required values in `.env`:

```text
FLASK_SECRET_KEY=<use the generated secret from above>
SURVEY_ASSIST_API_BASE_URL=https://your-gateway-host/v1/survey-assist
SA_EMAIL=<service-account>@<your-project>.iam.gserviceaccount.com
```

Set `SURVEY_ASSIST_API_BASE_URL` to the base URL of a Survey Assist API environment you can access.

Set `SA_EMAIL` to the email address of the service account for that environment. Your Google Cloud user must have `iam.serviceAccounts.signJwt` permission on the service account specified by `SA_EMAIL` to sign JWTs on its behalf.

`make run` does not load `.env` itself, so export the file into your current shell before starting the application:

```bash
set -a
source .env
set +a
```

See [Configuration reference](#configuration-reference) for all supported settings, documentation and defaults.

### 4. Create a local user

The local UI reads sign-in users from `users.json`.

Add a user before you run the UI. The script creates `users.json` if it does not exist.

```bash
poetry run python scripts/provision_users.py add \
  --username "user@example.com"
```

You will be prompted for the user's password. The password is hashed before being written to `users.json`.

See [Manage local users](#manage-local-users) for other commands and options.

### 5. Run the UI

```bash
make run
```

Open:

```text
http://127.0.0.1:5000
```

You should be redirected to `/login`. Use the login information for a user added during the [user configuration step](#4-create-a-local-user).


## Build and run with containers

Before you run a container, complete [Google Cloud authentication](#google-cloud-authentication-for-local-development), [environment configuration](#3-configure-the-environment), and [local user setup](#4-create-a-local-user).

Docker and Podman use equivalent Make targets.
The run commands read `.env`. They mount `users.json` and the file specified by `CRED_FILE` into the container.

The default `CRED_FILE` is `$HOME/gcp-project-creds-ui.json`. If your credentials are at another path, pass it to the run command, for example `make docker-run CRED_FILE=/path/to/credentials.json`. A new `gcloud auth application-default login` usually stores credentials at `~/.config/gcloud/application_default_credentials.json`.

Run with Docker:

```bash
make docker-build
make docker-run
```

Or with Podman:

```bash
make podman-build
make podman-run
```

The container is available at:

```text
http://127.0.0.1:8000
```

### Run with Podman Compose

Set `REDIS_PASSWORD` in `.env`; the Redis container and UI use the same password.
The API URL must be reachable from inside the UI container.

Start the UI with client-side sessions:

```bash
make podman-compose-up
```

Open `http://127.0.0.1:8000`

The Redis container starts, but the UI does not depend on it in client mode.
To exercise server-side sessions with Redis, see [Running with Redis server-side sessions](#running-with-redis-server-side-sessions).

Stop and remove the local stack when finished:

```bash
make podman-compose-down
```

## Running with Redis server-side sessions

By default, session data is stored client-side in the browser. For server-side session storage, configure Redis.

### Configure Redis in local development

Set these environment variables:

```text
SESSION_BACKEND=redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=not-a-real-password
REDIS_USE_TLS=false
```

Then run Redis in a separate terminal:

```bash
export REDIS_PASSWORD="not-a-real-password"  # pragma: allowlist secret
podman run --rm --name sayt-ui-redis \
  -p 127.0.0.1:6379:6379 \
  docker.io/library/redis:7-alpine redis-server --requirepass "${REDIS_PASSWORD}"
```

Verify Redis responds:

```bash
podman exec -e REDISCLI_AUTH="${REDIS_PASSWORD}" sayt-ui-redis redis-cli PING
```

You should see `PONG`.

Start the UI:

```bash
make run
```

See [Testing Redis sessions](#testing-redis-sessions) to verify the session backend is working correctly.

### Use Redis in Podman Compose

To exercise server-side sessions with Podman Compose:

```bash
make podman-compose-redis-up
```

Within the Compose network, the Redis host is `redis`, not `localhost`.
Compose sets `REDIS_USE_TLS=false` for local Redis.

The UI waits for Redis to become healthy before starting. View logs:

```bash
make podman-compose-logs
```

Verify Redis is running:

```bash
CRED_FILE="${HOME}/gcp-project-creds-ui.json" podman compose -f docker-compose.yaml exec redis redis-cli PING
```

Test sessions as described in [Testing Redis sessions](#testing-redis-sessions). Stop and remove the stack:

```bash
make podman-compose-down
```

For local development, Redis data is disposable and is not retained when its container is removed.

## Configuration reference

The application configuration is read from environment variables at startup.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `SURVEY_ASSIST_API_BASE_URL` | Yes | None | Base URL for the Survey Assist API. The hostname is also the JWT audience. |
| `SA_EMAIL` | Yes | None | Service account email used to sign the Survey Assist API JWT. |
| `FLASK_SECRET_KEY` | No | `dev-only-change-me` | Flask session signing key. Set a strong value outside tests and development. |
| `SERVICE_NAME` | No | `Survey Assist SAYT UI` | Service name displayed by the UI. |
| `SURVEY_DEFINITION_FILE` | No | Bundled `survey_definitions/example_survey.json` | Path to the JSON survey definition to load. |
| `AUTH_MODE` | No | `local` | Authentication backend. Use `local` for a local users file or `gcs` for a GCS users file. |
| `LOCAL_USERS_FILE` | No | `users.json` | Path to the users file when `AUTH_MODE=local`. The supplied container commands mount it at `/app/users.json`. |
| `GCP_AUTH_BUCKET_NAME` | Required when `AUTH_MODE=gcs` | None | GCS bucket that contains the users file. |
| `GCP_AUTH_BLOB_NAME` | No | `users.json` | GCS object name for the users file. |
| `SESSION_COOKIE_SECURE` | No | `false` | Whether the session cookie is HTTPS-only. Set `false` for local HTTP development. Set `true` in Cloud Run. |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Google ADC discovery | Optional Google credentials path. Container Make targets set it for the mounted credentials file. |
| `SESSION_BACKEND` | No | `client` | Session storage backend. Use `client` or `redis`. |
| `REDIS_HOST` | Required when `SESSION_BACKEND=redis` | None | Redis hostname. Use `127.0.0.1` for a local UI or `redis` in Podman Compose. |
| `REDIS_PORT` | No | `6379` | Redis port when `SESSION_BACKEND=redis`. |
| `REDIS_MAX_CONNECTIONS` | No | `32` | Maximum Redis connections when `SESSION_BACKEND=redis`. |
| `REDIS_PASSWORD` | No | None | Redis authentication password. Set it for local password testing and Memorystore. |
| `REDIS_USE_TLS` | No | `false` | Enable TLS for Redis. Set `true` for Memorystore and `false` for local Redis. |
| `REDIS_CA_CERT_DATA` | Required when `REDIS_USE_TLS=true` | None | PEM-encoded CA certificate for Redis TLS verification. Memorystore uses an IP address, so hostname verification is disabled while CA verification remains required. |
| `SESSION_LIFETIME_DAYS` | No | `15` | Positive number of days from successful login until authentication expires; applies to client and Redis sessions. Redis writes do not extend this deadline. |

## Manage local users

By default, `scripts/provision_users` stores users in `users.json`. This can be changed by using `--output` parameter.

The script can add, update, or delete individual users while preserving all other user records.

To show the available management commands:

```bash
make manage-users
```

### Add a user

```bash
poetry run python scripts/provision_users.py add \
  --username "user@example.com"
```

Attempting to add a username that already exists will fail. Use `update` to change an existing user's password.
Use interactive password entry where possible. The `--password` option stores the plaintext password in shell history.

### Change a user password

```bash
poetry run python scripts/provision_users.py update \
  --username "user@example.com"
```

### Delete a user

```bash
poetry run python scripts/provision_users.py delete \
  --username "user@example.com"
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

## Configure authentication for Cloud Run

### Use a GCS users file

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

## Deploy to Cloud Run

Create a Secret Manager secret that contains a strong Flask secret key before you deploy:

```bash
gcloud secrets create survey-assist-sayt-ui-flask-secret \
  --replication-policy=automatic
python -c "import secrets; print(secrets.token_hex(32))" | \
  gcloud secrets versions add survey-assist-sayt-ui-flask-secret --data-file=-
```

Deploy the service:

```bash
gcloud run deploy survey-assist-sayt-ui \
  --source . \
  --region europe-west2 \
  --allow-unauthenticated \
  --set-env-vars "AUTH_MODE=gcs,GCP_AUTH_BUCKET_NAME=YOUR_AUTH_BUCKET,GCP_AUTH_BLOB_NAME=users.json,SESSION_COOKIE_SECURE=true,SERVICE_NAME=Your Service Name,SURVEY_ASSIST_API_BASE_URL=https://your-gateway-host/v1/survey-assist,SA_EMAIL=SERVICE_ACCOUNT_EMAIL" \
  --set-secrets "FLASK_SECRET_KEY=survey-assist-sayt-ui-flask-secret:latest"
```

Replace `YOUR_AUTH_BUCKET`, `SERVICE_ACCOUNT_EMAIL`, and the Survey Assist API URL with deployed environment values.
Grant the Cloud Run service account access to the secret.

To use Memorystore sessions in Cloud Run, also configure:

```text
SESSION_BACKEND=redis
REDIS_HOST=<memorystore-ip>
REDIS_PORT=<memorystore-tls-port>
REDIS_PASSWORD=<from-secret-manager>
REDIS_USE_TLS=true
REDIS_CA_CERT_DATA=<memorystore-ca-pem>
```

Store the Redis password and CA certificate securely. The Redis connection verifies the certificate against the configured CA.

## Testing Redis sessions

When configured to use Redis for session storage, you can verify the session backend is working correctly.

Sign in and answer survey questions. Then list the server-side session keys.

If you started Redis in a separate terminal, run:

```bash
podman exec -e REDISCLI_AUTH="${REDIS_PASSWORD}" sayt-ui-redis \
  redis-cli --scan --pattern 'sayt-ui:session:*'
```

If you started the Redis session stack with Podman Compose, run:

```bash
podman compose -f docker-compose.yaml -f docker-compose.redis.yaml exec redis \
  redis-cli --scan --pattern 'sayt-ui:session:*'
```

You should see a session ID like:

```
sayt-ui:session:lbIaNIf0gGAyR-5wI5H--XB0cj_9bUZK-_pYE6WjJ1o
```

Inspect the session data:

```bash
REDIS_PASSWORD="${REDIS_PASSWORD}" REDIS_HOST=127.0.0.1 REDIS_PORT=6379 \
  poetry run python scripts/inspect_redis_session.py --show-values
```

Provide the session ID from the previous step. The output shows the session structure including stored survey responses.

**Warning:** Pass `--show-values` only for test responses; it prints personal and survey data. Do not share the session ID or decoded record.

## Session lifetime

Authenticated sessions expire after `SESSION_LIFETIME_DAYS`, regardless of activity.
Redis keys receive that absolute expiry; Redis writes do not extend the deadline.
The app rejects expired client-side cookies at request time.
The app clears the session after it renders `/survey/complete` and after `/logout`.
Refreshing the completion page requires another sign-in.

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

## Development checks

**Prerequisite:** Complete [Install dependencies](#1-install-dependencies) and [Fetch ONS Design System templates](#2-fetch-the-ons-design-system-templates) before running development checks.

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

## Known Limitations

Previous navigation is supported when respondents use the Previous link provided by the application.

Navigating directly to an earlier question by changing or pasting a URL, or using the browser Back button to revisit previously answered questions, is not supported. Doing so may cause the application to infer the previous answered question incorrectly.

The application does not currently maintain an explicit navigation-history list; Previous navigation is designed around the supported application journey.
