#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

import locale

from django.db import models
from django.db.models import Q
from django.contrib import admin


class Currency(models.Model):
    currency_id = models.CharField(max_length=200, primary_key=True)
    description = models.CharField(max_length=200)
    symbol = models.CharField(max_length=3)

    def __unicode__(self):
        return self.currency_id

    class Meta:
        verbose_name_plural = "currencies"

class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('currency_id', 'description')


class Category(models.Model):
    """Category for transactions."""
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


class Site(models.Model):
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


class Account(models.Model):
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


class Fee(models.Model):
    account = models.ForeignKey('Account')
    
    #description = models.CharField(max_length=255)

    # Regex to find transactions which have Fees applied to them.
    regex = models.CharField(max_length=255)

    # Fee amount
    amount = models.CharField(max_length=255)

    # Fee type
    FEE_TYPE = (
        ('F', 'Fixed'),
        ('%', 'Percentage'),
        ('M', 'Mixed'),
        )
    type = models.CharField(max_length=1, choices=FEE_TYPE)

class FeeAdmin(admin.ModelAdmin):
    list_display = ('account', 'regex', 'amount', 'type')


class RelatedTransaction(models.Model):
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
    list_display = ('trans_to', 'trans_from', 'relationship', 'type')
    list_filter = ('type', 'relationship',)


class Transaction(models.Model):
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


def dollar(text, field_name, currency):
    def f(obj):
        value = getattr(obj, field_name)
        if value is not None:
            value = str(value)
            if value[0] == "-":
                sign = "-"
                value = value[1:]
            else:
                sign = "+"
            cents = value[-2:]
            dollars = list(value[:-2])

            bits = [""]
            while len(dollars) > 0:
                if len(bits[0]) == 3:
                    bits.insert(0, "")
                bits[0] = dollars.pop(-1)+bits[0]
            if bits[0] == "":
                bits[0] = "0"

            return "$"+sign+",".join(bits)+'.'+cents
        return "(None)"
    f.short_description = text
    return f

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'trans_id', 'imported_effective_date', 'imported_entered_date', 'imported_description', dollar('Amount', 'imported_amount', 'account.currency.symbol'), 'imported_original_currency', 'imported_location', dollar('Original Amount', 'imported_original_amount', 'imported_original_currency.symbol'))
    list_filter = ('account',)
    search_fields = ('imported_description', 'override_description')
