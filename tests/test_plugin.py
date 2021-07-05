def test_respx_mock_fixture(testdir):
    testdir.makepyfile(
        """
        import httpx
        import pytest


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
        """
    )
    result = testdir.runpytest("-p", "respx")
    result.assert_outcomes(passed=2)
