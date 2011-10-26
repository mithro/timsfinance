#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
"""
The linker looks for transactions which should be linked together, such as
transfers between accounts.
"""

import datetime

from django.core.management.base import BaseCommand, CommandError

from finance import models


class Command(BaseCommand):
    args = '<site_id side_id ...>'
    help = 'Finds transfers between accounts.'

    # Descriptions which match the following should be looked at
    # Anything with "PAYMENT" in it
    # Anything with "TRANSFER" in it
    TRANSFERS = ("PAYMENT", "PMNT", "TRANSFER")

    def associate(self, a, b):
        return models.RelatedTransactions(trans_from=a, trans_to=b, type="A", relationship="TRANSFER")

    def handle(self, *args, **options):
        for trans in models.Transaction.objects.all():
            for desc_match in self.TRANSFERS:
                if desc_match in trans.imported_description.upper():
                    break
            else:
                continue

            print
            print trans

            # If this already had reference set, then done
            if len(trans.reference.all()) > 0:
                print "    ", trans.reference.all()
                continue

            # First attempt to find a transaction 7 days either way with the exact same amount
            q = models.Transaction.objects.all(
                ).filter(imported_entered_date__gt=trans.imported_entered_date-datetime.timedelta(days=7)
                ).filter(imported_entered_date__lt=trans.imported_entered_date+datetime.timedelta(days=7)
                ).filter(imported_amount__exact=-trans.imported_amount
                )
            
            if len(q) == 1:
                r = self.associate(trans, q[0])
                print "    Exact: ", r
                r.save()
                continue
            else:
                print "    Exact: ", q
