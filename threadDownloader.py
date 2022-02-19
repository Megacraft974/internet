url = "https://www.mysqltutorial.org/wp-content/uploads/2018/03/mysqlsampledatabase.zip"

import threading
import requests
from time import sleep
import os

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
    r = requests.get(fileurl, headers=resume_header, stream=True, verify=False, allow_redirects=True)
    root = "C:/Users/willi/Documents/"
    folder = os.path.join(root, "tmpDownload")
    if not os.path.exists(folder):
        os.mkdir(folder)
    file = os.path.join(folder, "chunk-{}-{}".format(start,stop))
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
    for file in sorted(os.listdir(path)):
        #print(file)
        with open(path+file,'rb') as tf:
            f.write(tf.read())
print("Done!")
