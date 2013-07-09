#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import datetime
import cStringIO as SIO

from django import test as djangotest

from finance import models
from finance.importers import csv_importer



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
        self.assertListEqual(["a"], common)
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


class CSVTestCaseBase(djangotest.TestCase):
    def setUp(self):
        # Mock out datetime.datetime.now
        self.now = lambda *args: datetime.datetime.strptime(
            '2012/10/15 12:08:23', '%Y/%m/%d %H:%M:%S')
        csv_importer.CSVImporter.now = self.now

        # Create an account
        currency = models.Currency.objects.create(
            currency_id="money",
            description="Monies!",
            symbol="$",
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
        self.reconcil = models.Reconciliation.objects.create(
            account=self.account,
            previous_id=None,
            at=datetime.datetime.fromtimestamp(0),
            amount=0,
            )
    maxDiff = None

    def assertTransEqual(self, query, actual):
        self.assertListEqual(
            list((trans.trans_id, 
                  trans.removed_by is not None,
                  trans.imported_description,
                  trans.imported_amount,
                  ) for trans in query),
            actual)

    def assertAllTransEqual(self, actual):
        self.assertTransEqual(
            models.Transaction.objects.all().order_by("id"),
            actual)

    def assertReconcileEqual(self, query, actual):
        reconcile = models.Reconciliation.objects.get(
            id=self.account.get_reconciliation_order()[-1])

        reconciliations = [reconcile]
        while reconcile.previous != None:
            reconcile = reconcile.previous
            reconciliations.append(reconcile)

        self.assertListEqual(
            list(tuple(unicode(reconcile).rsplit(" ", 1))
                 for reconcile in reversed(reconciliations)),
            actual)

    def assertAllReconcileEqual(self, actual):
        self.assertReconcileEqual(
            models.Reconciliation.objects.all().order_by("at"),
            actual)


class SimpleImporterTest(CSVTestCaseBase):
    """Test the simple date, amount and description style CSV file."""

    class Importer(csv_importer.CSVImporter):
        FIELDS = [
            csv_importer.FieldList.DATE,
            csv_importer.FieldList.AMOUNT,
            csv_importer.FieldList.DESCRIPTION,
            csv_importer.FieldList.IGNORE,
            ]
        DATEFMT = "%d/%m/%Y"
        ORDER = reversed

    def test_simple(self):
        importer = self.Importer()

        csv_basic = SIO.StringIO("""\
09/11/2011,"0.12","Cattle",""
09/11/2011,"1.23","Boat",""
09/11/2011,"4.56","Apple",""
""")

        self.assertTrue(importer.parse_file(self.account, csv_basic))
        self.assertAllTransEqual([
            (u"2011-11-09 00:00:00.000000.0", False, u"Apple", 456),
            (u"2011-11-09 00:00:00.000000.1", False, u"Boat", 123),
            (u"2011-11-09 00:00:00.000000.2", False, u"Cattle", 12),
            ])

    def test_simple_repeated_import(self):
        importer = self.Importer()

        # Import the exact same data twice, should cause no change
        csv_basic1 = SIO.StringIO("""\
09/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(self.account, csv_basic1))
        self.assertAllTransEqual([
            (u"2011-11-09 00:00:00.000000.0", False, u"Apple", 20),
            (u"2011-11-09 00:00:00.000000.1", False, u"Boat", 20),
            ])

        csv_basic2 = SIO.StringIO("""\
09/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        self.assertFalse(importer.parse_file(self.account, csv_basic2))
        self.assertAllTransEqual([
            (u"2011-11-09 00:00:00.000000.0", False, u"Apple", 20),
            (u"2011-11-09 00:00:00.000000.1", False, u"Boat", 20),
            ])

    def test_simple_duplicate_desc(self):
        importer = self.Importer()

        csv_duplicates = SIO.StringIO("""\
16/11/2011,"-0.20","INTNL FEE",""
15/11/2011,"-0.20","INTNL FEE",""
15/11/2011,"-0.20","INTNL FEE",""
14/11/2011,"-0.20","INTNL FEE",""
""")
        self.assertTrue(importer.parse_file(self.account, csv_duplicates))
        self.assertAllTransEqual([
            (u"2011-11-14 00:00:00.000000.0", False, u"INTNL FEE", -20),
            (u"2011-11-15 00:00:00.000000.0", False, u"INTNL FEE", -20),
            (u"2011-11-15 00:00:00.000000.1", False, u"INTNL FEE", -20),
            (u"2011-11-16 00:00:00.000000.0", False, u"INTNL FEE", -20),
            ])

    def test_simple_disappear_same_date(self):
        importer = self.Importer()

        csv_missing_a = SIO.StringIO("""\
07/11/2011,"0.20","Doggy",""
07/11/2011,"0.20","Cattle",""
07/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(self.account, csv_missing_a))
        self.assertAllTransEqual([
            (u"2011-11-07 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-07 00:00:00.000000.1", False, u"Boat",20),
            (u"2011-11-07 00:00:00.000000.2", False, u"Cattle",20),
            (u"2011-11-07 00:00:00.000000.3", False, u"Doggy",20),
            ])

        # Cattle disappears
        csv_missing_b = SIO.StringIO("""\
07/11/2011,"0.20","Doggy",""
07/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(self.account, csv_missing_b))
        self.assertAllTransEqual([
            (u"2011-11-07 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-07 00:00:00.000000.1", False, u"Boat",20),
            (u"2011-11-07 00:00:00.000000.2", True, u"Cattle",20),
            (u"2011-11-07 00:00:00.000000.3", True, u"Doggy",20),
            (u"2011-11-07 00:00:00.000000.2", False, u"Doggy",20),
            ])

    def test_simple_pogo_same_date(self):
        importer = self.Importer()

        csv_missing_a = SIO.StringIO("""\
07/11/2011,"0.20","Doggy",""
07/11/2011,"0.20","Cattle",""
07/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(self.account, csv_missing_a))
        self.assertAllTransEqual([
            (u"2011-11-07 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-07 00:00:00.000000.1", False, u"Boat",20),
            (u"2011-11-07 00:00:00.000000.2", False, u"Cattle",20),
            (u"2011-11-07 00:00:00.000000.3", False, u"Doggy",20),
            ])

        # Cattle disappears
        csv_missing_b = SIO.StringIO("""\
07/11/2011,"0.20","Doggy",""
07/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(self.account, csv_missing_b))
        self.assertAllTransEqual([
            (u"2011-11-07 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-07 00:00:00.000000.1", False, u"Boat",20),
            (u"2011-11-07 00:00:00.000000.2", True, u"Cattle",20),
            (u"2011-11-07 00:00:00.000000.3", True, u"Doggy",20),
            (u"2011-11-07 00:00:00.000000.2", False, u"Doggy",20),
            ])

        csv_missing_a.seek(0)
        self.assertTrue(importer.parse_file(self.account, csv_missing_a))
        self.assertAllTransEqual([
            (u"2011-11-07 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-07 00:00:00.000000.1", False, u"Boat",20),
            (u"2011-11-07 00:00:00.000000.2", True, u"Cattle",20),
            (u"2011-11-07 00:00:00.000000.3", True, u"Doggy",20),
            (u"2011-11-07 00:00:00.000000.2", True, u"Doggy",20),
            (u"2011-11-07 00:00:00.000000.2", False, u"Cattle",20),
            (u"2011-11-07 00:00:00.000000.3", False, u"Doggy",20),
            ])

        csv_missing_b.seek(0)
        self.assertTrue(importer.parse_file(self.account, csv_missing_b))
        self.assertAllTransEqual([
            (u"2011-11-07 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-07 00:00:00.000000.1", False, u"Boat",20),
            (u"2011-11-07 00:00:00.000000.2", True, u"Cattle",20),
            (u"2011-11-07 00:00:00.000000.3", True, u"Doggy",20),
            (u"2011-11-07 00:00:00.000000.2", True, u"Doggy",20),
            (u"2011-11-07 00:00:00.000000.2", True, u"Cattle",20),
            (u"2011-11-07 00:00:00.000000.3", True, u"Doggy",20),
            (u"2011-11-07 00:00:00.000000.2", False, u"Doggy",20),
            ])

    def test_simple_disappear_differ_date(self):
        importer = self.Importer()

        csv_missing_a = SIO.StringIO("""\
10/11/2011,"0.20","Doggy",""
09/11/2011,"0.20","Cattle",""
08/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(self.account, csv_missing_a))
        self.assertAllTransEqual([
            (u"2011-11-07 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-08 00:00:00.000000.0", False, u"Boat",20),
            (u"2011-11-09 00:00:00.000000.0", False, u"Cattle",20),
            (u"2011-11-10 00:00:00.000000.0", False, u"Doggy",20),
            ])

        # Cattle disappears
        csv_missing_b = SIO.StringIO("""\
10/11/2011,"0.20","Doggy",""
08/11/2011,"0.20","Boat",""
07/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(self.account, csv_missing_b))
        self.assertAllTransEqual([
            (u"2011-11-07 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-08 00:00:00.000000.0", False, u"Boat",20),
            (u"2011-11-09 00:00:00.000000.0", True, u"Cattle",20),
            (u"2011-11-10 00:00:00.000000.0", True, u"Doggy",20),
            (u"2011-11-10 00:00:00.000000.0", False, u"Doggy",20),
            ])

    def test_simple_appear_same_date(self):
        importer = self.Importer()

        csv_middle_addition_a = SIO.StringIO("""\
12/11/2011,"0.20","Doggy",""
12/11/2011,"0.20","Boat",""
12/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(
            self.account, csv_middle_addition_a))
        self.assertAllTransEqual([
            (u"2011-11-12 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-12 00:00:00.000000.1", False, u"Boat",20),
            (u"2011-11-12 00:00:00.000000.2", False, u"Doggy",20),
            ])

        # Doggy appears in the middle
        csv_middle_addition_b = SIO.StringIO("""\
12/11/2011,"0.20","Doggy",""
12/11/2011,"0.20","Cattle",""
12/11/2011,"0.20","Boat",""
12/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(
            self.account, csv_middle_addition_b))
        self.assertAllTransEqual([
            (u"2011-11-12 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-12 00:00:00.000000.1", False, u"Boat",20),
            (u"2011-11-12 00:00:00.000000.2", True, u"Doggy",20),
            (u"2011-11-12 00:00:00.000000.2", False, u"Cattle",20),
            (u"2011-11-12 00:00:00.000000.3", False, u"Doggy",20),
            ])

    def test_simple_appear_differ_date(self):
        importer = self.Importer()

        csv_middle_addition_a = SIO.StringIO("""\
12/11/2011,"0.20","Doggy",""
10/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(
            self.account, csv_middle_addition_a))
        self.assertAllTransEqual([
            (u"2011-11-09 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-10 00:00:00.000000.0", False, u"Boat",20),
            (u"2011-11-12 00:00:00.000000.0", False, u"Doggy",20),
            ])

        # Cattle appears in the middle
        csv_middle_addition_b = SIO.StringIO("""\
12/11/2011,"0.20","Doggy",""
11/11/2011,"0.20","Cattle",""
10/11/2011,"0.20","Boat",""
09/11/2011,"0.20","Apple",""
""")
        self.assertTrue(importer.parse_file(
            self.account, csv_middle_addition_b))
        self.assertAllTransEqual([
            (u"2011-11-09 00:00:00.000000.0", False, u"Apple",20),
            (u"2011-11-10 00:00:00.000000.0", False, u"Boat",20),
            (u"2011-11-12 00:00:00.000000.0", True, u"Doggy",20),
            (u"2011-11-11 00:00:00.000000.0", False, u"Cattle",20),
            (u"2011-11-12 00:00:00.000000.0", False, u"Doggy",20),
            ])


class RunningImporterTest(CSVTestCaseBase):
    """Test running totals in CSV files."""

    class Importer(csv_importer.CSVImporter):
        FIELDS = [
            csv_importer.FieldList.EFFECTIVE_DATE,
            csv_importer.FieldList.ENTERED_DATE,
            csv_importer.FieldList.DESCRIPTION,
            csv_importer.FieldList.AMOUNT,
            csv_importer.FieldList.RUNNING_TOTAL_INC,
            ]
        DATEFMT = "%d/%m/%Y"
        ORDER = reversed

    def test_running_import(self):
        importer = self.Importer()

        reconcile = models.Reconciliation.objects.all().order_by("id")[0]
        reconcile.amount = 2267198
        reconcile.save()

        csv_running = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT VISA (OS),0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL),0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE,-0.50,22671.48
""")
        self.assertTrue(importer.parse_file(
            self.account, csv_running))
        self.assertAllTransEqual([
            (u"2012-01-31 00:00:00.000000.0", False, u"NON REDIATM WITHDRAWAL FEE",-50),
            (u"2012-02-01 00:00:00.000000.0", False, u"REWARD BENEFIT BPAY",30),
            (u"2012-02-01 00:00:00.000000.1", False, u"REWARD BENEFIT VISA (LOCAL)",15),
            (u"2012-02-01 00:00:00.000000.2", False, u"REWARD BENEFIT VISA (OS)",10),
            ])
        self.assertAllReconcileEqual([
            (u"1970-01-01 10:00:00", u"$+22,671.98"),
            (u"2012-01-31 00:00:00", u"$+22,671.48"),
            (u"2012-02-01 00:00:00", u"$+22,671.78"),
            (u"2012-02-01 00:00:00.000001", u"$+22,671.93"),
            (u"2012-02-01 00:00:00.000002", u"$+22,672.03"),
            ])

    def test_running_normal(self):
        importer = self.Importer()

        reconcile = models.Reconciliation.objects.all().order_by("id")[0]
        reconcile.amount = 2267198
        reconcile.save()

        csv_normal1 = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT BPAY,0.30,22672.08
,01/02/2012,REWARD BENEFIT BPAY,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE,-0.50,22671.48
""")
        self.assertTrue(importer.parse_file(
            self.account, csv_normal1))
        self.assertAllTransEqual([
            (u"2012-01-31 00:00:00.000000.0", False, u"NON REDIATM WITHDRAWAL FEE",-50),
            (u"2012-02-01 00:00:00.000000.0", False, u"REWARD BENEFIT BPAY",30),
            (u"2012-02-01 00:00:00.000000.1", False, u"REWARD BENEFIT BPAY",30),
            ])
        self.assertAllReconcileEqual([
            (u"1970-01-01 10:00:00", u"$+22,671.98"),
            (u"2012-01-31 00:00:00", u"$+22,671.48"),
            (u"2012-02-01 00:00:00", u"$+22,671.78"),
            (u"2012-02-01 00:00:00.000001", u"$+22,672.08"),
            ])

        csv_normal2 = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT VISA (OS),0.10,22672.33
,01/02/2012,REWARD BENEFIT VISA (LOCAL),0.15,22672.23
,01/02/2012,REWARD BENEFIT BPAY,0.30,22672.08
,01/02/2012,REWARD BENEFIT BPAY,0.30,22671.78
""")
        self.assertTrue(importer.parse_file(
            self.account, csv_normal2))
        self.assertAllTransEqual([
            (u"2012-01-31 00:00:00.000000.0", False, u"NON REDIATM WITHDRAWAL FEE",-50),
            (u"2012-02-01 00:00:00.000000.0", False, u"REWARD BENEFIT BPAY",30),
            (u"2012-02-01 00:00:00.000000.1", False, u"REWARD BENEFIT BPAY",30),
            (u"2012-02-01 00:00:00.000000.2", False, u"REWARD BENEFIT VISA (LOCAL)",15),
            (u"2012-02-01 00:00:00.000000.3", False, u"REWARD BENEFIT VISA (OS)",10),
            ])
        self.assertAllReconcileEqual([
            (u"1970-01-01 10:00:00", u"$+22,671.98"),
            (u"2012-01-31 00:00:00", u"$+22,671.48"),
            (u"2012-02-01 00:00:00", u"$+22,671.78"),
            (u"2012-02-01 00:00:00.000001", u"$+22,672.08"),
            (u"2012-02-01 00:00:00.000002", u"$+22,672.23"),
            (u"2012-02-01 00:00:00.000003", u"$+22,672.33"),
            ])

    def test_running_missing(self):
        importer = self.Importer()

        reconcile = models.Reconciliation.objects.all().order_by("id")[0]
        reconcile.amount = 2267198
        reconcile.save()

        csv_running = SIO.StringIO("""\
,02/02/2012,REWARD BENEFIT VISA (OS),0.10,22672.03
,02/02/2012,REWARD BENEFIT VISA (LOCAL),0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE,-0.50,22671.48
""")
        self.assertTrue(importer.parse_file(
            self.account, csv_running))
        self.assertAllTransEqual([
            (u"2012-01-31 00:00:00.000000.0", False, u"NON REDIATM WITHDRAWAL FEE",-50),
            (u"2012-02-01 00:00:00.000000.0", False, u"REWARD BENEFIT BPAY",30),
            (u"2012-02-02 00:00:00.000000.0", False, u"REWARD BENEFIT VISA (LOCAL)",15),
            (u"2012-02-02 00:00:00.000000.1", False, u"REWARD BENEFIT VISA (OS)",10),
            ])
        self.assertAllReconcileEqual([
            (u"1970-01-01 10:00:00", u"$+22,671.98"),
            (u"2012-01-31 00:00:00", u"$+22,671.48"),
            (u"2012-02-01 00:00:00", u"$+22,671.78"),
            (u"2012-02-02 00:00:00", u"$+22,671.93"),
            (u"2012-02-02 00:00:00.000001", u"$+22,672.03"),
            ])

        csv_running_missing = SIO.StringIO("""\
,02/02/2012,REWARD BENEFIT VISA (OS),0.10,22671.73
,02/02/2012,REWARD BENEFIT VISA (LOCAL),0.15,22671.63
,31/01/2012,NON REDIATM WITHDRAWAL FEE,-0.50,22671.48
""")
        self.assertTrue(importer.parse_file(
            self.account, csv_running_missing))
        self.assertAllTransEqual([
            (u"2012-01-31 00:00:00.000000.0", False, u"NON REDIATM WITHDRAWAL FEE",-50),
            (u"2012-02-01 00:00:00.000000.0", True, u"REWARD BENEFIT BPAY",30),
            (u"2012-02-02 00:00:00.000000.0", True, u"REWARD BENEFIT VISA (LOCAL)",15),
            (u"2012-02-02 00:00:00.000000.1", True, u"REWARD BENEFIT VISA (OS)",10),
            (u"2012-02-02 00:00:00.000000.0", False, u"REWARD BENEFIT VISA (LOCAL)",15),
            (u"2012-02-02 00:00:00.000000.1", False, u"REWARD BENEFIT VISA (OS)",10),
            ])
        self.assertAllReconcileEqual([
            (u"1970-01-01 10:00:00", u"$+22,671.98"),
            (u"2012-01-31 00:00:00", u"$+22,671.48"),
            (u"2012-02-01 00:00:00", u"$+22,671.78"),
            (u"2012-02-02 00:00:00", u"$+22,671.93"),
            (u"2012-02-02 00:00:00.000001", u"$+22,672.03"),
            (self.now().strftime(u'%Y-%m-%d %H:%M:%S'), u"$+22,671.48"),
            (u"2012-02-02 00:00:00", u"$+22,671.63"),
            (u"2012-02-02 00:00:00.000001", u"$+22,671.73"),
            ])


    def not_yet_working(self):
        csv_running_extra = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT VISA (OS),0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL),0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE,-0.50,22671.48
""")

    def not_yet_working(self):
        csv_running_wrong_order = SIO.StringIO("""\
,01/02/2012,REWARD BENEFIT VISA (OS),0.10,22672.03
,01/02/2012,REWARD BENEFIT BPAY,0.30,22671.78
,01/02/2012,REWARD BENEFIT VISA (LOCAL),0.15,22671.93
,31/01/2012,NON REDIATM WITHDRAWAL FEE,-0.50,22671.48
""")


class DebitCreditImporterTest(CSVTestCaseBase):
    """Test the debit/credit style of CSV files."""

    class Importer(csv_importer.CSVImporter):
        FIELDS = [
            csv_importer.FieldList.DATE,
            csv_importer.FieldList.DEBIT,
            csv_importer.FieldList.CREDIT,
            csv_importer.FieldList.DESCRIPTION,
            ]
        DATEFMT = "%d/%m/%Y"
        ORDER = reversed

    def test_simple(self):
        importer = self.Importer()

        csv_basic = SIO.StringIO("""\
09/11/2011,0.12,,"Cattle"
09/11/2011,,3.45,"Boat"
09/11/2011,6.78,,"Apple"
""")

        self.assertTrue(importer.parse_file(self.account, csv_basic))
        self.assertAllTransEqual([
            (u"2011-11-09 00:00:00.000000.0", False, u"Apple", -678),
            (u"2011-11-09 00:00:00.000000.1", False, u"Boat", 345),
            (u"2011-11-09 00:00:00.000000.2", False, u"Cattle", -12),
            ])

