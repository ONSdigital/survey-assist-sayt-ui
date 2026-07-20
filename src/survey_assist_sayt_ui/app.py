"""Flask application factory for the Survey Assist SAYT UI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, request
from jinja2 import ChainableUndefined, ChoiceLoader, FileSystemLoader
from survey_assist_utils.api_token.jwt_utils import check_and_refresh_token

from survey_assist_sayt_ui.services.business_activity import HttpBusinessActivitySearchClient
from survey_assist_sayt_ui.survey.loader import (
    SurveyDefinitionError,
    load_survey_definition,
)
from survey_assist_sayt_ui.survey.models import SurveyDefinition

from .auth.routes import auth_blueprint
from .auth.service import AuthService, build_auth_store
from .config import Settings, load_settings
from .routes.main import main_blueprint

logger = logging.getLogger(__name__)

TokenRefresher = Callable[[int, str, str, str], tuple[int, str]]

dataclass(slots=True)


class JwtTokenState:  # pylint: disable=too-few-public-methods
    """Runtime state for the short-lived SAYT API JWT."""

    start_time: int = 0
    token: str = ""


def _get_api_gateway_hostname(api_url: str) -> str:
    """Extract the API Gateway audience from the configured endpoint URL."""
    hostname = urlparse(api_url).netloc.rstrip("/")

    if not hostname:
        raise ValueError("SAYT_API_URL must include a scheme and hostname")

    return hostname


def create_app(  # pylint: disable=too-many-locals
    settings: Settings | None = None,
    auth_service: AuthService | None = None,
    survey_definition: SurveyDefinition | None = None,
    *,
    token_refresher: TokenRefresher | None = None,
) -> Flask:
    """Create and configure the Flask application.

    Args:
        settings: Optional runtime settings. When omitted, settings are loaded from
            environment variables.
        auth_service: Optional authentication service implementation.
        survey_definition: Optional preloaded survey definition, primarily for
            testing.
        token_refresher: Optional callable to refresh the SAYT API JWT.

    Returns:
        Flask: The configured Flask application instance.
    """

    def refresh_sayt_api_token_state(*, force: bool = False) -> tuple[bool, str]:
        """Refresh the SAYT API token state when it is approaching expiry."""
        previous_start_time = token_state.start_time

        if force:
            token_state.start_time = 0

        token_state.start_time, token_state.token = refresh_token(
            token_state.start_time,
            token_state.token,
            gateway_hostname,
            resolved_settings.sa_email,
        )

        return token_state.start_time != previous_start_time, token_state.token

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    resolved_settings = settings or load_settings()

    resolved_survey_definition = survey_definition

    if resolved_survey_definition is None:
        survey_path = Path(resolved_settings.survey_definition_file)

        try:
            resolved_survey_definition = load_survey_definition(survey_path)
            logger.info("Loaded survey definition from %s", survey_path)
        except SurveyDefinitionError as exc:
            logger.exception(
                "Failed to load survey definition from %s",
                survey_path,
            )
            raise RuntimeError(f"Unable to start with survey definition {survey_path}") from exc

    refresh_token = token_refresher or check_and_refresh_token

    app = Flask(__name__, template_folder="app_templates")
    app.jinja_env.undefined = ChainableUndefined

    design_templates = Path(__file__).parent / "templates"
    loaders = []
    if app.jinja_loader is not None:
        loaders.append(app.jinja_loader)
    loaders.append(FileSystemLoader(str(design_templates)))
    app.jinja_loader = ChoiceLoader(loaders)

    app.secret_key = resolved_settings.secret_key
    app.config["settings"] = resolved_settings
    app.config["auth_service"] = auth_service or AuthService(build_auth_store(resolved_settings))

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=resolved_settings.session_cookie_secure,
    )

    app.extensions["survey_definition"] = resolved_survey_definition

    # Setup the business activity search client with a short-lived JWT token
    gateway_hostname = _get_api_gateway_hostname(resolved_settings.sayt_api_url)

    token_state = JwtTokenState()
    _, initial_token = refresh_sayt_api_token_state(force=True)

    business_activity_client = HttpBusinessActivitySearchClient(
        endpoint_url=resolved_settings.sayt_api_url,
        token=initial_token,
        query_parameter="description",
        timeout_seconds=5.0,
        token_refresher=lambda: refresh_sayt_api_token_state(force=True)[1],
    )

    app.extensions["business_activity_search_client"] = business_activity_client

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)

    @app.context_processor
    def inject_settings() -> dict[str, Settings]:
        """Expose settings within templates.

        Returns:
            dict[str, Settings]: Template context containing resolved settings.
        """
        return {"settings": resolved_settings}

    # Before each request, check if the SAYT API JWT is approaching expiry
    # and refresh it if necessary
    @app.before_request
    def refresh_sayt_api_token() -> None:
        """Refresh the SAYT API token when it is approaching expiry."""
        refreshed, token = refresh_sayt_api_token_state()

        if not refreshed:
            return

        business_activity_client.update_token(token)

        logger.info(
            "Refreshed SAYT API JWT for method=%s endpoint=%s",
            request.method,
            request.endpoint,
        )

    logger.info("Created Flask app with auth_mode=%s", resolved_settings.auth_mode)
    return app
