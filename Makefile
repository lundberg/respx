.PHONY: all
all: format lint mypy coverage


.PHONY: test
test:
	python setup.py test $(test)


.PHONY: coverage
coverage:
	coverage run setup.py test
	coverage report
	coverage xml


.PHONY: lint
lint:
	flake8 respx --exit-zero


.PHONY: mypy
mypy:
	mypy respx


.PHONY: format
format:
	black respx tests
	autoflake -r -i --remove-all-unused-imports respx tests
	isort -rc respx tests


.PHONY: clean
clean:
	rm -rf dist
	rm -rf *.egg-info


.PHONY: publish
publish: clean
	python setup.py sdist bdist_wheel
	python -m twine upload dist/*


.PHONY: requirements
requirements:
	pip-compile \
		--upgrade --pre --generate-hashes \
		--output-file requirements.dev.txt \
		requirements.dev.in
	chown \
		--reference requirements.dev.in \
		requirements.dev.txt
