
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def init():
    global driver
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(15)

def parse_url(url, fields):
    driver.get(url)
    tables = driver.find_elements(By.XPATH, '//button')

    if not tables:
        print('No table found!')
        return

    print(f'{len(tables)} found')

    out = []
    for table in tables:
        headers = []
        for col in table['thead']['tr']:
            headers.append(col.text)

        table = table['tbody']
        data = []
        for field in fields:
            table.find_element()

if __name__ == '__main__':
    URL = 'https://spys.one/en/socks-proxy-list/'
    FIELDS = []

    init()
    parse_url(URL, FIELDS)