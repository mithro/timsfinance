#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import getpass

from django.core.management.base import BaseCommand, CommandError

from finance import models

class Command(BaseCommand):
    args = '<site_id side_id ...>'
    help = 'Imports the accounts for each site.'

    def handle(self, *args, **options):
        for site_id in args:
            try:
                site = models.Site.objects.get(site_id=site_id)
            except models.Site.DoesNotExist:
                raise CommandError('Site "%s" does not exist' % site_id)

            module, klass = site.importer.rsplit('.', 1)

            exec("from %s import %s as importer_class" % (module, klass))
            importer = importer_class()

            if not site.password:
                password = getpass.getpass('Password for %s:' % site_id)
            else:
                password = site.password
            importer.login(site.username, password)

            importer.home()

            accounts = importer.accounts(site)
            for account in accounts:
                print account.description
                account.save()
