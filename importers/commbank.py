from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchFrameException, ElementNotVisibleException
from selenium.webdriver.support.ui import WebDriverWait

import os
import pdb
import time

# Create a new instance of the Firefox driver

download_dir = "/tmp/webdriver-downloads-%i" % os.getpid()
os.mkdir(download_dir)

profile = FirefoxProfile()
profile.set_preference('browser.download.dir', download_dir)
profile.set_preference('browser.download.folderList', 2)
profile.set_preference('browser.helperApps.neverAsk.saveToDisk', "text/csv,text/comma-separated-values,application/octet-stream,application/csv")

driver = webdriver.Firefox(profile)

# go to the google home page
driver.get("https://www3.netbank.commbank.com.au/netbank/bankmain")
WebDriverWait(driver, 10).until(lambda driver : driver.title.lower().startswith("netbank - logon"))

username = driver.find_element_by_id("clientNumber")
username.send_keys("XXXXXXXX")

password = driver.find_element_by_id("password")
password.send_keys("XXXXXXXXXXXXX")

form = driver.find_element_by_class_name("menubutton")
form.click()

WebDriverWait(driver, 10).until(lambda driver: driver.title.lower().startswith("netbank - home"))

def get_account_table(driver):
  return driver.find_element_by_id("MyPortfolioGrid1_a")
  
def account_table_found(driver):
  try:
    get_account_table(driver)
    return True
  except (NoSuchElementException, NoSuchFrameException), e:
    return False

try:
  WebDriverWait(driver, 10).until(account_table_found)
  time.sleep(5)
  account_table = get_account_table(driver)
  account_rows = account_table.find_elements_by_xpath('tbody/tr')

  accounts = []
  for account_row in account_rows[:-3]:
    accounts.append([y.text.strip() for y in account_row.find_elements_by_xpath('td')])
  import pprint
  pprint.pprint(accounts)

  account_rows[0].find_element_by_tag_name('a').click()

  WebDriverWait(driver, 10).until(lambda driver: driver.title.lower().startswith("netbank - trans"))

  show_form = driver.find_element_by_id('lnkShowHideSearch')
  show_form.click()

  date_range = driver.find_element_by_id('ctl00_BodyPlaceHolder_blockDates_rbtnChooseDates_field')
  date_range.click()

  from_date = driver.find_element_by_id('ctl00_BodyPlaceHolder_blockDates_caltbFrom_field')
  from_date.send_keys('10/10/2011')
  to_date = driver.find_element_by_id('ctl00_BodyPlaceHolder_blockDates_caltbTo_field')
  to_date.send_keys('20/10/2011')

  submit_button = driver.find_element_by_xpath('//input[@value="SEARCH"]')
  submit_button.click()

  def get_export_select(driver):
     return driver.find_element_by_id('ctl00_BodyPlaceHolder_blockExport_ddlExportType_field')

  def export_select_found(driver):
    try:
      export_select = get_export_select(driver)
      export_select.find_element_by_xpath('option').click()
      return True
    except (NoSuchElementException, NoSuchFrameException, ElementNotVisibleException), e:
      return False
  WebDriverWait(driver, 10).until(export_select_found)

  export_select = get_export_select(driver)
  export_csv = export_select.find_element_by_xpath('option[@value="CSV"]')
  export_csv.click()

  export_button = driver.find_element_by_xpath('//input[@value="EXPORT TRANSACTIONS"]')
  export_button.click()

  time.sleep(10)

  while True:
   files = os.listdir(download_dir)
   print files
   if len([f for f in files if f.endswith('.part')]) > 0:
      continue
   if len(files) > 0:
      break

  for filename in os.listdir(download_dir):
    fullpath = os.path.join(download_dir, filename)
    print fullpath
    print "-----------------------"
    print file(fullpath, 'r').read()
    print "-----------------------"
    os.unlink(fullpath)

except Exception, e:
  print e
  pdb.post_mortem()
finally:
  pdb.set_trace()

driver.quit()
