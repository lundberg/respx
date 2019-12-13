import nox

nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True
nox.options.keywords = "test + check"

source_files = ("respx", "tests", "setup.py", "noxfile.py")
lint_requirements = ("flake8", "black", "isort")
docs_requirements = ("mkdocs", "mkdocs-material", "mkautodoc>=0.1.0")


@nox.session(python=["3.6", "3.7", "3.8"])
def test(session):
    session.install("--upgrade", "pytest", "pytest-asyncio", "pytest-cov", "trio")
    session.install("-e", ".")

    options = session.posargs
    if "-k" in options:
        options.append("--no-cov")

    session.run("pytest", "-v", *options)


@nox.session
def check(session):
    session.install("--upgrade", "flake8-bugbear", "mypy", *lint_requirements)
    session.install("-e", ".")

    session.run("black", "--check", "--diff", "--target-version=py36", *source_files)
    session.run("isort", "--check", "--diff", "--project=respx", "-rc", *source_files)
    session.run("flake8", *source_files)
    session.run("mypy", "respx")


@nox.session
def lint(session):
    session.install("--upgrade", "autoflake", *lint_requirements)

    session.run("autoflake", "--in-place", "--recursive", *source_files)
    session.run("isort", "--project=respx", "--recursive", "--apply", *source_files)
    session.run("black", "--target-version=py36", *source_files)

    check(session)


@nox.session
def docs(session):
    session.install("--upgrade", *docs_requirements)
    session.install("-e", ".")

    args = session.posargs if session.posargs else ["build"]
    session.run("mkdocs", *args)


@nox.session(reuse_venv=True)
def watch(session):
    session.install("--upgrade", *docs_requirements)
    session.install("-e", ".")

    session.run("mkdocs", "serve")
