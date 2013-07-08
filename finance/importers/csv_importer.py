#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
#

"""
Most sites support exporting data as CSV. This base imports a bunch of CSV
formats.

We want to come up with an ID which as some given properties;
 * Changes in transactions on one day do effect transactions on another day (IE
   not ripple through the system).
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

import django.core.exceptions
from django.db import transaction

from finance import models
from finance.utils import dollar_fmt


class NoCommonLines(Warning):
    """No common lines between old CSV file and new CSV file."""
    pass


def csv_changes(order, old_data, new_data):
    """Finds the changes in the two csv files.

    The theory is that you rollback to a common subset and then reply the
    changes from the new file.

    Returns:
        common: List of rows that where common between both data sets.
        deletes: List of rows that need to be rolled back before the
            inserts can be applied.
        inserts: List of rows that need to added to the database.
    """
    old_lines = list(order(
        list(x for x in old_data.split('\n') if len(x) > 0)))
    new_lines = list(order(
        list(x for x in new_data.split('\n') if len(x) > 0)))

    differ = difflib.SequenceMatcher(None, old_lines, new_lines)

    line_changes = differ.get_opcodes()

    # Valid diffs look like the following
    # delete
    # equal
    # (insert|delete|equal)
    # This loop should skip to the bracketed section
    while len(line_changes) > 1 and line_changes[0][0] == "delete":
        line_changes.pop(0)

    equals = []
    while len(line_changes) > 0 and line_changes[0][0] == "equal":
        tag, old_start, old_end, new_start, new_end = line_changes.pop(0)
        for old_i, new_i in zip(
                range(old_start, old_end), range(new_start, new_end)):
            assert old_lines[old_i] == new_lines[new_i]
            equals.append(new_lines[new_i])

    deletes = []  # Transactions which have been removed.
    inserts = []  # Transactions which have been added.
    for tag, old_start, old_end, new_start, new_end in line_changes:
        if tag in ("delete", "replace", "equal"):
            for i in range(old_start, old_end):
                deletes.append(old_lines[i])
        if tag in ("insert", "replace", "equal"):
            for i in range(new_start, new_end):
                inserts.append(new_lines[i])

    # Santity checks
    old_ending = equals+deletes
    assert old_lines[-len(old_ending):] == old_ending, \
        "%s != %s" % (old_lines[-len(old_ending):], old_ending)

    new_ending = equals+inserts
    assert new_lines == new_ending, \
        "%s != %s" % (new_lines, new_ending)

    return equals, deletes, inserts

class FieldList(object):
    """Maps field values from CSV output to field names on a transaction."""

    UNIQUE_ID = '__unique_id'
    DATE = 'imported_entered_date'
    EFFECTIVE_DATE = 'imported_effective_date'
    ENTERED_DATE = 'imported_entered_date'
    DESCRIPTION = 'imported_description'
    AMOUNT = 'imported_amount'
    # Running total *includes* the line being processed transaction
    RUNNING_TOTAL_INC = '__running_total_inc'
    # Running total *excludes* the line being processed transaction
    RUNNING_TOTAL_EXC = '__running_total_exc'

    IGNORE = None

    # Set to avoid lint warnings
    imported_entered_date = None

    def __init__(self, fields_desc, fields_value, datefmt):
        assert len(fields_desc) == len(fields_value), \
            "len(fields_desc) %i != len(fields_value) %i\n%r, %r" % (
                len(fields_desc), len(fields_value),
                fields_desc, fields_value)

        self.fields_desc = fields_desc
        self.fields_raw = fields_value

        assert self.ENTERED_DATE in fields_desc, \
            "Entered date is a required field, please fix the importer."

        for field_name, field_value in zip(fields_desc, fields_value):
            if field_name is None:
                continue

            # Convert dates into datetime objects
            if field_name.endswith("_date"):
                if field_value:
                    field_value = datetime.datetime.strptime(field_value, datefmt)
                else:
                    field_value = None
                setattr(self, field_name, field_value)

            # Convert amount to an int
            elif field_name.endswith("_amount") or field_name.startswith("__running_total_"):
                field_value = re.sub('[^0-9.-]', '', field_value)

                # Negative only allow at front
                assert field_value.find('-') in (-1, 0)

                decimal_point = field_value.split('.')
                if len(decimal_point) == 1:
                    decimal_point.append("00")

                field_value = "".join(decimal_point)
                setattr(self, field_name, int(field_value))

            # Just set it.
            else:
                setattr(self, field_name, field_value)

        assert self.imported_entered_date is not None

    def trans_id(self, date_count):
        """Create the transaction id.

        Needs the date_count if no UNIQUE_ID existing.

        Args:
            date_count is the number of transactions on a given day.
                FIXME(mithro): This is really kudgy but can't figure out a
                better solution at the moment.
        """
        # Get the entered_date information
        if hasattr(self, self.UNIQUE_ID):
            # Get a unique ID for this transaction.
            return getattr(self, self.UNIQUE_ID)
        else:
            # No unique ID, we have to generate a unique ID.
            return "%s.%s" % (
                self.imported_entered_date.strftime("%Y-%m-%d %H:%M:%S.%f"),
                date_count)

    def reconcile(self, date_count):
        if hasattr(self, "__running_total_inc"):
            reconcile = models.Reconciliation()

            assert self.imported_entered_date.microsecond == 0
            reconcile.at = self.imported_entered_date.replace(
                microsecond=date_count)

            reconcile.amount = getattr(self, "__running_total_inc")
            return reconcile
        if hasattr(self, "__running_total_exc"):
            raise NotImplementedError


    def set(self, trans):
        """Copy data from ourselves into the transaction."""
        for field_name in self.fields_desc:
            if field_name is None:
                continue
            if field_name.startswith("__"):
                continue
            setattr(trans, field_name, getattr(self, field_name))

    def __str__(self):
        return "<FieldList %s>" % zip(self.fields_desc, self.fields_raw)


class CSVImporter(object):
    """Base class for importers which import from .csv files."""

    @staticmethod
    def now():
        return datetime.datetime.now

    # Override these attributes
    ###########################################################################
    FIELDS = None
    FIELDS__doc__ = """\
A list of FieldList.fields values describing the order of fields in the CSV
file.
"""
    DATEFMT = None
    DATEFMT__doc__ = """\
Format for dates found in the CSV file.
"""
    ORDER = lambda x: x
    ORDER__doc__ = """\
Function which changes the order in which the transactions are stored to be
oldest first.

ORDER = lambda x: x  -> Order is already oldest first.
ORDER = reversed     -> Order is newest first.
"""

    def filter(self, fields, trans):  # pylint:disable-msg=W0613,R0201
        """Extra filtering that may be needed for the CSV file.

        Args:
            field_list: A FieldList class.
            trans: The populated transaction.

        Returns:
            Boolean, False will cause the transaction not to be saved.
        """
        return True

    ###########################################################################

    @transaction.commit_on_success
    def parse_file(self, account, handle):
        """Parse a CSV file into the database.

        Arguments:
            account: models.Account to import the data too.
            handle: file handle of CSV file to import.

        Results:
            True if new Transactions where imported.
        """
        # ENTERED_DATE is a required field in the CSV
        assert FieldList.ENTERED_DATE in self.FIELDS

        # Step one, we need to find if there is any overlap with previous
        # imports
        new_data = handle.read()

        try:
            old_data_query = models.Imported.objects.all(
                ).filter(account=account
                ).order_by('-at')

            old_data_obj = old_data_query[0]
            old_data = old_data_obj.content
        except IndexError:
            old_data = ""

        common_lines, delete_lines, insert_lines = csv_changes(
            self.ORDER, old_data, new_data)

        # If there are no lines to insert, assume this import was a dud.
        if len(insert_lines) == 0:
            return []

        imported = models.Imported.objects.create(
            account=account,
            content=new_data)

        def annotate(lines):
            """Walk backwards an annotate with number of transactions per day.

            Args:
                lines: Lines suitable for csv.reader

            Yields:
                Number of transactions per day before this transaction.
                FieldList object.
            """
            count = None
            previous_entered_date = None
            for fields in csv.reader(lines):
                field_list = FieldList(self.FIELDS, fields, self.DATEFMT)
                if field_list.imported_entered_date != previous_entered_date:
                    previous_entered_date = field_list.imported_entered_date
                    count = self.date_count_query(
                        account, field_list.imported_entered_date)
                count -= 1
                yield (count, field_list)

        # Roll back the following transactions as they have disapeared in the
        # import. We walk backwards rolling back the newest first.
        amount = 0
        rolledback_trans = []
        for i, field_list in annotate(reversed(delete_lines)):

            # Find the transaction to rollback
            trans_id = field_list.trans_id(i)
            try:
                trans = models.Transaction.objects.get(
                    account=account, trans_id=trans_id, removed_by=None)
            except django.core.exceptions.ObjectDoesNotExist:
                assert False, (
                    "During rollback, could not find transaction.\n"
                    "%s %s\n%s\n" % (account, trans_id, field_list.fields_raw))

            assert trans.imported_fields == repr(field_list.fields_raw), (
                "When rolling back"
                " the found transaction's imported_fields don't match\n"
                "(in db) %s != (imported) %s\n" % (
                    trans.imported_fields, repr(field_list.fields_raw)))

            amount += trans.imported_amount

            # Mark the transaction as deleted
            trans.removed_by = imported
            trans.save()

            rolledback_trans.append(trans.id)

        # If we rolled back some transactions and we have a running total, we
        # need to insert an "rollback" reconciliation.
        if FieldList.RUNNING_TOTAL_INC in self.FIELDS:
            if amount != 0:
                previous_reconcile_id = account.get_reconciliation_order()[-1]
                previous_reconcile = models.Reconciliation.objects.get(
                    id=previous_reconcile_id)

                reconcile = models.Reconciliation()
                reconcile.previous = previous_reconcile
                reconcile.at = self.now()
                reconcile.account = account
                reconcile.imported_by = imported
                reconcile.amount = previous_reconcile.amount - amount
                reconcile.notes = "Reconciliation because of %s transaction rollback." % (
                    rolledback_trans)
                reconcile.save()

        # Mark these as also imported by this
        # Again we walk backwards as there might be many transactions for a
        # day, but only a given number ended up being common between imports.
        for i, field_list in annotate(reversed(common_lines)):

            trans_id = field_list.trans_id(i)
            try:
                trans = models.Transaction.objects.get(
                    account=account, trans_id=trans_id, removed_by=None)
            except django.core.exceptions.ObjectDoesNotExist:
                assert False, (
                    "When checking common, could not find transaction.\n"
                    "%s %s\n%s\n" % (account, trans_id, field_list.fields_raw))

            assert trans.imported_fields == repr(field_list.fields_raw), (
                "When checking common"
                " the found transaction's imported_fields don't match\n"
                "(in db) %s != %s (imported)" % (
                    trans.imported_fields, repr(field_list.fields_raw)))

            trans.imported_also_by.add(imported)
            trans.save()

        # Create any new transactions which have appeared
        inserted_trans = []
        for fields in csv.reader(insert_lines):
            field_list = FieldList(self.FIELDS, fields, self.DATEFMT)

            date_count = self.date_count_query(
                account, field_list.imported_entered_date)

            trans = models.Transaction()
            # Unique key
            trans.account = account
            trans.trans_id = field_list.trans_id(date_count)
            trans.removed_by = None

            # Information about this import
            trans.imported_first_by = imported
            trans.imported_fields = repr(fields)

            # Set the fields from the CSV
            field_list.set(trans)

            # Mangle transactions in a bank specific way
            self.process(trans)

            # If they have running totals, we need to do a reconcile
            reconcile = field_list.reconcile(date_count)
            if reconcile:
                reconcile.account = account
                reconcile.imported_by = imported

                previous_reconcile_id = account.get_reconciliation_order()[-1]
                previous_reconcile = models.Reconciliation.objects.get(
                    id=previous_reconcile_id)

                assert previous_reconcile.amount + trans.imported_amount == reconcile.amount, \
                    "%s + %s != %s\nShould be: %s difference: %s" % (
                        previous_reconcile, trans, reconcile,
                        dollar_fmt(previous_reconcile.amount+trans.imported_amount, account.currency.symbol),
                        dollar_fmt(previous_reconcile.amount+trans.imported_amount-reconcile.amount, account.currency.symbol),
                        )

                reconcile.previous = previous_reconcile

                reconcile.save()
                trans.reconciliation = reconcile

            # Run any module specific transforms.
            if self.filter(field_list, trans):
                # Mark the transaction as active
                trans.state = "Active"
                # Save the transaction
                trans.save()

                inserted_trans.append(trans.id)

        return inserted_trans

    def date_count_query(self, account, entered_date):
        """Get the number of transactions on a given day."""
        return models.Transaction.objects.all(
            ).filter(account=account
            ).filter(imported_entered_date=entered_date
            ).filter(removed_by=None  # Don't count removed transactions
            ).filter(parent_id=None  # Don't count sub-transactions
            ).count()

    def process(self, trans):
        """Do bank specific processing of the transaction.

        Mainly used for extracting extra data from the description,
         * phone numbers,
         * location information,
         * original currency information.
        """
        pass

