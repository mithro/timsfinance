#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import getpass
import datetime
import os
import subprocess
import time

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from finance import models


class VNCServer(object):

    def __init__(self, viewer=False):
        self.display = ':10'
        self.original = os.getenv('DISPLAY')

        self.vncserver = None

        self.viewer = viewer

    def __enter__(self):
        # Start the VNCServer
        p = subprocess.Popen(
            ' '.join(['vncserver', self.display, '-SecurityTypes', 'None']),
            shell=True,
            stdout=file('vncserver.stdout', 'w'),
            stderr=subprocess.STDOUT,
            )
        p.wait()
        self.vncserver = 'RUNNING'

        # Set the environment
        os.environ['DISPLAY'] = ':10'

        # Start a window manager
        winman = subprocess.Popen(
            ' '.join(['ratpoison']),
            shell=True,
            )

        # Start a viewer if needed
        if self.viewer:
            viewer = subprocess.Popen(
                ' '.join(['vncviewer', self.display]),
                shell=True,
                stdout=file('vncviewer.stdout', 'w'),
                stderr=subprocess.STDOUT,
                env={'DISPLAY': self.original},
                )

    def __exit__(self, exc_type, exc_value, traceback):
        if self.vncserver == 'RUNNING':
            os.putenv('DISPLAY', self.original)

            p = subprocess.Popen(
                ' '.join(['vncserver', '-kill', self.display]),
                shell=True,
                )
            p.wait()

            self.vncserver = 'TERMINATED'


class Command(BaseCommand):
    args = ''
    help = 'Imports the transactions into an accounts.'

    option_list = BaseCommand.option_list + (
        make_option(
            "--viewer", action="store_true", dest="viewer",
            default=False,
            help="Start a VNCViewer so you can watch the Selenium test run."),
        make_option(
            "--debug", action="store_true", dest="debug",
            default=False,
            help="Run the Python debugger on an exception."),
        make_option(
            "--accounts", action="append", dest="accounts",
            help="Only import from the following accounts."),
    )

    def handle(self, *args, **options):
        dry_run = len(args) > 0

        print options['accounts']

        with VNCServer(viewer=options['viewer']):
            for site in models.Site.objects.all():
                # Only start up this site if it has an account we are going to import from.
                if options['accounts']:
                    for account in site.account_set.all():
                        if account.account_id in options['accounts']:
                            break
                        if account.short_id in options['accounts']:
                            break
                    else:
                        continue

                if not site.password:
                    password = getpass.getpass('Password for %s:' % site.site_id)
                else:
                    password = site.password

                # Login into the website
                module, klass = site.importer.rsplit('.', 1)

                exec("from %s import %s as importer_class" % (module, klass))
                importer = importer_class()
                importer.login(site.username, password)

                # Get transactions for each account
                for account in site.account_set.all():
                    if options['accounts']:
                        if account.account_id in options['accounts'] or account.short_id in options['accounts']:
                            pass
                        else:
                            continue

                    importer.home()

                    end_date = datetime.datetime.now() - datetime.timedelta(days=1)
                    # Get the oldest transaction
                    oldest_transaction = account.transaction_set.all().order_by('-imported_entered_date')
                    if not oldest_transaction:
                        start_date = end_date - datetime.timedelta(days=30)
                    else:
                        # 30 days before this transaction
                        start_date = oldest_transaction[0].imported_entered_date - datetime.timedelta(days=30)

                    print "Importing into %-20s starting at %s to %s" % (
                        account, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

                    try:
                        transactions = importer.transactions(account, start_date, end_date)
                        for transaction in transactions:
                            print transaction
                            transaction.save()
                    except Exception, e:
                        if options['debug']:
                            import pdb
                            pdb.post_mortem()
                            raise
        return

