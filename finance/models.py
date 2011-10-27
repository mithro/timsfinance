#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import locale

from django.db import models
from django.db.models import Q
from django.contrib import admin

from finance.utils import dollar_display

###############################################################################

class RegexForField(models.Model):
    """A regex which should be applied to a given field on a transaction.

    This is used by both the Categorizer and the Fee systems.
    """
    field = models.CharField(max_length=255)
    regex = models.CharField(max_length=255)
    description = models.CharField(max_length=255)

    REGEX_TYPE = (
        ('S', 'Search'),
        ('M', 'Match'),
    )
    regex_type = models.CharField(max_length=1, choices=REGEX_TYPE)

    def __unicode__(self):
        return "%s %s %s" % (self.field, self.regex_type, self.regex)

class RegexForFieldAdmin(admin.ModelAdmin):
    list_display = ('description', 'field', 'regex', 'regex_type')

###############################################################################

class Currency(models.Model):
    """Currency is a form of units an account can be in.

    It might be a real currency like "Australia Dollar" or a fake currency
    liked "United Milage Plus Miles" or "Commonwealth Bank Awards Points".

    The CurrencyConversion table tracks how to convert from one currency to
    another.
    """
    currency_id = models.CharField(max_length=200, primary_key=True)
    description = models.CharField(max_length=200)
    symbol = models.CharField(max_length=3)

    def __unicode__(self):
        return self.currency_id

    class Meta:
        verbose_name_plural = "currencies"

class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('currency_id', 'description')

###############################################################################

class Category(models.Model):
    """Category for transactions.

    Categories are built in a tree like structure.

    IE
      medical
      medical/dental
      medical/emergency
    """
    category_id = models.CharField(max_length=200, primary_key=True)
    description = models.CharField(max_length=200)

    # Categories are built in a tree structure, they can be part of another category.
    parent = models.ForeignKey('self', null=True, blank=True)

    def __unicode__(self):
        return self.category_id

    class Meta:
        verbose_name_plural = "categories"

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'description')

###############################################################################

class Site(models.Model):
    """Sites are places which have accounts.

    Normally they are banks, but could be other things like brokers or similar.
    """
    site_id = models.CharField(max_length=200, primary_key=True)
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=200, null=True, blank=True)

    # The python class name for the tool which imports
    importer = models.CharField(max_length=200)
    image = models.URLField(max_length=1000)
    # Latest import time that occured
    last_import = models.DateTimeField('last import')

    def __unicode__(self):
        return self.site_id

class SiteAdmin(admin.ModelAdmin):
    list_display = ('site_id', 'username', 'last_import')
    list_filter = ('importer',)

###############################################################################

class Account(models.Model):
    """An account, associated with a "site" which is normally a bank."""
    site = models.ForeignKey('Site')
    account_id = models.CharField(max_length=200)

    description = models.CharField(max_length=255)
    currency = models.ForeignKey('Currency')

    # Latest import time that occured
    imported_last = models.DateTimeField('last import')

    @property
    def latest_transaction(self):
        q = Transaction.object.get(account=self)
        q.order_by("imported_effective_date")

    @property
    def current_balance(self):
        # starting_balance + sum(transactions.imported_amount)
        pass

    def __unicode__(self):
        return "%s (%s)" % (self.account_id, self.description)

    class Meta:
        unique_together = (("site", "account_id"))

class AccountAdmin(admin.ModelAdmin):
    list_display = ('site', 'account_id', 'description', 'currency', 'imported_last', 'current_balance')
    list_filter = ('site',)

###############################################################################

class Fee(models.Model):
    """Fee model describes fees which apply to an account.

    This is used in two ways:
      * by the Fees linker to connect Fee transactions with the transactions
        which caused them.
      * by the Fee spliter to split out the Fee cost from a transaction.
    """
    # Account this fee is applied too
    account = models.ForeignKey('Account')

    # Description
    description = models.CharField(max_length=255)

    # Regex to find transactions which have Fees applied to them.
    # This is an *AND* IE the transaction must match every regex given.
    regex = models.ManyToManyField('RegexForField')

    # Fee amount;
    #  * for percentage fees it's the percentage - IE "2.95%"
    #  * for fixed it's the amount per transaction - IE "200" cents.
    amount = models.CharField(max_length=255)

    # Fee type
    #  * Fixed fees are a given amount per transaction, IE $2 per transaction.
    #  * Percentage fees are a percentage of a given transaction.
    #  * Mixed fees are fees which are "$2 or 2% which ever is greater".
    FEE_TYPE = (
        ('F', 'Fixed'),
        ('%', 'Percentage'),
        ('M', 'Mixed'),
        )
    type = models.CharField(max_length=1, choices=FEE_TYPE)

    # Fee model,
    #  * Included means that the fee is hidden as part of the transaction
    #    amount.
    #  * External means that the fee can be found as a seperate transaction in
    #    the account somewhere.
    FEE_MODEL = (
        ('I', 'Included in charge.'),
        ('E', 'External transaction.'),
        )
    model = models.CharField(max_length=1, choices=FEE_MODEL)

class FeeAdmin(admin.ModelAdmin):
    list_display = ('account', 'description', 'amount', 'type', 'model')

###############################################################################

class RelatedTransaction(models.Model):
    """RelatedTransaction tracks the relationships between transactions.

    Currently there are 3 supported types of relationships;
     * Fee - The trans_from transaction caused the trans_to fee.
     * Transfer - Money was moved between two accounts.
     * Shipping - The trans_from transaction caused the trans_to shipping fee
                  to exist.

    The relationship also consists of three types;
     * Automatic, this relationship was automatically created by one of the
       automatic tools.
     * Manual, this relationship was manually entered by the user.
     * Tombstone, this relationship was original automatically created by one
       of the automatic tools, but then deleted by the user. These
       relationships exist so the automatic systems don't keep recreating
       relationships that are being manually removed.
    """
    trans_from = models.ForeignKey('Transaction', related_name='+')
    trans_to = models.ForeignKey('Transaction', related_name='+')

    TRANSACTION_RELATIONSHIPS = (
        ('FEE', 'Bank Fee'),
        ('TRANSFER', 'Transfer between accounts'),
        ('SHIPPING', 'Shipping costs for a purchase'),
        )
    relationship = models.CharField(max_length=1, choices=TRANSACTION_RELATIONSHIPS)

    TRANSACTION_TYPES = (
        ('A', 'Automatic'),
        ('M', 'Manual'),
        ('T', 'Tombstone'),
        )
    type = models.CharField(max_length=1, choices=TRANSACTION_TYPES)

    fee = models.ForeignKey('Fee', null=True)

    def __unicode__(self):
        return "%s <-- %s --> %s" % (self.trans_from, self.relationship, self.trans_to)

class RelatedTransactionAdmin(admin.ModelAdmin):
    list_display = ('trans_to', 'trans_from', 'relationship', 'type', 'fee')
    list_filter = ('type', 'relationship',)

###############################################################################

class Transaction(models.Model):
    """Transactions are the fundemental building block of this app.

    Transactions are normally imported from a site on the web. The importer
    will populate the imported_* fields. Some of the fields can be manually
    overriden by the user.
    """
    account = models.ForeignKey('Account')

    # Transaction ID for an account, the recommended format:
    #  <Transaction Date><Transaction Text><Transaction amount><Account running value>
    trans_id = models.CharField(max_length=200)

    # These are the values imported from the site
    imported_effective_date = models.DateTimeField('effective date', null=True)
    imported_entered_date = models.DateTimeField('entered date')
    imported_description = models.CharField(max_length=200)
    imported_location = models.CharField(max_length=200)
    imported_amount = models.IntegerField()
    imported_running = models.IntegerField(null=True)

    # Sometimes there was a currency conversion done
    imported_original_currency = models.ForeignKey('Currency', null=True)
    imported_original_amount = models.IntegerField(null=True)

    # Sometimes this transaction references another transaction
    reference = models.ManyToManyField('self', through='RelatedTransaction', symmetrical=False)

    def related_transactions(self, type=None, relationship=None, fee=None):
        """Get the related transactions to this one.

        Args:
            type: Filter transactions to a give type such as Automatic, Manual
                  or Tombstone.
            relationship: Filter transactions to a give relationship such as
                          Transfer, Fee or Shipping.
            fee: If filtering transactions to the Fee type, only return
                 transactions which are associated with a given fee.
        """
        q = RelatedTransaction.objects.all()
        q = q.filter(Q(trans_from=self) | Q(trans_to__exact=self))

        if type is not None:
            q = q.filter(type__exact=type)

        if relationship is not None:
            q = q.filter(relationship__exact=relationship)

            if relationship.upper().startswith("F") and fee is not None:
                q = q.filter(fee__exact=fee)

        return q

    def distribute(self, relationship):
        """Distribute a fee accross all transactions associated with it.

        Useful for distributing shipping costs accross multiple purchases
        associated with it.

        Args:
            relationship: Filter transactions to a give relationship. Probably
                          want Fee or Shipping.
        """
        transactions = list(related_transactions(relationship))

        amount = 0
        for trans in transactions:
            amount += trans.imported_amount

        per_dollar = self.imported_amount/amount

        output = []
        for trans in transaction:
            output.append((trans, int(per_dollar*trans.imported_amount)))
        return output

    # These are the values which a user can enter/override
    override_description = models.CharField(max_length=200, null=True)

    # Suggested category
    suggested_categories = models.ManyToManyField('Category', related_name='transaction_suggested_set')

    # Primary category
    primary_category = models.ForeignKey('Category', related_name='transaction_primary_set', null=True)

    # Tagging...
    def __unicode__(self):
        return self.trans_id

    class Meta:
        unique_together = (("account", "trans_id"))
        get_latest_by = "imported_entered_date"
        ordering = ["-imported_entered_date", "-imported_effective_date"]

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'trans_id', 'imported_effective_date', 'imported_entered_date', 'imported_description', dollar_display('Amount', 'imported_amount', 'account.currency.symbol'), 'imported_original_currency', 'imported_location', dollar_display('Original Amount', 'imported_original_amount', 'imported_original_currency.symbol'))
    list_filter = ('account',)
    search_fields = ('imported_description', 'override_description')

###############################################################################

class Categorizer(models.Model):
    """Look for signals in transactions that allow auto-categorization.  """

    # Accounts this categorizer applies to.
    accounts = models.ManyToManyField('Account')

    # Regex
    regex = models.ManyToManyField('RegexForField')

    # Value bounds
    amount_minimum = models.IntegerField(null=True)
    amount_maximum = models.IntegerField(null=True)

    # Category that
    category = models.ForeignKey('Category')
