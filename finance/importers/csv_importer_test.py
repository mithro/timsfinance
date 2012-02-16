#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import datetime
import cStringIO as SIO

#from django import unittest as unittest2
from django import test as djangotest

from finance import models
from finance.importers import csv_importer


class SimpleExampleImporter(csv_importer.CSVImporter):
    FIELDS = [
        csv_importer.CSVImporter.Fields.DATE,
        csv_importer.CSVImporter.Fields.AMOUNT,
        csv_importer.CSVImporter.Fields.DESCRIPTION,
        None]
    DATEFMT = "%d/%m/%Y"
    ORDER = reversed


class RunningExampleImporter(csv_importer.CSVImporter):
    FIELDS = [
        csv_importer.CSVImporter.Fields.EFFECTIVE_DATE,
        csv_importer.CSVImporter.Fields.ENTERED_DATE,
        csv_importer.CSVImporter.Fields.DESCRIPTION,
        csv_importer.CSVImporter.Fields.AMOUNT,
        csv_importer.CSVImporter.Fields.RUNNING_TOTAL_INC,
        ]
    DATEFMT = "%d/%m/%Y"
    ORDER = reversed


class CSVChangesTestCase(djangotest.TestCase):
    def test_csv_no_changes(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = "c b a".replace(" ", "\n")

        deletes, inserts = csv_importer.csv_changes(list, old_data, new_data)
        self.assertListEqual([], deletes)
        self.assertListEqual([], inserts)

    def test_csv_one_common(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = "a 1 2 3".replace(" ", "\n")
        deletes, inserts = csv_importer.csv_changes(list, old_data, new_data)
        self.assertListEqual([], deletes)
        self.assertListEqual(["1", "2", "3"], inserts)

    def test_csv_two_common(self):
        old_data = "c b a 1".replace(" ", "\n")
        new_data = "a 1 2 3".replace(" ", "\n")
        deletes, inserts = csv_importer.csv_changes(list, old_data, new_data)
        self.assertListEqual([], deletes)
        self.assertListEqual(["2", "3"], inserts)

    def test_csv_all_common(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = "c b a 1 2 3".replace(" ", "\n")
        deletes, inserts = csv_importer.csv_changes(list, old_data, new_data)
        self.assertListEqual([], deletes)
        self.assertListEqual(["1", "2", "3"], inserts)

    def test_csv_changes_missing(self):
        old_data = "d c b a".replace(" ", "\n")
        new_data = "c a 1 2 3".replace(" ", "\n") # b missing
        deletes, inserts = csv_importer.csv_changes(list, old_data, new_data)
        self.assertListEqual(["b", "a"], deletes)
        self.assertListEqual(["a", "1", "2", "3"], inserts)

    def test_csv_changes_addition(self):
        old_data = "d c a".replace(" ", "\n") # b missing
        new_data = "c b a 1 2 3".replace(" ", "\n")
        deletes, inserts = csv_importer.csv_changes(list, old_data, new_data)
        self.assertListEqual(["a"], deletes)
        self.assertListEqual(["b", "a", "1", "2", "3"], inserts)


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
        csv_basic = SIO.StringIO("""\
09/11/2011,"0.20","Cattle",""
09/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")

        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_basic)

        self.assertListEqual(
            list((trans.trans_id, trans.imported_description) for trans in
                  models.Transaction.objects.all().order_by("trans_id")),
            [("2011-11-09 00:00:00.000000.0", "Apple"),
             ("2011-11-09 00:00:00.000000.1", "Boat"),
             ("2011-11-09 00:00:00.000000.2", "Cattle")]
            )

    def test_same(self):
        # Import the exact same data twice, should cause no change
        csv_basic1 = SIO.StringIO("""\
09/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_basic1)

        self.assertListEqual(
            list((trans.trans_id, trans.imported_description) for trans in
                  models.Transaction.objects.all().order_by("trans_id")),
            [("2011-11-09 00:00:00.000000.0", "Apple"),
             ("2011-11-09 00:00:00.000000.1", "Boat")]
            )

        csv_basic2 = SIO.StringIO("""\
09/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        importer.parse_file(self.account, csv_basic2)

        self.assertListEqual(
            list((trans.trans_id, trans.imported_description) for trans in
                  models.Transaction.objects.all().order_by("trans_id")),
            [("2011-11-09 00:00:00.000000.0", "Apple"),
             ("2011-11-09 00:00:00.000000.1", "Boat")]
            )

    def test_duplicate(self):

        # -----------------
        csv_duplicates = SIO.StringIO("""\
16/11/2011,"-0.20","INTNL TRANSACTION FEE",""
15/11/2011,"-0.20","INTNL TRANSACTION FEE",""
15/11/2011,"-0.20","INTNL TRANSACTION FEE",""
14/11/2011,"-0.20","INTNL TRANSACTION FEE",""
""")
        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_duplicates)

        self.assertListEqual(
            list((trans.trans_id, trans.imported_description) for trans in
                  models.Transaction.objects.all().order_by("trans_id")),
            [("2011-11-14 00:00:00.000000.0", "INTNL TRANSACTION FEE"),
             ("2011-11-15 00:00:00.000000.0", "INTNL TRANSACTION FEE"),
             ("2011-11-15 00:00:00.000000.1", "INTNL TRANSACTION FEE"),
             ("2011-11-16 00:00:00.000000.0", "INTNL TRANSACTION FEE")])

    def temp(self):
        return

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

