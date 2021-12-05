from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import requests

driver = webdriver.Firefox(executable_path=r'C:\Program Files\geckodriver\geckodriver.exe')
driver.implicitly_wait(15)

xPth = lambda e: driver.find_element_by_xpath(e)

driver.get("https://www.youtube.com/watch?v=DCmh5fvgqq4")

"""xPth('/html/body/ytd-app/ytd-popup-container/paper-dialog/yt-upsell-dialog-renderer/div/div[3]/div[1]/yt-button-renderer/a').click()"""
data = driver.execute_script('return ytInitialPlayerResponse;')

driver.quit()

data = data['streamingData']['formats']

for d in data:
    print(d['quality']+"------"+d['url'])

ind = 1 #int(input("Index: "))
url = data[ind]['url']
file_out = 'video.mp4'

r = requests.get(url, stream=True)
with open(file_out, 'wb') as f:
    for chunk in r.iter_content(chunk_size=1024):
        if chunk: 
            f.write(chunk)
