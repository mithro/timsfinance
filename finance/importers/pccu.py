#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

"""
People's Choice Credit Union PCLink downloader.

Formally Savings & Loans Credit Union and Australian Central Credit Union.
"""

from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchFrameException
from selenium.webdriver.support.ui import WebDriverWait

import os
import pdb
import time

class PeoplesChoiceCreditUnion(object):

    def login(self, username, password):
        # go to the google home page
        driver.get("https://online.peopleschoicecu.com.au/daib/logon/cu5050/logon.asp")
        WebDriverWait(driver, 10).until(lambda driver : driver.title.lower().startswith("people's"))

        username = driver.find_element_by_name("mn")
        username.send_keys("XXXXXXXX")

        password = driver.find_element_by_name("pwd")
        password.send_keys("XXXXXXXXXXXXX")

        form = driver.find_element_by_name("loginform")
        form.submit()

        WebDriverWait(driver, 10).until(lambda driver: driver.title.lower().startswith("welcome"))
        driver.switch_to_frame("main1")

        continue_btn = driver.find_element_by_name("home")
        continue_btn.click()

        WebDriverWait(driver, 10).until(lambda driver: driver.title.lower().startswith("internet banking"))

    def _get_account_table(self):
      self.driver.switch_to_default_content()
      self.driver.switch_to_frame("main1")
      return self.driver.find_element_by_class_name("list")
      
    def _account_table_found(self):
      try:
        self._get_account_table(self)
        return True
      except (NoSuchElementException, NoSuchFrameException), e:
        return False

    def _account_table_rows(self):
        accounts = []
        for account_row in account_rows[1:]:
            accounts.append([y.text.strip() for y in account_row.find_elements_by_xpath('td')])
        return accounts

    def home(self):
      WebDriverWait(driver, 10).until(account_table_found)

    def accounts(self):
        return self._account_table_rows

    def _ready_download(driver):
        try:
            driver.find_element_by_tag_name('h1')
            return True
        except (NoSuchElementException, NoSuchFrameException), e:
            return False

    def transactions(self, account_id, start_date, end_date):
        # FIXME: Use start_date/end_date
        for account_row in self._account_table_rows():
            if account_row.find_elements_by_xpath('td')[0].text.strip() == account_id:
                account_rows.find_element_by_tag_name('a').click()
                break
        else:
            raise AccountNotFound('Could not find account of id %s' % account_id)

        WebDriverWait(driver, 10).until(self._ready_download)
        download_csv = driver.find_element_by_xpath('//input[@value=3]')
        download_csv.click()
  
        submit = driver.find_element_by_xpath('//input[@type="submit"]')
        submit.click()

        for handle in self._get_files():
            print handle.read()
