#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

"""
Commonwealth Bank of Australia NetBank downloader.
"""

from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchFrameException, ElementNotVisibleException
from selenium.webdriver.support.ui import WebDriverWait

import os
import pdb
import time


class Commbank(Importer):

    def login(self, username, password):
        self.driver.get("https://www3.netbank.commbank.com.au/netbank/bankmain")
        WebDriverWait(self.driver, 10).until(lambda driver : driver.title.lower().startswith("netbank - logon"))

        username = self.driver.find_element_by_id("clientNumber")
        username.send_keys(username)

        password = self.driver.find_element_by_id("password")
        password.send_keys(password)

        form = self.driver.find_element_by_class_name("menubutton")
        form.click()

        WebDriverWait(self.driver, 10).until(lambda driver: driver.title.lower().startswith("netbank - home"))
        return True

    def _get_account_table(self):
      return self.driver.find_element_by_id("MyPortfolioGrid1_a")
      
    def _account_table_found(self):
      try:
        self._get_account_table(self.driver)
        return True
      except (NoSuchElementException, NoSuchFrameException), e:
        return False

    def _account_table_rows(self):
        account_table = get_account_table(self.driver)
        return account_table.find_elements_by_xpath('tbody/tr')[:-3]

    def home(self):
        WebDriverWait(self.driver, 10).until(account_table_found)
        time.sleep(5)

    def accounts(self):
        accounts = []
        for account_row in self._account_table_rows():
            accounts.append([y.text.strip() for y in account_row.find_elements_by_xpath('td')])
        return accounts

    def _get_export_select(self):
        return self.driver.find_element_by_id('ctl00_BodyPlaceHolder_blockExport_ddlExportType_field')

    def _export_select_found(self):
        try:
            export_select = self._get_export_select(self.driver)
            export_select.find_element_by_xpath('option').click()
            return True
        except (NoSuchElementException, NoSuchFrameException, ElementNotVisibleException), e:
            return False

    def transactions(self, account_id, start_date, end_date):
        for account_row in self._account_table_rows():
            account_name = account_row.find_elements_by_xpath('td')[0].text.strip()
            if account_name == account_id:
                break
        else:
            raise AccountNotFound('Could not find account of id %s' % account_id)

        account_row.find_element_by_tag_name('a').click()
        WebDriverWait(self.driver, 10).until(lambda driver: driver.title.lower().startswith("netbank - trans"))

        show_form = self.driver.find_element_by_id('lnkShowHideSearch')
        show_form.click()

        date_range = self.driver.find_element_by_id('ctl00_BodyPlaceHolder_blockDates_rbtnChooseDates_field')
        date_range.click()

        from_date = self.driver.find_element_by_id('ctl00_BodyPlaceHolder_blockDates_caltbFrom_field')
        from_date.send_keys(start_date.strftime('%d/%m/%y'))
        to_date = self.driver.find_element_by_id('ctl00_BodyPlaceHolder_blockDates_caltbTo_field')
        to_date.send_keys(start_date.strftime('%d/%m/%y'))

        submit_button = self.driver.find_element_by_xpath('//input[@value="SEARCH"]')
        submit_button.click()

        WebDriverWait(self.driver, 10).until(self._export_select_found)

        export_select = self._get_export_select()
        export_csv = export_select.find_element_by_xpath('option[@value="CSV"]')
        export_csv.click()

        export_button = self.driver.find_element_by_xpath('//input[@value="EXPORT TRANSACTIONS"]')
        export_button.click()

        time.sleep(10)

        for handle in self._get_files():
            print handle.read()
