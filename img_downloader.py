from tkinter import *
from selenium import webdriver
import re, requests, time, os, datetime
import threading

def getClip():
	fen = Tk()
	clip = fen.clipboard_get()
	fen.destroy()
	return clip


def get_url(url):
	driver.get(url)

	content = driver.page_source

	return content

def download_img(img_url, folder):
	try:
		filename = img_url.rsplit("/", 1)[-1].rsplit(".", 1)
		filename = filename[0] + str(len(os.listdir(folder))) + "." + filename[1]
	except IndexError:
		return

	if not re.match(url_pattern, img_url):
		tmp = url + ("/" if url[-1] != "/" else "") + img_url
		if re.match(url_pattern, tmp):
			img_url = tmp

	print(img_url, flush=True)

	try:
		img_r = requests.get(img_url)
		img_r.raise_for_status()
	except Exception as e:
		print(e, flush=True)
		return

	with open(os.path.join(folder, filename), 'wb') as f:
		f.write(img_r.content)
	print(img_url, "DONE", flush=True)

def wait_for_threads(threads):
	def handler(t, e):
		t.join()
		e.set()

	e = threading.Event()
	for t in threads:
		threading.Thread(target=handler, args=(t, e), daemon=True).start()
	return e

root = os.path.abspath("pictures")
if not os.path.exists(root):
	os.mkdir(root)

url_pattern = re.compile(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)")
img_link = re.compile("<img[^>]* (?:data-)?src=(?:\"|')([^ ]+)(?:\"|')[^>]*>")

MAX_THREADS = 10

url = getClip()

if re.match(url_pattern, url):
	folder = os.path.join(root, "file-" + str(len(os.listdir(root))+1))#datetime.datetime.now().strftime("%H-%M-%S"))
	os.mkdir(folder)
	with open(os.path.join(folder, "website.txt"), "w") as f:
		f.write(url)


	executable_path = r'C:\Program Files\geckodriver\geckodriver.exe'
	opts = webdriver.FirefoxOptions()
	opts.headless = True
	driver = webdriver.Firefox(executable_path=executable_path,options=opts)
	driver.implicitly_wait(15)

	r = get_url(url)

	threads = []
	imgs = re.findall(img_link, r)
	if len(imgs) > 0:
		print(str(len(imgs)) + " images found")
		for img_url in imgs:
			# img_url = img_url.decode()
			print(img_url)

			t = threading.Thread(target=download_img, args=(img_url, folder), daemon=True)
			t.start()
			threads.append(t)

			while len(threads) > MAX_THREADS:
				threads = list(filter(lambda e: e.is_alive(), threads))
				wait_for_threads(threads).wait()
		
		for t in threads:
			t.join()
	else:
		print("No image found")
	driver.quit()
else:
	print(url, "is not an url!")