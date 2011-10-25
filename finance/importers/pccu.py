#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

"""
People's Choice Credit Union PCLink downloader.

Formally Savings & Loans Credit Union and Australian Central Credit Union.
"""

import csv
import os
import pdb
import time
import datetime

from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchFrameException
from selenium.webdriver.support.ui import WebDriverWait

from finance.importers.base import Importer
from finance import models


class PeoplesChoiceCreditUnion(Importer):

    def login(self, username, password):
        # go to the google home page
        self.driver.get("https://online.peopleschoicecu.com.au/daib/logon/cu5050/logon.asp")
        WebDriverWait(self.driver, 10).until(lambda driver: driver.title.lower().startswith("people's"))

        usernamebox = self.driver.find_element_by_name("mn")
        usernamebox.send_keys(username)

        passwordbox = self.driver.find_element_by_name("pwd")
        passwordbox.send_keys(password)

        form = self.driver.find_element_by_name("loginform")
        form.submit()

        WebDriverWait(self.driver, 10).until(lambda driver: driver.title.lower().startswith("welcome"))
        self.driver.switch_to_frame("main1")

        continue_btn = self.driver.find_element_by_name("home")
        continue_btn.click()

        WebDriverWait(self.driver, 10).until(lambda driver: driver.title.lower().startswith("internet banking"))
        return True

    @classmethod
    def _get_account_table(cls, driver):
      driver.switch_to_default_content()
      driver.switch_to_frame("main1")
      return driver.find_element_by_class_name("list")
    
    @classmethod
    def _account_table_found(cls, driver):
      try:
        cls._get_account_table(driver)
        return True
      except (NoSuchElementException, NoSuchFrameException), e:
        return False

    @classmethod
    def _account_table_rows(cls, driver):
        account_table = cls._get_account_table(driver)
        return account_table.find_elements_by_xpath('tbody/tr')[1:]

    def home(self):
        WebDriverWait(self.driver, 10).until(self._account_table_found)

    def accounts(self, site, dummy=[]):
        if dummy:
            account_table_rows = dummy
        else:
            account_table_rows = self._account_table_rows(self.driver)

        account_details = []
        for account_row in account_table_rows:
            account_details.append([y.text.strip() for y in account_row.find_elements_by_xpath('td')])

        accounts = []
        for (account_id,
             description,
             current_blance, 
             overdraft_limit, 
             uncollected_funds, 
             available_balance) in account_details:

            try:
                account = models.Account.objects.get(site=site, account_id=account_id)
            except models.Account.DoesNotExist:
                account = models.Account(site=site, account_id=account_id)
                account.imported_last = datetime.datetime.fromtimestamp(0)

            account.description = description
            account.currency = models.Currency.objects.get(pk="AUD")

            accounts.append(account)

        return accounts

    @classmethod
    def _ready_download(cls, driver):
        try:
            driver.find_element_by_tag_name('h1')
            return True
        except (NoSuchElementException, NoSuchFrameException), e:
            return False

    def transactions(self, account, start_date, end_date):
        for account_row in self._account_table_rows(self.driver):
            if account_row.find_elements_by_xpath('td')[0].text.strip() == account.account_id:
                account_row.find_element_by_tag_name('a').click()
                break
        else:
            raise AccountNotFound('Could not find account of id %s' % account_id)

        WebDriverWait(self.driver, 10).until(self._ready_download)

        select_date_range = self.driver.find_element_by_name('DateRange').find_element_by_xpath('option[@value=6]')
        select_date_range.click()

        download_csv = self.driver.find_element_by_xpath('//input[@name="OutputRdo1"]').find_element_by_xpath('//input[@value=3]')
        download_csv.click()
 
        start_date_field = self.driver.find_element_by_name('BeginDate')
        start_date_field.clear()
        start_date_field.send_keys(start_date.strftime('%d/%m/%Y'))
        end_date_field = self.driver.find_element_by_name('EndDate')
        end_date_field.clear()
        end_date_field.send_keys(end_date.strftime('%d/%m/%Y'))

        submit = self.driver.find_element_by_xpath('//input[@type="submit"]')
        submit.click()

        for handle in self._get_files():
            return self.parse_file(account, handle)

    def parse_file(self, account, handle):
        transactions = []

        #Effective Date,Entered Date,Transaction Description,Amount,Balance
        #,15/10/2011,PAYMENT ,4500.00,236524.94
        for row in csv.DictReader(handle):
            trans_id = "%s|%s|%s|%s|%s" % (row['Effective Date'],row['Entered Date'],row['Transaction Description'],row['Amount'],row['Balance'])

            try:
                trans = models.Transaction.objects.get(account=account, trans_id=trans_id)
            except models.Transaction.DoesNotExist:
                trans = models.Transaction(account=account, trans_id=trans_id)

            trans.imported_entered_date = datetime.datetime.strptime(row['Entered Date'], '%d/%m/%Y')
            if row['Effective Date']:
                trans.imported_effective_date = datetime.datetime.strptime(row['Effective Date'], '%d/%m/%Y')

            trans.imported_description = row['Transaction Description'].strip()
            if '(OS)' in row['Transaction Description']:
                trans.imported_location = "Outside Australia"
            else:
                trans.imported_location = "Australia"

            # Remove the decimal so we get back to cents
            amount = int(row['Amount'].replace('.', ''))
            trans.imported_amount = int(amount)

            running = int(row['Balance'].replace('.', ''))
            trans.imported_running = running

            transactions.append(trans)


        # At the moment it's hardcoded to the following;
        # FEE TO BE CAP'D
        # PRIN CR ADJUST
        for trans in transactions:
            if trans.imported_description in ("FEE TO BE CAP'D", "PRIN CR ADJUST"):
                amount = trans.imported_amount
                trans.imported_amount = 0
                trans.imported_description += " -- $%i.%s" % (amount/100, str(amount)[-2:])

        # For loans an a couple of other weird transactions, the amount is set
        # to something but the Balance doesn't change. We go back over the
        # transactions and root out these.
        #
        # For this we need the last transcation in the account..
        #last_trans = account.transaction_set.all()
        #last_trans.order_by('imported_entered_date')

        #temp_transactions = transactions+[last_trans[0]]
        #while len(temp_transactions) > 1:
        #    trans = temp_transactions.pop(0)
        #
        #    difference = temp_transactions[0].imported_running - trans.imported_running 
        #    print trans.imported_description, difference, trans.imported_amount

        return transactions
