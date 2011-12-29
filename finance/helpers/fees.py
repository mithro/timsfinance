#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
"""
The linker looks for transactions which should be linked together, such as
transfers between accounts.
"""

import math
import re
import datetime

from finance import models
from finance.helpers import base


class Fees(base.Helper):
    """Finds fees associated with transactions."""

    def __init__(self, *args, **kw):
        base.Helper.__init__(self, *args, **kw)

    def associate(self, fee, a, b):
        return base.Helper.associate(self, a, b, relationship="FEE", fee=fee)

    def handle(self, account, trans):
        for fee in account.fee_set.all():

            # Check the regex patterns match
            for regex in fee.regex.all():
                if regex.match(trans):
                    break
            else:
                continue

            # Check this association hasn't already been created
            fee_already = trans.related_transactions(relationship="FEE", fee=fee)
            if len(fee_already) > 0:
                print "Fee already associated for %60s ---> %s" % (trans, fee_already[0])
                continue

            # Search for a suitable transaction
            q = models.Transaction.objects.all(
                ).filter(account__exact=account
                ).filter(imported_entered_date__gte=trans.imported_entered_date
                ).filter(imported_entered_date__lt=trans.imported_entered_date+datetime.timedelta(days=2)
                ).order_by("imported_entered_date"
                ).exclude(trans_id__exact=trans.trans_id
                )

            if fee.type == '%':
                percent = float(fee.amount[:-1])/100
                fee_amount = -abs(math.floor(trans.imported_amount * percent))

                q = q.filter(imported_amount__gte=fee_amount-2
                    ).filter(imported_amount__lte=fee_amount+2
                    )

            elif fee.type == "F":
                fee_amount = -int(fee.amount)
                q = q.filter(imported_amount__exact=fee_amount)

            else:
                raise TypeError("Unknown fee type %s (%s)." % (regex.type, regex))

            for fee_trans in q:
                fee_related = fee_trans.related_transactions(relationship="FEE", fee=fee)
                if len(fee_related) == 0:
                    print "Associating %-30s (%10i) with %s (%8i)" % (
                        trans.imported_description, trans.imported_amount,
                        fee_trans.imported_description, fee_trans.imported_amount)
                    self.associate(fee, trans, fee_trans).save()
                    return
                else:
                    print "Fee associated with other transaction", fee_related
            else:
                print "Found no fee transaction for", trans
