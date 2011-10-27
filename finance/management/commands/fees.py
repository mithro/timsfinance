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

from django.core.management.base import BaseCommand, CommandError

from finance import models


class Command(BaseCommand):
    args = '<site_id side_id ...>'
    help = 'Finds fees associated with transactions'

    def associate(self, fee, a, b):
        return models.RelatedTransaction(trans_from=a, trans_to=b, type="A", relationship="FEE", fee=fee)

    def handle(self, *args, **options):
        for account in models.Account.objects.all():
            for fee in account.fee_set.all():
                print
                print "Account:", account, "Fee:", fee
                print "----------------------------------------"

                for trans in account.transaction_set.all():
                    matches = True
                    for regex in fee.regex.all():
                        field_value = getattr(trans, regex.field)
                        if field_value is None:
                            matches = False
                            continue

                        if regex.regex_type == "S":
                            if not re.search(regex.regex, str(field_value)):
                                matches = False

                        elif regex.regex_type == "M":
                            if not re.match(regex.regex, str(field_value)):
                                matches = False
                        else:
                            raise TypeError("Unknown regex type %s (%s)." % (regex.type, regex))

                    if not matches:
                        continue

                    fee_already = trans.related_transactions(relationship="FEE", fee=fee)
                    if len(fee_already) > 0:
                        print "Fee already associated for %60s ---> %s" % (trans, fee_already[0])
                        continue

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
                            break
                        else:
                            print "Fee associated with other transaction", fee_related
                    else:
                        print "Found no fee transaction for", trans
