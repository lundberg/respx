.PHONY: test
test:
	nox

.PHONY: clean
clean:
	rm -rf build dist respx.egg-info

.PHONY: build
build: clean
	python -m pip install --upgrade pip
	python -m pip install --upgrade wheel
	python setup.py sdist bdist_wheel

.PHONY: release
release: build
	python -m pip install --upgrade twine
	python -m twine upload dist/*
