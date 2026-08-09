from application.ports import MarketplaceAdapterError


class FakeMarketplaceAdapter:
    """Adaptador configurable de memoria exclusivo para pruebas."""

    def __init__(
        self,
        *,
        marketplace=None,
        business_models=(),
        snapshots=(),
        requirements=(),
        restrictions=(),
        capabilities=(),
        failures=None,
    ):
        self._marketplace = marketplace
        self._business_models = tuple(business_models)
        self._snapshots = tuple(snapshots)
        self._requirements = tuple(requirements)
        self._restrictions = tuple(restrictions)
        self._capabilities = tuple(capabilities)
        self._failures = dict(failures or {})

    @property
    def adapter_id(self):
        return "fake-marketplace-adapter"

    def _return_or_raise(self, operation, value):
        failure = self._failures.get(operation)
        if failure is not None:
            if not isinstance(failure, Exception):
                failure = MarketplaceAdapterError(str(failure))
            raise failure
        return value

    def get_marketplace(self, region):
        return self._return_or_raise("marketplace", self._marketplace)

    def list_business_models(self, marketplace, region):
        return self._return_or_raise("business_models", self._business_models)

    def list_condition_snapshots(self, marketplace, region):
        return self._return_or_raise("snapshots", self._snapshots)

    def list_requirements(self, marketplace, region):
        return self._return_or_raise("requirements", self._requirements)

    def list_restrictions(self, marketplace, region):
        return self._return_or_raise("restrictions", self._restrictions)

    def list_capabilities(self, marketplace, region):
        return self._return_or_raise("capabilities", self._capabilities)
