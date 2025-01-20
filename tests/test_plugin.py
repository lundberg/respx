from textwrap import dedent


def test_respx_mock_fixture(testdir):
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.fixture
        def some_fixture():
            yield "foobar"

        def test_plain_fixture(respx_mock):
            route = respx_mock.get("https://foo.bar/") % 204
            response = httpx.get("https://foo.bar/")
            assert response.status_code == 204


        @pytest.mark.respx(base_url="https://foo.bar", assert_all_mocked=False)
        def test_marked_fixture(respx_mock):
            route = respx_mock.get("/") % 204
            response = httpx.get("https://foo.bar/")
            assert response.status_code == 204
            response = httpx.get("https://example.org/")
            assert response.status_code == 200


        def test_with_extra_fixture(respx_mock, some_fixture):
            import respx
            assert isinstance(respx_mock, respx.Router)
            assert some_fixture == "foobar"


        @pytest.mark.respx(assert_all_mocked=False)
        def test_marked_with_extra_fixture(respx_mock, some_fixture):
            import respx
            assert isinstance(respx_mock, respx.Router)
            assert some_fixture == "foobar"
        """
    )
    testdir.makeini(
        dedent(
            """
            [pytest]
            asyncio-mode = auto
            asyncio_default_fixture_loop_scope = session
            """
        )
    )
    result = testdir.runpytest("-p", "respx")
    result.assert_outcomes(passed=4)
