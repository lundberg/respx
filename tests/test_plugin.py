def test_respx_mock_fixture(testdir):
    testdir.makepyfile(
        """
        import httpx

        def test_fixture(respx_mock):
            route = respx_mock.get("https://foo.bar/") % httpx.Response(202)
            response = httpx.get("https://foo.bar/")
            assert response.status_code == 202
        """
    )
    result = testdir.runpytest("-p", "respx")
    result.assert_outcomes(passed=1)
