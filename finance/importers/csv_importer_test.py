#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import datetime
import cStringIO as SIO

from django import test as djangotest

from finance import models
from finance.importers import csv_importer


class SimpleExampleImporter(csv_importer.CSVImporter):
    FIELDS = [
        csv_importer.FieldList.DATE,
        csv_importer.FieldList.AMOUNT,
        csv_importer.FieldList.DESCRIPTION,
        None]
    DATEFMT = "%d/%m/%Y"
    ORDER = reversed


class RunningExampleImporter(csv_importer.CSVImporter):
    FIELDS = [
        csv_importer.FieldList.EFFECTIVE_DATE,
        csv_importer.FieldList.ENTERED_DATE,
        csv_importer.FieldList.DESCRIPTION,
        csv_importer.FieldList.AMOUNT,
        csv_importer.FieldList.RUNNING_TOTAL_INC,
        ]
    DATEFMT = "%d/%m/%Y"
    ORDER = reversed


class CSVChangesTestCase(djangotest.TestCase):
    def test_csv_empty_first(self):
        old_data = ""
        new_data = "c b a".replace(" ", "\n")

        common, deletes, inserts = csv_importer.csv_changes(
            list, old_data, new_data)
        self.assertListEqual([], common)
        self.assertListEqual([], deletes)
        self.assertListEqual(["c", "b", "a"], inserts)

    def test_csv_empty_second(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = ""

        common, deletes, inserts = csv_importer.csv_changes(
            list, old_data, new_data)
        self.assertListEqual([], common)
        self.assertListEqual(["c", "b", "a"], deletes)
        self.assertListEqual([], inserts)

    def test_csv_no_changes(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = "c b a".replace(" ", "\n")

        common, deletes, inserts = csv_importer.csv_changes(
            list, old_data, new_data)
        self.assertListEqual(["c", "b", "a"], common)
        self.assertListEqual([], deletes)
        self.assertListEqual([], inserts)

    def test_csv_one_common(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = "a 1 2 3".replace(" ", "\n")
        common, deletes, inserts = csv_importer.csv_changes(
            list, old_data, new_data)
        self.assertListEqual([], deletes)
        self.assertListEqual(["1", "2", "3"], inserts)

    def test_csv_two_common(self):
        old_data = "c b a 1".replace(" ", "\n")
        new_data = "a 1 2 3".replace(" ", "\n")
        common, deletes, inserts = csv_importer.csv_changes(
            list, old_data, new_data)
        self.assertListEqual(["a", "1"], common)
        self.assertListEqual([], deletes)
        self.assertListEqual(["2", "3"], inserts)

    def test_csv_all_common(self):
        old_data = "c b a".replace(" ", "\n")
        new_data = "c b a 1 2 3".replace(" ", "\n")
        common, deletes, inserts = csv_importer.csv_changes(
            list, old_data, new_data)
        self.assertListEqual(["c", "b", "a"], common)
        self.assertListEqual([], deletes)
        self.assertListEqual(["1", "2", "3"], inserts)

    def test_csv_changes_missing(self):
        old_data = "d c b a".replace(" ", "\n")
        new_data = "c a 1 2 3".replace(" ", "\n") # b missing
        common, deletes, inserts = csv_importer.csv_changes(
            list, old_data, new_data)
        self.assertListEqual(["c"], common)
        self.assertListEqual(["b", "a"], deletes)
        self.assertListEqual(["a", "1", "2", "3"], inserts)

    def test_csv_changes_missing_big(self):
        old_data = "d c b a 1 2".replace(" ", "\n")
        new_data = "c a 1 2 3".replace(" ", "\n") # b missing
        common, deletes, inserts = csv_importer.csv_changes(
            list, old_data, new_data)
        self.assertListEqual(["c"], common)
        self.assertListEqual(["b", "a", "1", "2"], deletes)
        self.assertListEqual(["a", "1", "2", "3"], inserts)

    def test_csv_changes_addition(self):
        old_data = "d c a".replace(" ", "\n") # b missing
        new_data = "c b a 1 2 3".replace(" ", "\n")
        common, deletes, inserts = csv_importer.csv_changes(
            list, old_data, new_data)
        self.assertListEqual(["c"], common)
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

    maxDiff=None

    def assertTransEqual(self, query, actual):
        self.assertListEqual(
            list((trans.trans_id, trans.removed_by is not None,
                  trans.imported_description) for trans in query),
            actual)

    def assertAllTransEqual(self, actual):
        self.assertTransEqual(
            models.Transaction.objects.all().order_by("id"),
            actual)

    def test_unique(self):
        # Test csv which has a unique identifer....
        pass


    def test_multi(self):
        csv_basic = SIO.StringIO("""\
09/11/2011,"0.20","Cattle",""
09/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")

        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_basic)

        self.assertAllTransEqual(
            [(u"2011-11-09 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-09 00:00:00.000000.1", False, u"Boat"),
             (u"2011-11-09 00:00:00.000000.2", False, u"Cattle")]
            )

    def test_same(self):
        # Import the exact same data twice, should cause no change
        csv_basic1 = SIO.StringIO("""\
09/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_basic1)

        self.assertAllTransEqual(
            [(u"2011-11-09 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-09 00:00:00.000000.1", False, u"Boat")]
            )

        csv_basic2 = SIO.StringIO("""\
09/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        importer.parse_file(self.account, csv_basic2)

        self.assertAllTransEqual(
            [(u"2011-11-09 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-09 00:00:00.000000.1", False, u"Boat")]
            )

    def test_duplicate(self):
        csv_duplicates = SIO.StringIO("""\
16/11/2011,"-0.20","INTNL TRANSACTION FEE",""
15/11/2011,"-0.20","INTNL TRANSACTION FEE",""
15/11/2011,"-0.20","INTNL TRANSACTION FEE",""
14/11/2011,"-0.20","INTNL TRANSACTION FEE",""
""")
        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_duplicates)

        self.assertAllTransEqual(
            [(u"2011-11-14 00:00:00.000000.0", False, u"INTNL TRANSACTION FEE"),
             (u"2011-11-15 00:00:00.000000.0", False, u"INTNL TRANSACTION FEE"),
             (u"2011-11-15 00:00:00.000000.1", False, u"INTNL TRANSACTION FEE"),
             (u"2011-11-16 00:00:00.000000.0", False, u"INTNL TRANSACTION FEE")])

    def test_line_disappear_same_date(self):
        csv_missing_a = SIO.StringIO("""\
07/11/2011,"0.20","Doggy",""
07/11/2011,"0.20","Cattle",""
07/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_missing_a)
        self.assertAllTransEqual(
            [(u"2011-11-07 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-07 00:00:00.000000.1", False, u"Boat"),
             (u"2011-11-07 00:00:00.000000.2", False, u"Cattle"),
             (u"2011-11-07 00:00:00.000000.3", False, u"Doggy")])

        # Cattle disappears
        csv_missing_b = SIO.StringIO("""\
07/11/2011,"0.20","Doggy",""
07/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        importer.parse_file(self.account, csv_missing_b)

        self.assertAllTransEqual(
            [(u"2011-11-07 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-07 00:00:00.000000.1", False, u"Boat"),
             (u"2011-11-07 00:00:00.000000.2", True, u"Cattle"),
             (u"2011-11-07 00:00:00.000000.3", True, u"Doggy"),
             (u"2011-11-07 00:00:00.000000.2", False, u"Doggy")])

    def test_line_disappear_differ_date(self):
        csv_missing_a = SIO.StringIO("""\
10/11/2011,"0.20","Doggy",""
09/11/2011,"0.20","Cattle",""
08/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_missing_a)

        self.assertAllTransEqual(
            [(u"2011-11-07 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-08 00:00:00.000000.0", False, u"Boat"),
             (u"2011-11-09 00:00:00.000000.0", False, u"Cattle"),
             (u"2011-11-10 00:00:00.000000.0", False, u"Doggy")])

        # Cattle disappears
        csv_missing_b = SIO.StringIO("""\
10/11/2011,"0.20","Doggy",""
08/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        importer.parse_file(self.account, csv_missing_b)

        self.assertAllTransEqual(
            [(u"2011-11-07 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-08 00:00:00.000000.0", False, u"Boat"),
             (u"2011-11-09 00:00:00.000000.0", True, u"Cattle"),
             (u"2011-11-10 00:00:00.000000.0", True, u"Doggy"),
             (u"2011-11-10 00:00:00.000000.0", False, u"Doggy")])

    def test_line_appear_same_date(self):
        csv_middle_addition_a = SIO.StringIO("""\
12/11/2011,"0.20","Doggy",""
12/11/2011,"0.20","Boat",""
12/11/2011,"0.20","Apple",""
""")
        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_middle_addition_a)

        self.assertAllTransEqual(
            [(u"2011-11-12 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-12 00:00:00.000000.1", False, u"Boat"),
             (u"2011-11-12 00:00:00.000000.2", False, u"Doggy")])

        # Doggy appears in the middle
        csv_middle_addition_b = SIO.StringIO("""\
12/11/2011,"0.20","Doggy",""
12/11/2011,"0.20","Cattle",""
12/11/2011,"0.20","Boat",""
12/11/2011,"0.20","Apple",""
""")
        importer.parse_file(self.account, csv_middle_addition_b)

        self.assertAllTransEqual(
            [(u"2011-11-12 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-12 00:00:00.000000.1", False, u"Boat"),
             (u"2011-11-12 00:00:00.000000.2", True, u"Doggy"),
             (u"2011-11-12 00:00:00.000000.2", False, u"Cattle"),
             (u"2011-11-12 00:00:00.000000.3", False, u"Doggy")])

    def test_line_appear_differ_date(self):
        csv_middle_addition_a = SIO.StringIO("""\
12/11/2011,"0.20","Doggy",""
10/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        importer = SimpleExampleImporter()
        importer.parse_file(self.account, csv_middle_addition_a)

        self.assertAllTransEqual(
            [(u"2011-11-09 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-10 00:00:00.000000.0", False, u"Boat"),
             (u"2011-11-12 00:00:00.000000.0", False, u"Doggy")])

        # Cattle appears in the middle
        csv_middle_addition_b = SIO.StringIO("""\
12/11/2011,"0.20","Doggy",""
11/11/2011,"0.20","Cattle",""
10/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        importer.parse_file(self.account, csv_middle_addition_b)
        self.assertAllTransEqual(
            [(u"2011-11-09 00:00:00.000000.0", False, u"Apple"),
             (u"2011-11-10 00:00:00.000000.0", False, u"Boat"),
             (u"2011-11-12 00:00:00.000000.0", True, u"Doggy"),
             (u"2011-11-11 00:00:00.000000.0", False, u"Cattle"),
             (u"2011-11-12 00:00:00.000000.0", False, u"Doggy")])


    def test(self):
        # -----------------
        csv_normal1 = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
""")
        csv_normal2 = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
""")
        # -----------------
        csv_running = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
""")
        # -----------------
        csv_running_missing = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
""")
        # -----------------
        csv_running_extra = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
""")
        # -----------------
        csv_running_wrong_order = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
""")

