"""
Picks the HTTPX library to work with, i.e. `httpx` or its `httpx2` successor.

All respx modules import `httpx` and `httpcore` from here, and *not* directly.

`httpx` is used when installed, otherwise `httpx2`. To pick one explicitly, e.g. when
both are installed, set the `RESPX_HTTPX` environment variable to `httpx` or `httpx2`.

Type checkers can't tell which one gets picked at runtime, and will assume `httpx`.
Define `RESPX_HTTPX2` as *always true* for them to assume `httpx2` instead.
"""

import os
from importlib.util import find_spec
from typing import Optional

__all__ = ["RESPX_HTTPX2", "httpcore", "httpx"]


def use_httpx2(name: Optional[str]) -> bool:
    if not name:
        return find_spec("httpx") is None
    if name not in ("httpx", "httpx2"):
        raise ImportError(
            f"Invalid RESPX_HTTPX {name!r}, expected either 'httpx' or 'httpx2'"
        )
    return name == "httpx2"


RESPX_HTTPX2 = use_httpx2(os.environ.get("RESPX_HTTPX"))

# Type checkers can't tell which branch runs. Mypy picks the first import, and pyright
# the one in try, hence this structure, for both to assume httpx by default.
try:
    if not RESPX_HTTPX2:  # pragma: nocover
        import httpcore
        import httpx
    else:  # pragma: nocover
        raise ImportError()
except ImportError:  # pragma: nocover
    if RESPX_HTTPX2:
        import httpcore2 as httpcore  # type: ignore[no-redef,unused-ignore]
        import httpx2 as httpx  # type: ignore[no-redef,unused-ignore]
    else:
        raise
