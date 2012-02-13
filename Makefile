###############################################################################
## Helpful Definitions
###############################################################################
define \n


endef

ACTIVATE = . bin/activate

###############################################################################
# Export the configuration to sub-makes
###############################################################################
export


###############################################################################
# VirtualEnv set up
###############################################################################
virtualenv: bin/activate
lib: bin/activate

distclean: virtualenv-clean clean

virtualenv-clean:
	rm -rf bin include lib lib64 share src

clean:
	git clean -f -d

bin/activate:
	virtualenv --no-site-packages .

lib/python2.6/site-packages/distribute-0.6.24-py2.6.egg-info: lib
	rm distribute*.tar.gz
	$(ACTIVATE) && pip install -U distribute

lib/python2.6/site-packages/ez_setup.py: lib
	$(ACTIVATE) && pip install ez_setup

src/pip-delete-this-directory.txt: requirements.txt
	$(ACTIVATE) && pip install -E . -r requirements.txt
	mkdir src || true
	touch -r requirements.txt src/pip-delete-this-directory.txt

install: lib/python2.6/site-packages/ez_setup.py lib/python2.6/site-packages/distribute-0.6.24-py2.6.egg-info src/pip-delete-this-directory.txt

###############################################################################
# Actual useful targets
###############################################################################

SOURCE=$(shell find \( -name bin -o -name include -o -name lib -o -name src \) -prune -o -name \*.py -print)

prepare-serve: install
	$(ACTIVATE) && python manage.py collectstatic --noinput
	$(ACTIVATE) && python manage.py syncdb

serve: prepare-serve install
	$(ACTIVATE) && python manage.py runserver

lint: install
	@# R0904 - Disable "Too many public methods" warning
	@# W0221 - Disable "Arguments differ from parent", as get and post will.
	@# E1103 - Disable "Instance of 'x' has no 'y' member (but some types could not be inferred)"
	@# I0011 - Disable "Locally disabling 'xxxx'"
	$(ACTIVATE) && python \
		-W "ignore:disable-msg is:DeprecationWarning:pylint.lint" \
		-c "import sys; from pylint import lint; lint.Run(sys.argv[1:])" \
		--reports=n \
		--include-ids=y \
		--no-docstring-rgx "(__.*__)|(get)|(post)|(main)" \
		--indent-string='    ' \
		--disable=W0221 \
		--disable=R0904 \
		--disable=E1103 \
		--disable=I0011 \
		--const-rgx='[a-z_][a-z0-9_]{2,30}$$' ${SOURCE} 2>&1 | grep -v 'maximum recursion depth exceeded'

reset-sql:
	python manage.py sqlclear finance | sqlite3 finance.sqlite3; python manage.py syncdb

test:
	python manage.py test

.PHONY: lint reset-sql test
