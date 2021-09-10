import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from main import app
import typing as t
import respx


@pytest.fixture()
def fast_api_app() -> FastAPI:
    return app


@pytest.fixture()
def client_app(fast_api_app: FastAPI) -> t.Generator[TestClient, None, None]:
    with TestClient(fast_api_app) as client:
        yield client


def test_app_for_test(client_app: TestClient) -> None:
    with respx.mock(
        base_url='https://test.com',
        assert_all_called=True,
        assert_all_mocked=True,
    ) as respx_mock:
        respx_mock.post('/post').respond(status_code=400, text='Bad request')
        response = client_app.post('/endpoint', json={'body': 'data'})
        assert response.status_code == 400
        assert response.json()['detail'] == 'Bad request'
