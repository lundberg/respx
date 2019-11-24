# type: ignore
from .mock import HTTPXMock

# Expose mock api
mock = HTTPXMock(assert_all_called=False, local=False)
__api__ = list(filter(lambda m: not m.startswith("_"), dir(mock)))

__all__ = ["HTTPXMock", "mock"]
__all__.extend(__api__)
globals().update({method: getattr(mock, method) for method in __api__})
