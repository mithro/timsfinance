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
        incoming = {}
        outgoing = {}

        accounts = []
        for account_id in args:
            try:
                accounts.append(models.Account.objects.get(account_id=account_id))
            except models.Account.DoesNotExist:
                raise CommandError('Account "%s" does not exist' % account_id)

        for trans in models.Transaction.objects.all():
            month = trans.imported_entered_date.month

            if accounts and trans.account not in accounts:
                continue

            if trans.related_transactions(relationship="TRANSFER"):
                print "Skipping transfer:", trans
                continue

            if month not in incoming:
                incoming[month] = []
                outgoing[month] = []

            if trans.imported_amount > 0:
                incoming[month].append(trans)

            if trans.imported_amount < 0:
                outgoing[month].append(trans)


        sum_in_amount = 0
        sum_out_amount = 0
        for month in set(incoming.keys() + outgoing.keys()):
            print month
            print

            in_amount = 0
            for trans in incoming[month]:
                in_amount += trans.imported_amount
            print "Incoming:", dollar_fmt(in_amount)
            for trans in incoming[month]:
                if trans.imported_amount > 50000:
                    print " "*5, "%20s" % dollar_fmt(trans.imported_amount), trans.description
            sum_in_amount += in_amount


            out_amount = 0
            for trans in outgoing[month]:
                out_amount += trans.imported_amount
            print "Outgoing:", dollar_fmt(out_amount)
            for trans in outgoing[month]:
                if trans.imported_amount < -50000:
                    print " "*5, "%20s" % dollar_fmt(trans.imported_amount), trans.description
            sum_out_amount += out_amount

            print
            print "Difference:", dollar_fmt(in_amount+out_amount)
            print "--------------------------------"
        print "Overall difference:", dollar_fmt(sum_in_amount+sum_out_amount)
