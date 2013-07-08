import inspect

from django.db import models as django_models
from django.contrib import admin

from finance import models as finance_models
from finance.utils import dollar_display
from finance.models import (RegexForField, Currency, Category, Site, Account, Imported, Fee,
                     RelatedTransaction, Transaction, Reconciliation, Categorizer)


class RegexForFieldAdmin(admin.ModelAdmin):
    list_display = ('description', 'field', 'regex', 'regex_type', 'regex_flags')


class CurrencyInline(admin.TabularInline):
    model = Currency


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('currency_id', 'description')


class CategoryInline(admin.TabularInline):
    model = Category


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'description')


class AccountInline(admin.TabularInline):
    model = Account


class SiteAdmin(admin.ModelAdmin):
    list_display = ('site_id', 'username', 'importer')
    list_filter = ('importer',)
    inlines = [AccountInline]


class AccountAdmin(admin.ModelAdmin):
    list_display = ('site', 'account_id', 'sql_id', 'description', 'currency', 'current_balance')
    list_filter = ('site',)


class FeeAdmin(admin.ModelAdmin):
    list_display = ('account', 'description', 'amount', 'type', 'model')


class RelatedTransactionAdmin(admin.ModelAdmin):
    list_display = ('trans_to', 'trans_from', 'relationship', 'type', 'fee')
    list_filter = ('type', 'relationship',)


class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'account',
        'imported_entered_date',
        'description',
        dollar_display('Amount', 'imported_amount', 'account.currency.symbol'),
        'location',
        dollar_display('Original Amount', 'imported_original_amount', 'imported_original_currency.symbol'),
        'primary_category',
        'categories',
        )
    list_filter = ('account','primary_category')
    search_fields = ('imported_description', 'override_description', 'imported_location', 'override_location')
    list_editable = ('primary_category',)
    date_hierarchy = 'imported_entered_date'


class CategorizerAdmin(admin.ModelAdmin):
    list_display = ('pk', 'accounts_set', 'regex_set', 'amount_minimum', 'amount_maximum', 'personal', 'category')
    list_filter = ('category', 'personal')


for model_name in dir(finance_models):
    model = getattr(finance_models, model_name)
    if inspect.isclass(model) and issubclass(model, django_models.Model):
       admin_interface = getattr(finance_models, model_name+'Admin', None)
       if admin_interface:
          admin.site.register(model, admin_interface)
       else:
          admin.site.register(model)
