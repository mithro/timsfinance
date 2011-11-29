#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
"""
The linker looks for transactions which should be linked together, such as
transfers between accounts.
"""

from django.core.management.base import BaseCommand, CommandError

from finance import models
from finance.utils import dollar_fmt


class Command(BaseCommand):
    args = '<site_id side_id ...>'
    help = 'Finds fees associated with transactions'

    def handle(self, *args, **options):
        totals = {}

        for trans in models.Transaction.objects.all():

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
