from ..service import ProdApiService


class PlanningService(ProdApiService):
    excluded_fields = \
        {
            '_id',
            'item_class',
            'flags',
            'lock_user',
            'lock_time',
            'lock_session',
        } | ProdApiService.excluded_fields


class EventsService(ProdApiService):
    excluded_fields = \
        {
            '_id',
            'lock_action',
            'lock_user',
            'lock_time',
            'lock_session',
        } | ProdApiService.excluded_fields


class AssignmentsService(ProdApiService):
    excluded_fields = \
        {
            'lock_action',
            'lock_user',
            'lock_time',
        } | ProdApiService.excluded_fields
