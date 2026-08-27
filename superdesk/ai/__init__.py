"""Configuration of the AI providers Superdesk talks to, and the actions built on top of them.

Security boundary: provider credentials are stored unencrypted, the way ingest and search provider
credentials are. The ``ai_studio`` privilege is therefore equivalent to access to every stored key.
A holder can point a provider's ``base_url`` at a host they control and have the key sent there,
and can narrow a key down by sorting a listing on ``api_key``, even though the key itself is never
returned in a response. Grant the privilege only to users already trusted with the system's
credentials.
"""

from .module import module

__all__ = ["module"]
