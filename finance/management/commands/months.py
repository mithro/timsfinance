#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
"""
The linker looks for transactions which should be linked together, such as
transfers between accounts.
"""

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from finance import models
from finance.utils import dollar_fmt


class Command(BaseCommand):
    args = '<site_id side_id ...>'
    help = 'Outputs major transactions and difference each month.'

    option_list = BaseCommand.option_list + (
        make_option(
            "--accounts", action="append", dest="accounts",
            help="Skip the following accounts."),
    )

    def handle(self, *args, **options):
        incoming = {}
        outgoing = {}

        for trans in models.Transaction.objects.all():
            if trans.account_filter(exclude=options['accounts']):
                print "Skipping as in excluded account:", trans
                continue

            related = trans.related_transactions(relationship="TRANSFER")
            if related:
                if (not related[0].trans_to.account_filter(exclude=options['accounts']) and
                    not related[0].trans_from.account_filter(exclude=options['accounts'])):
                    print "Skipping transfer:", trans
                    continue

            month = trans.imported_entered_date.month

            if month not in incoming:
                incoming[month] = []
                outgoing[month] = []

            if trans.imported_amount > 0:
                incoming[month].append(trans)

            if trans.imported_amount < 0:
                outgoing[month].append(trans)


        def sort_by_amount(a, b):
            return cmp(a.imported_amount, b.imported_amount)

        print
        print "--------------------------------"

        sum_in_amount = 0
        sum_out_amount = 0
        for month in set(incoming.keys() + outgoing.keys()):
            print month
            print

            in_amount = 0
            for trans in sorted(incoming[month], cmp=sort_by_amount):
                in_amount += trans.imported_amount
            print "Incoming:", dollar_fmt(in_amount)
            for trans in sorted(incoming[month], cmp=sort_by_amount):
                if trans.imported_amount > 50000:
                    print " "*5, "%20s" % dollar_fmt(trans.imported_amount), trans.description
            sum_in_amount += in_amount


            out_amount = 0
            for trans in sorted(outgoing[month], cmp=sort_by_amount):
                out_amount += trans.imported_amount
            print "Outgoing:", dollar_fmt(out_amount)
            for trans in sorted(outgoing[month], cmp=sort_by_amount):
                if trans.imported_amount < -50000:
                    print " "*5, "%20s" % dollar_fmt(trans.imported_amount), trans.description
            sum_out_amount += out_amount

            print
            print "Difference:", dollar_fmt(in_amount+out_amount)
            print "--------------------------------"
        print "Overall difference:", dollar_fmt(sum_in_amount+sum_out_amount)
