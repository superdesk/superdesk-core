from ..service import ProdApiService


class UsersService(ProdApiService):
    excluded_fields = \
        {
            'user_preferences',
            'session_preferences',
            'password',
        } | ProdApiService.excluded_fields
