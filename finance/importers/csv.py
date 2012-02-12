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

class CSVImporter(object):

    DATE = 'entered_date'
    EFFECTIVE_DATE = 'effective_date'
    ENTERED_DATE = 'entered_date'
    DESCRIPTION = 'imported_description'
    AMOUNT = 'imported_amount'
    # Running total *includes* the line being processed transaction
    RUNNING_TOTAL_INC = '__running_total_inc'
    # Running total *excludes* the line being processed transaction
    RUNNING_TOTAL_EXC = '__running_total_exc'

    #19/11/2011,"-423.00","JETSTAR                  MELBOURNE","","-6314.84"
    COMMBANK_FIELDS = [
        DATE, AMOUNT, DESCRIPTION, None, None]
    COMMBANK_DATEFMT = "%Y/%m/%d"
    COMMBANK_ORDER = reversed  # Oldest first

    #01/02/2012,02/02/2012,IB TFR to 032090  793177 ,-60.00,22512.03
    #,30/01/2012,BPAY COMMONWEALTH CARDS ,-5389.66,37370.08
    PCCU = [
        EFFECTIVE_DATE, ENTERED_DATE, DESCRIPTION, AMOUNT, TOTAL,
        ]
    PCCU_DATEFMT = "%Y/%m/%d"
    PCCU_ORDER = reversed  # Oldest first

    def filter(self, fields, trans):
        pass

    def parse_file(self, account, handle):
        FIELDS = self.PCCU
        DATEFMT = self.PCCU_DATEFMT
        ORDER = self.PCCU_ORDER

        # ENTERED_DATE is a required field in the CSV
        assert self.ENTERED_DATE in FIELDS

        previous_reconciliation_query = Reconciliation.objects.all()
        previous_reconciliation_query.filter(account__eq = account)

        date_counts = {}
        for fields in ORDER(csv.reader(handle)):
            # Get the entered_date information
            entered_date = fields[FIELDS.indexof(self.ENTERED_DATE)]
            entered_date_dt = datetime.datetime.strptime(entered_date, DATEFMT)

            # Get a unique ID for this transaction.
            id_index = FIELDS.indexof(self.UNIQUE_ID)
            if id_index == -1:
                # We have to generate a unqiue ID.

                date_count = date_counts.get(entered_date_dt, 0)
                date_counts[entered_date] = date_count + 1

                unique_id = "%s.%s" % (entered_date_dt.strftime("%Y%m%d%H%M%S.%f"), date_count)
            else:
                unique_id = fields[id_index]

            # Try and find an existing transaction, or create a new one
            try:
                trans = models.Transaction.objects.get(account=account, trans_id=trans_id)
            except models.Transaction.DoesNotExist:
                trans = models.Transaction(account=account, trans_id=trans_id)

            # Set the fields on the transactions
            for field_index, field_name in FIELDS:
                if not field_name:
                    continue

                # Just a basic set
                if not field_name.startswith("__"):
                    field_value = fields[field_index]
                    setattr(trans, field_name, field_value)

                # We have running totals, so we can do the reconcilation per transaction.
                elif field_name == "__running_total_inc":
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

