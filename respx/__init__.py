from .__version__ import __version__
from .api import HTTPXMock

# Expose mock api
mock = HTTPXMock(assert_all_called=False)
__api__ = list(filter(lambda m: not m.startswith("_"), dir(mock)))

__all__ = ["__version__", "HTTPXMock", "mock"]
__all__.extend(__api__)
globals().update({method: getattr(mock, method) for method in __api__})
