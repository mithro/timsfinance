#!/usr/bin/python
#
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
from finance.importers import csv_importer



class Command(BaseCommand):
    args = ''
    help = 'Imports transactions from a hand downloaded CSV file.'

    option_list = BaseCommand.option_list + (
        make_option(
            "-f", "--filename",
            action="store", type="string", dest="filename",
            help="CSV file to import from."),
        make_option(
            "--debug",
            action="store_true", dest="debug", default=False,
            help="Run the Python debugger on an exception."),
        make_option(
            "--fields",
            action="append", dest="fields",
            default=[],
            help=("Field types in the CSV file, should be in the right order.\n"
                  "DATE              - Date of the transaction. If you only get one date use this.\n"
#                  "EFFECTIVE_DATE    - Effective date of the transaction (IE when it took affect).\n"
#                  "ENTERED_DATE      - Entered date of the transaction (IE when it first appeared in the system).\n"
                  "DESCRIPTION       - Description of the transaction.\n"
                  "AMOUNT            - Amount in the accounts currency.\n"
                  "IGNORE            - Ignore this field.\n"
#                  "RUNNING_TOTAL_INC - Running total *including* the line being processed transaction.\n"
#                  "RUNNING_TOTAL_EXC - Running total *excluding* the line being processed transaction.\n"
                  )),
        make_option(
            "--datefmt",
            action="store", type="string", dest="datefmt",
            default="%d/%m/%Y",
            help="Format for the dates in the CSV file."),
        make_option(
            "--reversed",
            action="store_true", dest="order", default=True,
            help="File is in reverse order (newest transactions first)."),
        make_option(
            "--account",
            action="store", type="string", dest="account",
            help="Account to load CSV file into."),
    )

    def handle(self, *args, **options):

        if not options['fields']:
            options['fields'] = ["AMOUNT", "DATE", "DESCRIPTION"]

        class TemporaryImporter(csv_importer.CSVImporter):
            FIELDS = [getattr(csv_importer.FieldList, field) for field in options['fields']]
            DATEFMT = options['datefmt']
            ORDER = [lambda x: x, reversed][options['order']]

        print "Using an order for the CSV file of:", options['fields']
        print

        try:
            account = models.Account.objects.get(account_id=options['account'])
        except Exception, e:
            print e
        try:
            account = models.Account.objects.get(short_id=options['account'])
        except Exception, e:
            print e

        importer = TemporaryImporter()
        try:
            print "Importing"
            r = importer.parse_file(account, file(options['filename']))
            print r
            return "Successful import."
        except Exception, e:
            import traceback
            print traceback.format_exc()
            if options['debug']:
                import pdb
                pdb.post_mortem()
            raise
