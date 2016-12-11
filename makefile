
install:
	pip install .

uninstall:
	pip uninstall -y opendir_dl

reinstall: uninstall install

lint:
	pylint -E opendir_dl

clean:
	rm -f opendir_dl/*.pyc
	rm -f tests/*.pyc
	rm -rf coverage_html
	rm -f .coverage

clean_db:
	rm -f sqlite3.db
	rm -f tests/sqlite3.db

test:
	nosetests
