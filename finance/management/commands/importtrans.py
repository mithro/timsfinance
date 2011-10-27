#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import getpass
import datetime

from django.core.management.base import BaseCommand, CommandError

from finance import models

class Command(BaseCommand):
    args = '<account_id account_id ...>'
    help = 'Imports the transactions into an accounts.'

    def handle(self, *args, **options):
        end_date = datetime.datetime.now() - datetime.timedelta(days=1)
        start_date = end_date - datetime.timedelta(days=60)

        print start_date, end_date

        for account_id in args:
            try:
                account = models.Account.objects.get(account_id=account_id)
            except models.Account.DoesNotExist:
                raise CommandError('Account "%s" does not exist' % account_id)

            if not account.site.password:
                password = getpass.getpass('Password for %s:' % account.site.site_id)
            else:
                password = account.site.password

            module, klass = account.site.importer.rsplit('.', 1)
            exec("from %s import %s as importer_class" % (module, klass))
            importer = importer_class()

            importer.login(account.site.username, password)
            importer.home()

            try:
                transactions = importer.transactions(account, start_date, end_date)
                for transaction in transactions:
                    transaction.save()
            except Exception, e:
                print e
                import pdb
                pdb.post_mortem()
                raise

