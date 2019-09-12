from ..service import ProdApiService


class ItemsService(ProdApiService):
    excluded_fields = \
        {
            '_id',
            'fields_meta',
            'unique_id',
            'family_id',
            'event_id',
            'lock_session',
            'lock_action',
            'lock_time',
            'lock_user',
        } | ProdApiService.excluded_fields
