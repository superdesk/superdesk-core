from ..service import ProdApiService


class PlanningService(ProdApiService):
    excluded_fields = \
        {
            'item_class',
            'flags',
            'lock_user',
            'lock_time',
            'lock_session',
        } | ProdApiService.excluded_fields


class EventsService(ProdApiService):
    excluded_fields = \
        {
            'lock_action',
            'lock_user',
            'lock_time',
            'lock_session',
        } | ProdApiService.excluded_fields


assignments_excluded_fields = \
    {
        'lock_action',
        'lock_user',
        'lock_time',
    } | ProdApiService.excluded_fields
assignments_excluded_fields.remove('_id')


class AssignmentsService(ProdApiService):
    excluded_fields = assignments_excluded_fields
