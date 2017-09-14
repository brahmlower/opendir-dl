
define USAGE_HELP
Available targets:
  help       - Print this message
  install    - Install the package
  uninstall  - Uninstall the package
  reinstall  - Reinstall the package
  lint       - Lint the package (only for errors)
  clean      - Removes .pyc files
  clean_db   - Removes sqlite database files
  test       - Run tests using nose
endef
export USAGE_HELP

.PHONY: help
help:
	@echo "$$USAGE_HELP"

.PHONY: install
install: lint
	pip install .

.PHONY: uninstall
uninstall:
	pip uninstall -y opendir_dl

.PHONY: reinstall
reinstall: uninstall install

.PHONY: lint
lint:
	pylint -E opendir_dl

.PHONY: clean
clean:
	rm -f opendir_dl/*.pyc
	rm -f tests/*.pyc
	rm -rf coverage_html
	rm -f .coverage

.PHONY: clean_db
clean_db:
	rm -f sqlite3.db
	rm -f tests/sqlite3.db

.PHONY: test
test: clean
	nosetests
