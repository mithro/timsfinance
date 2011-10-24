
resetsql:
	 python manage.py sqlclear finance | sqlite3 finance.sqlite3; python manage.py syncdb
