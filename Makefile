.PHONY: test
test:
	nox

.PHONY: clean
clean:
	rm -rf dist respx.egg-info

.PHONY: build
build: clean
	python setup.py sdist bdist_wheel

.PHONY: release
release: build
	python -m twine upload dist/*
