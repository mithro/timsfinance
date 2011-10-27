#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import datetime
import cStringIO as StringIO

from django.utils import unittest

from finance import models
from finance.importers import commbank


class CommBankNetBankTest(unittest.TestCase):
    fixtures = []

    def testParseFile(self):
        models.Currency.objects.all().delete()

        aud = models.Currency.objects.create(
            currency_id="AUD", description="AUD", symbol="AUD ")
        gbp = models.Currency.objects.create(
            currency_id="GBP", description="GBP", symbol="GBP ")
        usd = models.Currency.objects.create(
            currency_id="USD", description="USD", symbol="USD ")

        site = models.Site.objects.create(
            site_id="1", username="2", importer="3", image="4",
            last_import=datetime.datetime.now())
        account = models.Account.objects.create(
            site=site, account_id="1", description="2", currency=aud,
            last_import=datetime.datetime.now())

        csv = """\
18/10/2011,"+9.23","PREMIUM TOURS LTD        LONDON  N1 0 ##1011           6.00 POUND STERLING",""
19/10/2011,"-3.09","Amazon Services-Kindle   866-321-8851WA ##0911         2.99 US DOLLAR     ",""
20/10/2011,"+5781.77","PAYMENT RECEIVED, THANK YOU",""
20/10/2011,"-3456.90","AUTO PAYMENT - THANK YOU",""
"""
        transactions = commbank.CommBankNetBank.parse_file(
            account, StringIO.StringIO(csv), 0)

        premium_trans = transactions[0]
        amazon_trans = transactions[1]
        payment1_trans = transactions[2]
        payment2_trans = transactions[3]

        self.assertEqual(premium_trans.imported_amount, 923)
        self.assertEqual(premium_trans.imported_description, "PREMIUM TOURS LTD")
        self.assertEqual(premium_trans.imported_original_currency, gbp)
        self.assertEqual(premium_trans.imported_original_amount, 600)
        self.assertEqual(premium_trans.imported_location, "LONDON  N1 0")

        self.assertEqual(amazon_trans.imported_amount, -309)
        self.assertEqual(amazon_trans.imported_description, "Amazon Services-Kindle")
        self.assertEqual(amazon_trans.imported_original_currency, usd)
        self.assertEqual(amazon_trans.imported_original_amount, -299)
        self.assertEqual(amazon_trans.imported_location, "866-321-8851WA")

        self.assertEqual(payment1_trans.imported_amount, 578177)
        self.assertEqual(payment1_trans.imported_description, "PAYMENT RECEIVED, THANK YOU")
        self.assertEqual(payment1_trans.imported_original_currency, None)
        self.assertEqual(payment1_trans.imported_original_amount, None)
        self.assertEqual(payment1_trans.imported_location, "Australia")

        self.assertEqual(payment2_trans.imported_amount, -345690)
        self.assertEqual(payment2_trans.imported_description, "AUTO PAYMENT - THANK YOU")
        self.assertEqual(payment2_trans.imported_original_currency, None)
        self.assertEqual(payment2_trans.imported_original_amount, None)
        self.assertEqual(payment2_trans.imported_location, "Australia")
