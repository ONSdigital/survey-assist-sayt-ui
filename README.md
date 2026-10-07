# Survey Assist SAYT UI

A containerised Flask app for implementing a Search As You Type (SAYT) user interface to test Survey Assist Smart SAYT.

## Requirements

For local development you need:

* Python 3.12
* Poetry 2.2.1
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
| `SESSION_BACKEND`                | No                            | `client`                                         | Whether the session is stored `client` side in the browser or server side in `redis`|
| `REDIS_HOST` | Required when `SESSION_BACKEND=redis` | None | Redis hostname: `127.0.0.1` for a UI running locally; `redis` for the UI container in Podman Compose. |
| `REDIS_PORT`                | No        | `6379`                                                     | Used when `SESSION_BACKEND` is set as `redis`|
| `REDIS_MAX_CONNECTIONS`                | No                            |   `32`                                       | When `SESSION_BACKEND` is set to `redis` this variable defines the maximum number of connections|
| `REDIS_PASSWORD` | No | None | Redis authentication password. Configure for local password testing and for Memorystore when Redis is enabled. |
| `REDIS_USE_TLS` | No | `false` | Enables TLS for the Redis connection. Set to `true` for the GCP deployment, set to `false` for local dev testing  |
| `REDIS_CA_CERT_DATA` | Required when `REDIS_USE_TLS=true` | None | PEM encoded CA certificate used to verify the TLS certificate presented by Memorystore. Memorystore is accessed using its instance IP address rather than a DNS hostname. Hostname verification is therefore disabled, while certificate verification remains required against the configured Memorystore CA.|
| `SESSION_LIFETIME_DAYS` | No | `15` | Positive number of days from successful login until authentication expires; applies to client and Redis sessions. Redis writes do not extend this deadline. |


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
SESSION_BACKEND=client
```

`SURVEY_ASSIST_API_BASE_URL` and `SA_EMAIL` must be replaced with values for an API environment you can access.

### Inspect a local Redis session

When testing with `SESSION_BACKEND=redis`, you can inspect a saved session
without displaying its values by default:

```bash
REDIS_PASSWORD=<redis password> REDIS_HOST=127.0.0.1 REDIS_PORT=6379 \
  poetry run python scripts/inspect_redis_session.py
```

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

By default, the Makefile uses
`~/.config/gcloud/application_default_credentials.json`, where `gcloud auth
application-default login` writes Application Default Credentials. Override it when necessary, for example with a file in your home directory.

```bash
make docker-run CRED_FILE="${HOME}/gcp-project-creds-ui.json"
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

### Run the UI and Redis together with Podman Compose

Start the Podman machine if necessary:

```bash
podman machine list
podman machine init   # Only if no machine exists
podman machine start  # Only if the existing machine is stopped
```

`podman compose` requires an installed Compose provider (`docker-compose` or `podman-compose`).
It is a Podman command that delegates Compose file handling to that provider; check `podman compose --help` before proceeding.

Create `.env` from `.env.example` and configure `SURVEY_ASSIST_API_BASE_URL`, `SA_EMAIL`, `FLASK_SECRET_KEY` and `REDIS_PASSWORD`.

`REDIS_PASSWORD` is used by both the local Redis container and the UI.
Local Compose Redis does not use TLS; `REDIS_USE_TLS` is forced to `false`.

Create `users.json` using the local-user instructions above.

Make sure the Google credentials file configured by
`CRED_FILE` exists and can sign API tokens for `SA_EMAIL`.

The API URL must be reachable **from inside the UI container**.

Start both containers while keeping the existing client-side Flask sessions:

```bash
make podman-compose-up
```

Open `http://127.0.0.1:8000`

`make podman-compose-up` uses `SESSION_BACKEND=client`, regardless of the Redis service being present. The UI has no Redis startup dependency in this mode.

To exercise server-side sessions instead, use the specific redis compose command:

```bash
make podman-compose-redis-up
```

The UI waits for Redis to become healthy before starting. Within the Compose network its Redis host is `redis`, not `localhost`.

To view the logs of the UI you can run:

```bash
make podman-compose-logs
```

To inspect the Compose setup and verify Redis:

```bash
export CRED_FILE="${HOME}/.config/gcloud/application_default_credentials.json"
podman compose -f docker-compose.yaml exec redis redis-cli PING
```

Replace the exported `CRED_FILE` path if needed. If Redis is running you should see `PONG`.

Sign in to the ui, answer a survey question.

Inspect the browser's `session` cookie to check it does not increase as you navigate the survey.

Check that a corresponding Redis key exists:

```bash
podman compose -f docker-compose.yaml exec redis redis-cli --scan --pattern "sayt-ui:session:*"
```

The existing inspection script can read that local test record:

```bash
REDIS_PASSWORD=<redis password> REDIS_HOST=127.0.0.1 REDIS_PORT=6379 \
  poetry run python scripts/inspect_redis_session.py
```

Pass `--show-values` only for test responses; it prints personal and survey
data. Do not share the session ID or decoded record.

Stop and remove the local stack when finished:

```bash
make podman-compose-down
```

For local development, the Redis data is disposable and is not retained when its container is
removed.

When running in production, authenticated sessions expire 15 days after login, regardless of activity.
Redis session keys receive that absolute expiry, and an expired client-side
cookie is rejected at request time. Rendering `/survey/complete` clears the
session after producing the page; refreshing completion requires signing in
again. `/logout` also clears the session.


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

## Running with Redis session management

The [Podman Compose setup](#run-the-ui-and-redis-together-with-podman-compose)
is the recommended way to run both services together.

The following instructions allow you to start the UI against a separate local Redis container

### Check podman is running

Podman runs containers inside a Podman machine.

```bash
podman machine list
podman machine init   # Only if no machine exists
podman machine start  # Only if the machine is stopped
```

### Run Redis locally

In a separate terminal, run Redis with its port exposed on localhost

```bash
export REDIS_PASSWORD="not-a-real-password"  # pragma: allowlist secret
podman run --rm --name sayt-ui-redis \
  -p 127.0.0.1:6379:6379 \
  docker.io/library/redis:7-alpine redis-server --requirepass "${REDIS_PASSWORD}"
```

Check Redis responds, in another terminal execute:

```bash
podman exec -e REDISCLI_AUTH="${REDIS_PASSWORD}" sayt-ui-redis redis-cli PING
```

The Redis instance should respond ```PONG```

### Start the UI with Redis config

Ensure the following env vars are set:

```
SESSION_BACKEND=redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=not-a-real-password
REDIS_USE_TLS=false
```

Start the UI

```make run```

### Check a session is stored in Redis

Check that a server-side session key was created without displaying its contents

```
podman exec \
  -e REDISCLI_AUTH="${REDIS_PASSWORD}" \
  sayt-ui-redis \
  redis-cli --scan --pattern 'sayt-ui:session:*'
```

When you are **signed in** to the UI you should see a session id like:

```
sayt-ui:session:lbIaNIf0gGAyR-5wI5H--XB0cj_9bUZK-_pYE6WjJ1o
```

### Inspect the data in Redis

When you **complete the survey questions**, you can inspect a saved session displaying its values using the script ```inspect_redis_session.py```:

```bash
REDIS_PASSWORD=<redis password> REDIS_HOST=127.0.0.1 REDIS_PORT=6379 \
  poetry run python scripts/inspect_redis_session.py --show-values
```


You will need to provide the session-id that you want to inspect e.g ```lbIaNIf0gGAyR-5wI5H--XB0cj_9bUZK-_pYE6WjJ1o```, the output should show a session structure including the stored values.


### Environment variables for Cloud Run / Memorystore

```bash
SESSION_BACKEND=redis
REDIS_HOST=<memorystore-ip>
REDIS_PORT=<memorystore-tls-port>
REDIS_PASSWORD=<from-secret-manager>
REDIS_USE_TLS=true
REDIS_CA_CERT_DATA=<memorystore-ca-pem>
```

## Extending the code

Replace `src/survey_assist_sayt_ui/app_templates/index.html` and add new blueprints under `src/survey_assist_sayt_ui/routes/`.

Use the `@login_required` decorator for routes that should only be available after sign-in.

## Known Limitations

Previous navigation is supported when respondents use the Previous link provided by the application.

Navigating directly to an earlier question by changing or pasting a URL, or using the browser Back button to revisit previously answered questions, is not supported. Doing so may cause the application to infer the previous answered question incorrectly.

The application does not currently maintain an explicit navigation-history list; Previous navigation is designed around the supported application journey.
