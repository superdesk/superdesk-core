from pymongo import uri_parser

from superdesk.core.types import MongoClientConfig


def get_mongo_client_config(app_config: dict, prefix: str = "MONGO") -> tuple[dict, str]:
    config = MongoClientConfig.create_from_dict(app_config, prefix)

    client_kwargs: dict = {
        "appname": config.appname,
        "connect": config.connect,
        "tz_aware": config.tz_aware,
    }

    if config.options is not None:
        client_kwargs.update(config.options)

    if config.write_concern is not None:
        client_kwargs.update(config.write_concern)

    if config.replicaSet is not None:
        client_kwargs["replicaset"] = config.replicaSet

    uri_parser.validate_options(client_kwargs)

    if config.uri is not None:
        host = config.uri
        # raises an exception if uri is invalid
        mongo_settings = uri_parser.parse_uri(host)

        # extract username and password from uri
        if mongo_settings.get("username"):
            client_kwargs["username"] = mongo_settings["username"]
            client_kwargs["password"] = mongo_settings["password"]

        # extract default database from uri
        dbname = mongo_settings.get("database")
        if not dbname:
            dbname = config.dbname

        # extract auth source from uri
        auth_source = mongo_settings["options"].get("authSource")
        if not auth_source:
            auth_source = dbname
    else:
        dbname = config.dbname
        auth_source = dbname
        host = config.host
        client_kwargs["port"] = config.port

    client_kwargs["host"] = host
    client_kwargs["authSource"] = auth_source

    if config.document_class is not None:
        client_kwargs["document_class"] = config.document_class

    auth_kwargs: dict = {}
    if config.username is not None:
        username = config.username
        password = config.password
        auth = (username, password)
        if any(auth) and not all(auth):
            raise Exception("Must set both USERNAME and PASSWORD or neither")
        client_kwargs["username"] = username
        client_kwargs["password"] = password
        if any(auth):
            if config.auth_mechanism is not None:
                auth_kwargs["authMechanism"] = config.auth_mechanism
            if config.auth_source is not None:
                auth_kwargs["authSource"] = config.auth_source
            if config.auth_mechanism_properties is not None:
                auth_kwargs["authMechanismProperties"] = config.auth_mechanism_properties

    return {**client_kwargs, **auth_kwargs}, dbname
