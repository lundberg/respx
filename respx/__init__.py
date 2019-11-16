from .mock import HTTPXMock

__all__ = ["HTTPXMock"]

# Expose mock api
__httpx_mock = HTTPXMock()
__api_methods = list(filter(lambda m: not m.startswith("_"), dir(__httpx_mock)))
__all__.extend(__api_methods)
globals().update({method: getattr(__httpx_mock, method) for method in __api_methods})
