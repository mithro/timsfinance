#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
"""
The linker looks for transactions which should be linked together, such as
transfers between accounts.
"""

import datetime
import logging
import math
import re

from finance import models
from finance.helpers import base


class Categorizer(base.Helper):
    """Automatically categorizes transactions."""

    def __init__(self, *args, **kw):
        base.Helper.__init__(self, *args, **kw)

        self.categorizers = models.Categorizer.objects.all()

    def handle(self, account, trans):
        for categorizer in self.categorizers:
            if len(categorizer.accounts_set) > 0:
                if account not in categorizer.accounts_set:
                    logging.info("Skipping categorizer because it's for a different account")
                    continue

            # Check the amount matches (if an amount is imported)
            if categorizer.amount_maximum and trans.imported_amount > categorizer.amount_maximum:
                continue
            if categorizer.amount_minimum and trans.imported_amount < categorizer.amount_minimum:
                continue

            # Check the regex patterns match
            for regex in categorizer.regex_set:
                if regex.match(trans):
                    break
            else:
                continue

            if categorizer.category not in trans.suggested_categories.all():
                logging.info("Adding category %s", categorizer.category)
                trans.suggested_categories.add(categorizer.category)
                trans.save()
