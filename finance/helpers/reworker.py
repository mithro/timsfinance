#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
"""
The reworker looks for things in descriptions and locations which can be
reworked to look better.

Some examples of things that it looks for are:
  * US Phone numbers
  * State/Province abbreviations for USA/Canada/Australia
  * Extra spaces, commas and such
"""

import csv
import math
import re
import datetime
import os.path

from finance import models
from finance.helpers import base


STATE_ABBR = {}
for fullname, abbr, country in csv.reader(file(os.path.join(os.path.dirname(__file__), "reworker", "states.csv"))):
    if not country in STATE_ABBR:
        STATE_ABBR[country] = {}
    STATE_ABBR[country][abbr] = fullname

CURRENCY_TO_COUNTRY = {
    "AUD": "Australia",
    "CAD": "Canada",
    "USD": "USA",
    "SGP": "Singapore",
    }


class LocationFixer(base.Helper):
    """Finds common problems with location information and corrects it."""

    def handle(self, account, trans):
        for possible in "imported_location", "imported_description":
            override = possible.replace("imported", "override")

            orig_value = getattr(trans, possible)
            value = orig_value

            # Look for things that look like US phone numbers and rewrite them
            # 0415-291-0224
            # 08775239849
            # 8775239849
            # 877-5239849
            # 877-5239-849
            value = re.sub(
                "[01]?([0-9][0-9][0-9])-?([0-9][0-9][0-9])-?([0-9][0-9][0-9][0-9])([^0-9])",
                r"ph:+1-\1-\2-\3 \4",
                value)

            # Look for things that look like state codes - check the currency
            currency = trans.imported_original_currency
            if currency is None:
                currency = trans.account.currency

            if currency.currency_id in CURRENCY_TO_COUNTRY:
                country = CURRENCY_TO_COUNTRY[currency.currency_id]
                if country in STATE_ABBR:
                    abbr = STATE_ABBR[country]
                    for abbr, fullname in abbr.items():
                            value = re.sub(' (%s) ?$' % abbr, ', %s, %s ' % (fullname, country), value)

            # Multiple space fixer
            while value != re.sub("  ", " ", value):
                value = re.sub("  ", " ", value)

            # Clean up any extra commas
            while value != re.sub(' ,', ',', value):
                value = re.sub(' ,', ',', value)

            value = re.sub(',, $', '', value)
            value = re.sub(', $', '', value)
            value = re.sub('^ *,', '', value)

            if orig_value != value and getattr(trans, override) == None:
                print account, "%40s" % trans
                print repr(orig_value)
                print repr(value)
                print repr(getattr(trans, override))
                print
                setattr(trans,override, value)

        trans.save()
