import nox

nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True
nox.options.keywords = "test + mypy"


@nox.session(python=["3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"])
@nox.parametrize("tool", ["httpx", "httpx2", "both"])
def test(session, tool):
    deps = ["pytest", "pytest-asyncio", "pytest-cov", "trio", "starlette", "flask"]
    if tool != "httpx":
        if session.python in ("3.8", "3.9"):
            session.skip("httpx2 requires Python 3.10+")
        deps.append("httpx2")
    session.install("--upgrade", *deps)
    # Install without dependencies to test httpx2 only, i.e. no httpx
    session.install("-e", ".", *(["--no-deps"] if tool == "httpx2" else []))

    if any(option in session.posargs for option in ("-k", "-x")):
        session.posargs.append("--no-cov")

    session.run("pytest", *session.posargs)
    if tool == "both":
        session.run("pytest", *session.posargs, env={"RESPX_HTTPX": "httpx2"})


@nox.session(python="3.10")
def mypy(session):
    session.install("--upgrade", "mypy", "httpx2")
    session.install("-e", ".")
    session.run("mypy")
    session.run("mypy", "--always-true", "RESPX_HTTPX2")


@nox.session(python="3.10")
def docs(session):
    deps = ["mkdocs", "mkdocs-material", "mkautodoc>=0.1.0"]
    session.install("--upgrade", *deps)
    session.install("-e", ".")
    args = session.posargs if session.posargs else ["build"]
    session.run("mkdocs", *args)
