#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

from django.db import models
from django.contrib import admin

class Currency(models.Model):
    currency_id = models.CharField(max_length=200, primary_key=True)
    description = models.CharField(max_length=200)

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

    class Meta:
        verbose_name_plural = "categories"

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'description')


class Transaction(models.Model):
    account_id = models.ForeignKey('Site')

    # Transaction ID for an account, the recommended format:
    #  <Transaction Date><Transaction Text><Transaction amount><Account running value>
    trans_id = models.CharField(max_length=200, primary_key=True)

    # These are the values imported from the site
    imported_effective_date = models.DateTimeField('effective date')
    imported_entered_date = models.DateTimeField('entered date')
    imported_description = models.CharField(max_length=200)
    imported_amount = models.IntegerField()
    imported_running = models.IntegerField()

    # Sometimes there was a currency conversion done
    imported_original_currency = models.ForeignKey('Currency')
    imported_original_amount = models.IntegerField()

    # Sometimes this transaction references another transaction
    imported_reference = models.ManyToManyField('self')

    # These are the values which a user can enter/override
    override_description = models.CharField(max_length=200)
    
    # Suggested category
    suggested_categories = models.ManyToManyField('Category', related_name='transaction_suggested_set')

    # Primary category
    primary_category = models.ForeignKey('Category', related_name='transaction_primary_set')

    # Tagging...
    
    class Meta:
        get_latest_by = "imported_effective_date"
        ordering = ["-imported_effective_date"]

    
class Account(models.Model):
    site_id = models.ForeignKey('Site')
    account_id = models.CharField(max_length=200, primary_key=True)
    currency = models.ForeignKey('Currency')

    # Latest import time that occured
    last_import = models.DateTimeField('last import')

    starting_balance = models.IntegerField()
    current_balance = models.IntegerField()

class AccountAdmin(admin.ModelAdmin):
    list_display = ('site_id', 'account_id', 'currency', 'last_import', 'current_balance')
    list_filter = ('site_id',)


class Site(models.Model):
    site_id = models.CharField(max_length=200, primary_key=True)
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=200, null=True, blank=True)

    # The python class name for the tool which imports
    importer = models.CharField(max_length=200)
    image = models.URLField(max_length=1000)
    # Latest import time that occured
    last_import = models.DateTimeField('last import')

class SiteAdmin(admin.ModelAdmin):
    list_display = ('site_id', 'username', 'last_import')
    list_filter = ('importer',)
