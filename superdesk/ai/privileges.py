"""Privilege names of the AI module.

They live apart from ``module.py`` so the endpoint classes it registers can guard a route with one
without importing the module that imports them.
"""

#: Grants access to the AI configuration: the providers and the actions built on them
AI_STUDIO_PRIVILEGE = "ai_studio"

#: Grants the right to run AI actions on content
AI_PRIVILEGE = "ai"
