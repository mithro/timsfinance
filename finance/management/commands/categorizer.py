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
        for trans in models.Transaction.objects.all():
            categorizers = models.Categorizer.objects.all()

            for categorizer in categorizers:
                if len(categorizer.accounts_set) > 0:
                    if trans.account not in categorizer.accounts_set:
                        print "Skipping categorizer because it's for a different account"
                        continue

                if categorizer.amount_maximum and trans.imported_amount > categorizer.amount_maximum:
                    continue
                if categorizer.amount_minimum and trans.imported_amount < categorizer.amount_minimum:
                    continue

                for regex in categorizer.regex_set:
                    regex_flags = 0
                    if regex.regex_flags:
                        for f in str(regex.regex_flags):
                            regex_flags = regex_flags | getattr(re, f)

                    field_value = getattr(trans, regex.field)

                    matches = True
                    if field_value is None:
                        matches = False
                        continue

                    if regex.regex_type == "S":
                        if not re.search(regex.regex, str(field_value), regex_flags):
                            matches = False

                    elif regex.regex_type == "M":
                        if not re.match(regex.regex, str(field_value), regex_flags):
                            matches = False

                    else:
                        raise TypeError("Unknown regex type %s (%s)." % (regex.type, regex))

                    if matches:
                        break
                else:
                    continue

                if categorizer.category not in trans.suggested_categories.all():
                    print trans, categorizer.category
                    trans.suggested_categories.add(categorizer.category)
