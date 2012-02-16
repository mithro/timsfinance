#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
#

"""
Most sites support exporting data as CSV. This base imports a bunch of CSV
formats.

We want to come up with an ID which as some given properties;
 * Changes in transactions on one day do not ripple through the system.
 * Multiple imports of the CSV do not duplicate the transactions.
 * Imports of two different CSVs which have overlapping data does not duplicate
   transactions.
 * Two transactions with the same amount and description should not be
   de-duped.

The biggest problem we have is that order of the transactions is the only way
to uniquely identify them but banks don't export the exact transaction
date/time.

<date>-<day row number>

15/11/2011,"-9.56","INTNL TRANSACTION FEE",""
15/11/2011,"-18.27","INTNL TRANSACTION FEE",""
09/11/2011,"0.20","INTNL TRANSACTION FEE",""

2011-11-15-1
2011-11-15-0
2011-11-09-0

------------------------------------------

1	Transaction(Floating)
1.1       Transaction(Split) == 0.25 * T1
1.2       Transaction(Split) == 0.75 * T1
2	Transaction(Floating)
3	--Reconcile == sum(T1+T2+T3)
4	Transaction(Floating)
5	Transaction(Floating)
6	Transaction(Floating)
7	--Reconcile == sum(T4+T5+T6+T7)
8	Transaction(Floating)

CURRENT_BALANCE == LATEST("Reconcile").amount
  + SUM(SELECT amount FROM transactions WHERE type IS "Floating" AND serial > LATEST("Reconcile").serial)
"""

import csv
import datetime
import difflib
import re
import warnings

from django.db import transaction

from finance import models


class NoCommonLines(Warning):
    pass



class CSVImporter(object):

    UNIQUE_ID = '__unique_id'
    DATE = 'imported_entered_date'
    EFFECTIVE_DATE = 'imported_effective_date'
    ENTERED_DATE = 'imported_entered_date'
    DESCRIPTION = 'imported_description'
    AMOUNT = '__amount'
    # Running total *includes* the line being processed transaction
    RUNNING_TOTAL_INC = '__running_total_inc'
    # Running total *excludes* the line being processed transaction
    RUNNING_TOTAL_EXC = '__running_total_exc'

    def filter(self, fields, trans):
        pass

    @staticmethod
    def csv_changes(order, old_data, new_data):
        """Finds the changes in the two csv files.

        Returns:
            deletes: List of rows that need to be rolled back before the
                inserts can be applied.
                (These are in the correct order needed to rollback, IE latest
                first.)
            inserts: List of rows that need to added to the database.
                (These are in the correct order needed to insert, IE earlier
                first.)
        """

        old_lines = list(order(old_data.split('\n')))
        new_lines = list(order(new_data.split('\n')))

        differ = difflib.SequenceMatcher(None, old_lines, new_lines)

        common = differ.find_longest_match(0, -1, 0, -1)
        if common.size == 0:
            warnings.warn(
                "No common lines found between imports," +
                    " assuming all lines are new.",
                NoCommonLines)

        line_changes = differ.get_opcodes()
        while len(line_changes) > 0:
            tag, i1, i2, j1, j2 = line_changes[0]
            if i2 <= common.a or j1 <= common.b:
                # Make sure that everything before the common section is just
                # deletes of equals, no inserts.
                assert line_changes[0][0] in ("delete", "equal")
                line_changes.pop(0)
                continue
            break

        dirty = False

        deletes = []
        inserts = []
        for tag, i1, i2, j1, j2 in line_changes:
            if tag == "equal":
                dirty = True
                for i in range(i1, i2):
                    deletes.append(('delete', old_lines[i]))

        for tag, i1, i2, j1, j2 in line_changes:
            if tag in ("delete", "replace"):
                for i in range(i1, i2):
                    deletes.append(('delete', old_lines[i]))
            if tag in ("insert", "replace", "equal"):
                for i in range(j1, j2):
                    inserts.append(('insert', new_lines[i]))

        return dirty, list(reversed(deletes)), inserts

    @transaction.commit_on_success
    def parse_file(self, account, handle):
        FIELDS = self.FIELDS
        DATEFMT = self.DATEFMT

        # ENTERED_DATE is a required field in the CSV
        assert self.ENTERED_DATE in FIELDS

        # Step one, we need to find if there is any overlap with previous imports
        new_data = handle.read()
        old_data_query = models.Imported.objects.all()
        old_data_query = old_data_query.filter(account=account)
        old_data_query = old_data_query.order_by('date')

        try:
            old_data_obj = old_data_query[0]
            old_data = old_data_obj.content
        except IndexError:
            old_data = ""

        merged_data = self.only_new_lines(old_data, new_data)
        lines = self.ORDER(list(csv.reader(StringIO.StringIO(merged_data))))

        date_counts = {}


        for fields in []:
            # Get the entered_date information
            entered_date = fields[FIELDS.index(self.ENTERED_DATE)]
            entered_date_dt = datetime.datetime.strptime(entered_date, DATEFMT)

            try:
                # Get a unique ID for this transaction.
                id_index = FIELDS.index(self.UNIQUE_ID)
                trans_id = fields[id_index]
            except ValueError:
                # No unique ID, we have to generate a unique ID.
                date_count = date_counts.get(entered_date_dt, 0)
                date_counts[entered_date] = date_count + 1

                trans_id = "%s.%s" % (entered_date_dt.strftime("%Y%m%d%H%M%S.%f"), date_count)

            # Try and find an existing transaction, or create a new one
            try:
                trans = models.Transaction.objects.get(account=account, trans_id=trans_id)
            except models.Transaction.DoesNotExist:
                trans = models.Transaction(account=account, trans_id=trans_id)

            # Set the fields on the transactions
            for field_index, field_name in enumerate(FIELDS):
                if not field_name:
                    continue

                field_value = fields[field_index]

                # Just a basic set
                if not field_name.startswith("__"):
                    if field_name.endswith("date"):
                        field_value = datetime.datetime.strptime(entered_date, DATEFMT)

                    setattr(trans, field_name, field_value)

                # We have running totals, so we can do the reconcilation per transaction.
                elif field_name == "__amount":
                    field_value = re.sub('[^0-9]', '', field_value)
                    trans.imported_amount = int(field_value)

                elif field_name == "__running_total_inc":
                    if trans.reconcile is None:
                        reconcile = models.Reconciliation(
                            date = entered_date,
                            previous_id = previous_reconciliation,
                            )
                        reconcile.save()
                        trans.reconcile = reconcile
                elif field_name == "__running_total_inc":
                    raise NotImplemented()

            # Run any module specific transforms.
            self.filter(fields, trans)
            trans.save()
