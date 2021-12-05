#url = "https://big.romspure.com/NSW/Hyrule%20Warriors%20Age%20of%20Calamity%20%5B01002B00111A2000%5D%5Bv0%5D.nsp?__cf_chl_jschl_tk__=e55fb2e7ee47f902fe1d7e386fad472b2f088de4-1608966695-0-AeYu_VPccZAV8iU2bCqAYW8tPNsOHPVnFpHo9Qy6Rf3WGq-o56WiXUmeapMeJ0KJyUogW60oEV06U_CcBgxU5Md8ySUYfiuc6mvJDbqElMeAdCGb1Piu_TMffXq2dhouC-Ftqfz04Tkr3EC0TaTi-CNPT8Pm7D1WY09Xb0x73a356fdvzUGg1LlxwHKIT2IwytHVmM-Win0kDbVVUAMAT0lHn-XrzpsrNOp0ULUxLFxBujJRQ0zBng37cxsdSKbCtffJB9rGL_ikdKuK6CN__BESObcBGabx0Fku3ero0ZMYbRnoYjov5QGbg5yzVcsIojf0BBmYVy64hzN4KNPUE_tfJiIS-P6LHjRVQMWlrhRtMIVVBe46__gs30PMt2BkM4yy8Xe_MCn8eSuPOtm2J2XtBXngrSSZ1cfZXmv6SPdd"
url = "https://big.romspure.com/NSW/Hyrule%20Warriors%20Age%20of%20Calamity%20%5B01002B00111A2000%5D%5Bv0%5D.nsp?__cf_chl_jschl_tk__=e55fb2e7ee47f902fe1d7e386fad472b2f088de4-1608966695-0-AeYu_VPccZAV8iU2bCqAYW8tPNsOHPVnFpHo9Qy6Rf3WGq-o56WiXUmeapMeJ0KJyUogW60oEV06U_CcBgxU5Md8ySUYfiuc6mvJDbqElMeAdCGb1Piu_TMffXq2dhouC-Ftqfz04Tkr3EC0TaTi-CNPT8Pm7D1WY09Xb0x73a356fdvzUGg1LlxwHKIT2IwytHVmM-Win0kDbVVUAMAT0lHn-XrzpsrNOp0ULUxLFxBujJRQ0zBng37cxsdSKbCtffJB9rGL_ikdKuK6CN__BESObcBGabx0Fku3ero0ZMYbRnoYjov5QGbg5yzVcsIojf0BBmYVy64hzN4KNPUE_tfJiIS-P6LHjRVQMWlrhRtMIVVBe46__gs30PMt2BkM4yy8Xe_MCn8eSuPOtm2J2XtBXngrSSZ1cfZXmv6SPdd"

import threading
import requests
from time import sleep
from os import listdir

requests.packages.urllib3.disable_warnings()

file = url.split('/')[-1].split("?")[0]
if file == "":
    file = "image.jpg"
r = requests.head(url)
try:
    size = int(r.headers["Content-length"])
except:
    size = 10**1000
default_threads = threading.enumerate() 

def get_chunk(fileurl, start, stop):
    resume_header = {'Range': 'bytes={}-{}'.format(start,stop)}
    #resume_header = {}
    r = requests.get(fileurl, headers=resume_header, stream=True,  verify=False, allow_redirects=True)
    file = "C:/Users/willi/Documents/tmpDownload/chunk-{}-{}".format(start,stop)
    if not r.status_code in (200,206):
        print("{} stopped, status: {}\n".format(start,r.status_code),end="")
        global running
        running = False
        return
    with open(file,'wb') as f:
        for ch in r.iter_content(chunk_size=1024):
            if ch:
                f.write(ch)

chunk = 1024
start, stop = 0, chunk*10

running = True
counter = 0
print("Downloading...")
while running:
    counter += 1
    thread = threading.Thread(target=get_chunk,args=(url,start,stop))
    thread.start()
    sleep(0.1)
    print("Started {}\n".format(start),end="")
    if counter >= 1000 or stop > size:
        running = False
    start, stop = stop, stop + chunk*10

print("Done, waiting...")
for t in threading.enumerate(): 
    if not t in default_threads:
        t.join()

path = "C:/Users/willi/Documents/tmpDownload/"
print("Done, merging...")
with open(file,'wb') as f:
    for file in listdir(path):
        #print(file)
        with open(path+file,'rb') as tf:
            f.write(tf.read())
print("Done!")
