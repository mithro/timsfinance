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
                field, regex = fee.regex.split(':', 1)

                for trans in account.transaction_set.all():
                    print
                    fee_already = trans.related_transactions(relationship="FEE", fee=fee)
                    if len(fee_already) > 0:
                        print "Fee already associated for ", trans, fee_already[0]
                        continue

                    field_value = getattr(trans, field)
                    if field_value is None:
                        continue

                    if not re.match(regex, str(field_value)):
                        continue

                    if fee.type == '%':
                        percent = float(fee.amount[:-1])/100
                        fee_amount = -abs(math.floor(trans.imported_amount * percent))

                    q = models.Transaction.objects.all(
                        ).filter(account__exact=account
                        ).filter(imported_entered_date__gte=trans.imported_entered_date
                        ).filter(imported_entered_date__lt=trans.imported_entered_date+datetime.timedelta(days=2)
                        ).filter(imported_amount__gte=fee_amount-1
                        ).filter(imported_amount__lte=fee_amount+1
                        ).order_by("imported_entered_date")

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
