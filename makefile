
install:
	pip install .

uninstall:
	pip uninstall -y opendir_dl

reinstall: uninstall install

lint:
	pylint -E opendir_dl

clean:
	rm opendir_dl/*.pyc
	rm tests/*.pyc

clean_db:
	rm sqlite3.db

test:
	nosetests
