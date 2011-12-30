#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import datetime

from finance import models
from finance.helpers import base


class Transfers(base.Helper):
    """
    The linker looks for transactions which should be linked together, such as
    transfers between accounts.
    """

    # Descriptions which match the following should be looked at
    # Anything with "PAYMENT" in it
    # Anything with "TRANSFER" in it
    TRANSFERS = ("PAYMENT", "PMNT", "TRANSFER", "Direct Debit")

    def __init__(self, *args, **kw):
        base.Helper.__init__(self, *args, **kw)

        self.category = models.Category.objects.get(category_id='transfer')

    def associate(self, a, b):
        return base.Helper.associate(self, a, b, relationship="TRANSFER")

    def handle(self, account, trans):
        for desc_match in self.TRANSFERS:
            if desc_match in trans.imported_description.upper():
                break
        else:
            return

        print
        print trans

        # If this already had reference set, then done
        related = trans.related_transactions(relationship="TRANSFER")
        if len(related) > 0:
            print "    ", related
            return

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

            trans.primary_category = self.category
            trans.save()

            q[0].primary_category = self.category
            q[0].save()
        else:
            print "    Exact: ", q

