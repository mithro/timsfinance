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
    """No common lines between old CSV file and new CSV file."""
    pass


def csv_changes(order, old_data, new_data):
    """Finds the changes in the two csv files.

    The theory is that you rollback to a common subset and then reply the
    changes from the new file.

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
        tag, old_start, old_end, new_start, new_end = line_changes[0]
        if old_end <= common.a or new_start <= common.b:
            # Make sure that everything before the common section is just
            # deletes or equals, no inserts.
            assert line_changes[0][0] in ("delete", "equal")
            line_changes.pop(0)
            continue
        break

    deletes = []
    inserts = []
    for tag, old_start, old_end, new_start, new_end in line_changes:
        if tag == "equal":
            for i in range(old_start, old_end):
                deletes.append(old_lines[i])

    for tag, old_start, old_end, new_start, new_end in line_changes:
        if tag in ("delete", "replace"):
            for i in range(old_start, old_end):
                deletes.append(old_lines[i])
        if tag in ("insert", "replace", "equal"):
            for i in range(new_start, new_end):
                inserts.append(new_lines[i])

    return list(reversed(deletes)), inserts

class FieldList(object):
    """Maps field values from CSV output to field names in the description."""

    def __init__(self, fields_desc, fields_value, datefmt):
        assert len(fields_desc) == len(fields_value), \
            "len(fields_desc) %i != len(fields_value) %i" % (
                len(fields_desc), len(fields_value))

        self.fields_desc = fields_desc

        assert CSVImporter.Fields.ENTERED_DATE in fields_desc, \
            "Entered date is a required field, please fix the importer."

        for field_name, field_value in zip(fields_desc, fields_value):
            if field_name is None:
                continue

            # Convert dates into datetime objects
            if field_name.endswith("_date"):
                field_value = datetime.datetime.strptime(field_value, datefmt)
                setattr(self, field_name, field_value)

            # Convert amount to an int
            elif field_name.endswith("_amount"):
                field_value = re.sub('[^0-9]', '', field_value)
                setattr(self, field_name, int(field_value))

            elif field_name == "__running_total_inc":
                raise NotImplementedError()

            elif field_name == "__running_total_inc":
                raise NotImplementedError()

            # Just set it.
            else:
                setattr(self, field_name, field_value)

    def trans_id(self, date_count):
        """Create the transaction id.

        Needs the date_count if no UNIQUE_ID existing.
        FIXME(mithro): This is really kudgy but can't figure out a better
            solution at the moment.
        """
        # Get the entered_date information
        if hasattr(self, CSVImporter.Fields.UNIQUE_ID):
            # Get a unique ID for this transaction.
            return getattr(self, CSVImporter.Fields.UNIQUE_ID)
        else:
            # No unique ID, we have to generate a unique ID.
            return "%s.%s" % (
                self.imported_entered_date.strftime("%Y-%m-%d %H:%M:%S.%f"),
                date_count)

    def set(self, trans):
        """Copy data from ourselves into the transaction."""
        for field_name in self.fields_desc:
            if field_name is None:
                continue
            if field_name.startswith("__"):
                continue
            setattr(trans, field_name, getattr(self, field_name))


class CSVImporter(object):
    """Base class for importers which import from .csv files."""

    class Fields(object):
        """Fields which can be imported."""
        def __init__(self):
            raise SyntaxError('Holder object, do not construct!')

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

    # Override these attributes
    ###########################################################################
    FIELDS = None
    FIELDS__doc__ = """\
A list of CSVImporter.fields values describing the order of fields in the CSV
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
            A list of transaction IDs which where changed.
        """
        # ENTERED_DATE is a required field in the CSV
        assert self.Fields.ENTERED_DATE in self.FIELDS

        # Step one, we need to find if there is any overlap with previous
        # imports
        new_data = handle.read()

        try:
            old_data_query = models.Imported.objects.all(
                ).filter(account=account
                ).order_by('date')

            old_data_obj = old_data_query[0]
            old_data = old_data_obj.content
        except IndexError:
            old_data = ""

        delete_lines, insert_lines = csv_changes(self.ORDER, old_data, new_data)

        # If there are no lines to insert, assume this import was a dud...
        if len(insert_lines) == 0:
            return

        models.Imported.objects.create(
            account=account,
            content=new_data)

        # Mark any transaction which has disappeared as deleted
        for fields in csv.reader(delete_lines):
            field_list = FieldList(self.FIELDS, fields, self.DATEFMT)
            self.delete_trans(account, field_list)

        # Create any new transactions which have appeared
        for fields in csv.reader(insert_lines):
            field_list = FieldList(self.FIELDS, fields, self.DATEFMT)
            self.insert_trans(account, field_list)

    def date_count_query(self, account, field_list):
        return models.Transaction.objects.all(
            ).filter(account=account
            ).filter(imported_entered_date=field_list.imported_entered_date
            ).exclude(trans_id__endswith=".deleted"
            ).count()

    def delete_trans(self, account, field_list):
        date_count = self.date_count_query(account, field_list) - 1
        trans_id = field_list.trans_id(date_count)

        # Get the existing transaction
        trans = models.Transaction.objects.get(
            account=account, trans_id=trans_id)

        # Mark the transaction as deleted
        trans.trans_id += ".deleted"
        # Save the transaction
        trans.save()

    def insert_trans(self, account, field_list):
        date_count = self.date_count_query(account, field_list)
        trans_id = field_list.trans_id(date_count)

        # Try and find an existing transaction, or create a new one
        try:
            trans = models.Transaction.objects.get(
                account=account, trans_id=trans_id)
        except models.Transaction.DoesNotExist:
            trans = models.Transaction()
            trans.account=account
            trans.trans_id=trans_id

        field_list.set(trans)

        # Run any module specific transforms.
        if self.filter(field_list, trans):
            # Mark the transaction as active
            trans.state = "Active"
            # Save the transaction
            trans.save()
