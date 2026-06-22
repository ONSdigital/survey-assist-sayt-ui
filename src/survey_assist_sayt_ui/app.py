"""Flask application factory for the Survey Assist SAYT UI."""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask
from jinja2 import ChainableUndefined, ChoiceLoader, FileSystemLoader

from .auth.routes import auth_blueprint
from .auth.service import AuthService, build_auth_store
from .config import Settings, load_settings
from .routes.main import main_blueprint

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, auth_service: AuthService | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        settings: Optional runtime settings. When omitted, settings are loaded from
            environment variables.
        auth_service: Optional authentication service implementation.

    Returns:
        Flask: The configured Flask application instance.
    """
    resolved_settings = settings or load_settings()

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

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)

    @app.context_processor
    def inject_settings() -> dict[str, Settings]:
        """Expose settings within templates.

        Returns:
            dict[str, Settings]: Template context containing resolved settings.
        """
        return {"settings": resolved_settings}

    logger.info("Created Flask app with auth_mode=%s", resolved_settings.auth_mode)
    return app
