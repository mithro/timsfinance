#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:


import getpass
import datetime
import os
import subprocess
import time

import optparse
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from finance import models
from finance.importers import csv_importer



####################
# FIXME: Move all the below into a common file used by all management commands.
####################
import textwrap
class SpecialHelpFormatter(optparse.IndentedHelpFormatter):
    def format_option(self, option):
        result = []
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = "%*s%s\n" % (self.current_indent, "", opts)
            indent_first = self.help_position
        else:                       # start help on same line as opts
            opts = "%*s%-*s  " % (self.current_indent, "", opt_width, opts)
            indent_first = 0
        result.append(opts)
        if option.help:
            help_text_lines = self.expand_default(option).split('\n')

            first = True
            for help_text in help_text_lines:
                if not help_text:
                    result.append("\n")
                    continue
                help_lines = textwrap.wrap(help_text, self.help_width)

                if first:
                    result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
                    result.extend(["%*s%s\n" % (self.help_position, "", line)
                                   for line in help_lines[1:]])
                    first = False
                else:
                    result.extend(["%*s%s\n" % (self.help_position, "", line)
                                   for line in help_lines])


        elif opts[-1] != "\n":
            result.append("\n")
        return "".join(result)

####################

class Command(BaseCommand):
    args = ''
    help = """Imports transactions from a hand downloaded CSV file.

If your CSV file looks like:
  03/07/2013,"-2.02","INTNL TRANSACTION FEE",""
  03/07/2013,"-67.19","PAYPAL *GELASKINS        4029357733  ON ##0713          60.80 US DOLLAR",""

  python manage.py csvimport --account accountname --filename data.csv \\
    --fields=DATE --fields=AMOUNT --fields=DESCRIPTION --fields=IGNORE

If your CSV file looks like:
  Effective Date,Entered Date,Transaction Description,Amount,Balance
  01/07/2012,30/06/2012,CAPITALISATION ,-876.50,197705.32
  ,30/06/2012,CAPITALISATION ,-8.00,196828.82

  python manage.py csvimport --account accountname --filename data.csv \\
    --fields=EFFECTIVE_DATE --fields=ENTERED_DATE --fields=DESCRIPTION \\
    --fields=AMOUNT --fields=RUNNING_TOTAL_INC
"""

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``OptionParser`` which will be used to
        parse the arguments to this command.

        """


        return optparse.OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version=self.get_version(),
                            option_list=self.option_list,
                            formatter=SpecialHelpFormatter())

#formatter_class=argparse.RawTextHelpFormatter

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
            help=("""
Field types in the CSV file, should be in the right order.

* DATE
Date of the transaction. If you only get one date use this.

* EFFECTIVE_DATE
Effective date of the transaction (IE when it took affect).

* ENTERED_DATE
Entered date of the transaction (IE when it first appeared in the system).

* DESCRIPTION
Description of the transaction.

* AMOUNT
Amounts in the accounts currency, both negative and positive.

* DEBIT
Removals from the amount to the account.

* CREDIT
Additions to the amount to the account.

* IGNORE
Ignore this field.

* RUNNING_TOTAL_INC
Running total *including* the line being processed transaction.

* RUNNING_TOTAL_EXC
Running total *excluding* the line being processed transaction.

""")),
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
            help=("Account to load CSV file into. Can either be the 'Account"
                  " ID' (normally a number like 12321354) or the 'Account"
                  " Short Name' what you set when creating the account.")),
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

        account = None
        try:
            account = models.Account.objects.get(account_id=options['account'])
        except Exception, e:
            print e
        try:
            account = models.Account.objects.get(short_id=options['account'])
        except Exception, e:
            print e
        if account is None:
            raise Exception("Could not find the account you specified.")

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
