#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import datetime
import cStringIO as StringIO

#from django import unittest as unittest2
from django import test as djangotest

from finance import models
from finance.importers import csv_importer


class SimpleExampleImporter(csv_importer.CSVImporter):
    FIELDS = [
        csv_importer.CSVImporter.DATE,
        csv_importer.CSVImporter.AMOUNT,
        csv_importer.CSVImporter.DESCRIPTION,
        None,
        None]
    DATEFMT = "%d/%m/%Y"
    ORDER = reversed


class RunningExampleImporter(csv_importer.CSVImporter):
    FIELDS = [
        csv_importer.CSVImporter.EFFECTIVE_DATE,
        csv_importer.CSVImporter.ENTERED_DATE,
        csv_importer.CSVImporter.DESCRIPTION,
        csv_importer.CSVImporter.AMOUNT,
        csv_importer.CSVImporter.RUNNING_TOTAL_INC,
        ]
    DATEFMT = "%d/%m/%Y"
    ORDER = reversed


class CSVNoDBTestCase(djangotest.TestCase):
    def test_csv_no_changes(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = "c b a".replace(" ", "\n")

        deletes, inserts = csv_importer.CSVImporter.csv_changes(list, old_data, new_data)
        self.assertFalse(dirty)
        self.assertListEqual([], deletes)
        self.assertListEqual([], inserts)

    def test_csv_one_common(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = "a 1 2 3".replace(" ", "\n")
        deletes, inserts = csv_importer.CSVImporter.csv_changes(list, old_data, new_data)
        self.assertListEqual([], deletes)
        self.assertListEqual([
            ("insert", "1"),
            ("insert", "2"),
            ("insert", "3"),
            ],
            inserts)

    def test_csv_two_common(self):
        old_data = "c b a 1".replace(" ", "\n")
        new_data = "a 1 2 3".replace(" ", "\n")
        deletes, inserts = csv_importer.CSVImporter.csv_changes(list, old_data, new_data)
        self.assertListEqual([], deletes)
        self.assertListEqual([
            ("insert", "2"),
            ("insert", "3"),
            ],
            inserts)

    def test_csv_all_common(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = "c b a 1 2 3".replace(" ", "\n")
        deletes, inserts = csv_importer.CSVImporter.csv_changes(list, old_data, new_data)
        self.assertListEqual([], deletes)
        self.assertListEqual([
            ("insert", "1"),
            ("insert", "2"),
            ("insert", "3"),
            ],
            inserts)

    def test_csv_changes_missing(self):
        old_data = "d c b a".replace(" ", "\n")
        new_data = "c a 1 2 3".replace(" ", "\n") # b missing
        deletes, inserts = csv_importer.CSVImporter.csv_changes(list, old_data, new_data)
        self.assertListEqual([
            ("delete", "a"),
            ("delete", "b"),
            ],
            deletes)
        self.assertListEqual([
            ("insert", "a"),
            ("insert", "1"),
            ("insert", "2"),
            ("insert", "3"),
            ],
            inserts)

    def test_csv_changes_addition(self):
        old_data = "d c a".replace(" ", "\n") # b missing
        new_data = "c b a 1 2 3".replace(" ", "\n")
        deletes, inserts = csv_importer.CSVImporter.csv_changes(list, old_data, new_data)
        self.assertListEqual([
            ("delete", "a"),
            ],
            deletes)
        self.assertListEqual([
            ("insert", "b"),
            ("insert", "a"),
            ("insert", "1"),
            ("insert", "2"),
            ("insert", "3"),
            ],
            inserts)


class CSVTestCase(djangotest.TestCase):
    def setUp(self):
        # Create an account
        currency = models.Currency.objects.create(
            currency_id="money",
            description="Monies!",
            symbol="!",
            )
        site = models.Site.objects.create(
            site_id="site_1",
            username="username",
            password="password",
            importer="importer",
            image="img.png",
            )
        self.account = models.Account.objects.create(
            site=site,
            account_id="account_1",
            short_id="acc1",
            description="",
            currency=currency,
            last_import=datetime.datetime.now(),
            )

    def test_unique(self):
        # Test csv which has a unique identifer....
        pass

    def test_multi(self):
        # -----------------
        csv_basic = StringIO.StringIO("""\
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
""")

        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_basic)

        # -----------------
        # Import the exact same data twice, should cause change


        # -----------------
        csv_basic1 = """\
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""
        csv_basic2 = """\
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction B",""
"""

        # -----------------
        csv_duplicates = """\
16/11/2011,"-0.20","INTNL TRANSACTION FEE",""
15/11/2011,"-0.20","INTNL TRANSACTION FEE",""
15/11/2011,"-0.20","INTNL TRANSACTION FEE",""
14/11/2011,"-0.20","INTNL TRANSACTION FEE",""
"""


        # -----------------
        csv_missing_a = """\
10/11/2011,"0.20","Transaction D",""
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""

        csv_missing_a = """\
10/11/2011,"0.20","Transaction D",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""
        # -----------------
        csv_middle_addition_a = """\
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""

        csv_middle_addition_b = """\
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction D",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""
        # -----------------

    def test_running_total(self):
        csv_normal1 = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
"""
        csv_normal2 = """\
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""
        # -----------------
        csv_running = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""
        # -----------------
        csv_running_missing = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""
        # -----------------
        csv_running_extra = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""
        # -----------------
        csv_running_wrong_order = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""

