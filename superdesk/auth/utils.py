from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


def generate_url_with_token(url: str, expiry_days: int = 7, **payload) -> str:
    """Generate a URL with JWT token for use with blueprint_auth_or_token.

    See Also:
        superdesk.auth.decorator.blueprint_auth_or_token: Decorator that validates the token.
    """
    from superdesk.utils import jwt_encode

    token = jwt_encode(payload, expiry=expiry_days)
    parsed = urlparse(url)
    query = parse_qsl(parsed.query)
    query.append(("token", token))
    return urlunparse(parsed._replace(query=urlencode(query)))
