import superdesk


def init_app(app) -> None:
    app.client_config.update(
        {
            "tansa": {
                "base_url": app.config.get("TANSA_CLIENT_BASE_URL"),
                "app_id": app.config.get("TANSA_APP_ID"),
                "app_version": superdesk.__version__,
                "user_id": app.config.get("TANSA_USER_ID"),
                "profile_id": int(app.config["TANSA_PROFILE_ID"]) if app.config.get("TANSA_PROFILE_ID") else None,
                "license_key": app.config.get("TANSA_LICENSE_KEY"),
                "profiles": app.config.get("TANSA_PROFILES"),
            },
        }
    )
