#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

"""
Importers download account and transaction data from banks.
"""

import os
import shutil

from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile


class Importer(object):
    
    def __init__(self):
        self.download_dir = "/tmp/%s-downloads-%i" % (self.__class__.__name__, os.getpid())
        os.mkdir(self.download_dir)

        profile = FirefoxProfile()
        profile.set_preference('browser.download.dir', self.download_dir)
        profile.set_preference('browser.download.folderList', 2)
        profile.set_preference('browser.helperApps.neverAsk.saveToDisk', "text/csv,text/comma-separated-values,application/octet-stream,application/csv")

        self.driver = webdriver.Firefox(profile)

    def __del__(self, rmtree=shutil.rmtree):
        rmtree(self.download_dir)
        self.driver.quit()

    def _get_files(self):
        # Wait until some files exist and all .part files are gone.
        while True:
           files = os.listdir(download_dir)
           if len([f for f in files if f.endswith('.part')]) > 0:
              continue
           if len(files) > 0:
              break

        for filename in os.listdir(download_dir):
            fullpath = os.path.join(download_dir, filename)
            yield file(fullpath, "r")
            os.unlink(fullpath)

    def login(self, username, password):
        pass

    def home(self):
        """Return to the home screen so we can call other functions."""
        pass

    def accounts(self):
        """Return the accounts that exist."""
        pass

    def transactions(self, account_id, start_date, end_date):
        """Download the transaction details for a given account."""
        pass
