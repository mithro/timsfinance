from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchFrameException
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
profile.set_preference('browser.helperApps.neverAsk.saveToDisk', "text/csv")
profile.set_preference('browser.helperApps.neverAsk.saveToDisk', "text/comma-separated-values")
profile.set_preference('browser.helperApps.neverAsk.saveToDisk', "application/octet-stream")

driver = webdriver.Firefox(profile)

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

def get_account_table(driver):
  driver.switch_to_default_content()
  driver.switch_to_frame("main1")
  return driver.find_element_by_class_name("list")
  
def account_table_found(driver):
  try:
    get_account_table(driver)
    return True
  except (NoSuchElementException, NoSuchFrameException), e:
    return False

try:
  WebDriverWait(driver, 10).until(account_table_found)
  account_table = get_account_table(driver)
  account_rows = account_table.find_elements_by_xpath('tbody/tr')

  accounts = []
  for account_row in account_rows[1:]:
    accounts.append([y.text.strip() for y in account_row.find_elements_by_xpath('td')])
  import pprint
  pprint.pprint(accounts)


  account_rows[1].find_element_by_tag_name('a').click()

  def ready_download(driver):
    try:
      driver.find_element_by_tag_name('h1')
      return True
    except (NoSuchElementException, NoSuchFrameException), e:
      return False

  WebDriverWait(driver, 10).until(ready_download)
  download_csv = driver.find_element_by_xpath('//input[@value=3]')
  download_csv.click()
  
  submit = driver.find_element_by_xpath('//input[@type="submit"]')
  submit.click()

  while len(os.listdir(download_dir)) == 0:
    time.sleep(1)

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
