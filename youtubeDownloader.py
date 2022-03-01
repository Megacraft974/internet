from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import requests

class Downloader:
    def __init__(self, executable_path=None):
        if executable_path is None:
            executable_path = r'C:\Program Files\geckodriver\geckodriver.exe'
        
        opts = webdriver.FirefoxOptions()
        opts.headless = True
        self.driver = webdriver.Firefox(executable_path=executable_path,options=opts)
        self.driver.implicitly_wait(15)

        self.xPth = lambda e: self.driver.find_element_by_xpath(e)

    def get_urls(self, url):
        self.driver.get(url)

        """xPth('/html/body/ytd-app/ytd-popup-container/paper-dialog/yt-upsell-dialog-renderer/div/div[3]/div[1]/yt-button-renderer/a').click()"""
        data = self.driver.execute_script('return ytInitialPlayerResponse;')

        self.driver.quit()

        data = data['streamingData']['formats']

        return sorted(data, key=lambda e:e['height'], reverse=True)

    def ddl(self, url, file=None):
        data = self.get_urls(url)
        if len(data) == 0:
            return

        # print('\n'.join('-'.join(map(str, e)) for e in data[0].items()))
        url = data[0]['url']
        size = int(data[0]['contentLength'])
        if file is None:
            file = 'video.mp4'

        current_size = 0
        r = requests.get(url, stream=True)
        with open(file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    current_size += len(chunk)
                    f.write(chunk)
                    print(str(current_size) + " / " + str(size) + " - " + str(int(current_size/size*100)) + "%")

url = "https://www.youtube.com/watch?v=8CYy9jNmpXM"
d = Downloader()
d.ddl(url)