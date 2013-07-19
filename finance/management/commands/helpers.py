#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:
"""
The linker looks for transactions which should be linked together, such as
transfers between accounts.
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from finance import models
from finance import helpers


class Command(BaseCommand):
    args = ''
    help = 'Run helpers with transactions'

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)

        active_helpers = [
            helpers.categorizer.Categorizer(),
            helpers.fees.Fees(),
            helpers.reworker.LocationFixer(),
            helpers.transfers.Transfers(),
            ]

        for account in models.Account.objects.all():
            logging.info("%s", account)
            for transaction in account.transaction_set.all():
                logging.info("%s", transaction)
                for helper in active_helpers:
                    logging.info("%s", helper)
                    helper.handle(account, transaction)
