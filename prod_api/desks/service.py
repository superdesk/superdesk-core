from ..service import ProdApiService


class DesksService(ProdApiService):
    excluded_fields = {
        'default_content_template',
        'working_stage',
        'incoming_stage',
        'desk_metadata',
        'content_expiry',
    } | ProdApiService.excluded_fields
