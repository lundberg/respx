import nox

nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True
nox.options.keywords = "test + mypy"


@nox.session(python=["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"])
def test(session):
    deps = ["pytest", "pytest-asyncio", "pytest-cov", "trio", "starlette", "flask"]
    session.install("--upgrade", *deps)
    session.install("-e", ".")

    if any(option in session.posargs for option in ("-k", "-x")):
        session.posargs.append("--no-cov")

    session.run("pytest", *session.posargs)


@nox.session(python="3.8")
def mypy(session):
    session.install("--upgrade", "mypy")
    session.install("-e", ".")
    session.run("mypy")


@nox.session(python="3.10")
def docs(session):
    deps = ["mkdocs", "mkdocs-material", "mkautodoc>=0.1.0"]
    session.install("--upgrade", *deps)
    session.install("-e", ".")
    args = session.posargs if session.posargs else ["build"]
    session.run("mkdocs", *args)
