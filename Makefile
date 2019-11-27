.PHONY: all
all: test


.PHONY: test
test:
	nox


.PHONY: clean
clean:
	rm -rf dist *.egg-info


.PHONY: release
release: clean
	python setup.py sdist bdist_wheel
	python -m twine upload dist/*
