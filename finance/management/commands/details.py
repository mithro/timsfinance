#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
"""
The linker looks for transactions which should be linked together, such as
transfers between accounts.
"""

from datetime import datetime, timedelta
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from finance import models
from finance.utils import dollar_fmt


class Command(BaseCommand):
    args = '<site_id side_id ...>'
    help = 'Outputs the amount spent in a given category.'

    option_list = BaseCommand.option_list + (
        make_option(
            "--start", action="store", dest="start_date",
            help="Start date.", default=datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)),
        make_option(
            "--end", action="store", dest="end_date",
            help="End date.", default=datetime.now().replace(day=31, hour=23, minute=59, second=59, microsecond=999999)),
        make_option(
            "--accounts", action="append", dest="accounts",
            help="Skip the following accounts."),
    )

    def handle(self, *args, **options):
        totals = {}

        for trans in models.Transaction.objects.all():
            if trans.account_filter(exclude=options['accounts']):
                print "Skipping as in excluded account:", trans
                continue

            if trans.primary_category and trans.primary_category.category_id == "transfer":
                continue

            if len(trans.categories):
                assert len(trans.categories[0].category_id) > 0
                bits = trans.categories[0].category_id.split('/')
            else:
                bits = ['unknown']

            i = 0
            while i < len(bits):
                category = "/".join(bits[0:i+1])
                totals[category] = totals.get(category, 0) + trans.imported_amount
                print trans, category

                i += 1

        i = 0
        while i < 5:
            for category, amount in sorted(totals.items()):
                level = len(category.split('/'))
                if level > i:
                    continue
                print " " * (level*10) + "%-40s %15s" % (category.split('/')[-1], dollar_fmt(amount))
            print "=================================="
            i += 1
