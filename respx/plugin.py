import pytest

import respx


@pytest.fixture
def respx_mock():
    with respx.mock as _respx_mock:
        yield _respx_mock
