class ElasticNotConfiguredForResource(KeyError):
    def __init__(self, resource_name: str):
        super().__init__(f"Elasticsearch not enabled on resource '{resource_name}'")
