import base64
import mimetypes
import os
import re
import ssl
from tkinter import Tk
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from urllib3.exceptions import SSLError
from webdriver_manager.chrome import ChromeDriverManager


def getClip():
	fen = Tk()
	clip = fen.clipboard_get()
	fen.destroy()
	return clip.strip()


def get_url(url):
	driver.get("http://www.google.com/")
	driver.get(url)

	content = driver.page_source

	return content


def ddl_requests(url, path, headers=None):
	with session.get(url, stream=True, headers=headers) as rep:
		rep.raise_for_status()

		content_type = rep.headers['content-type']
		ext = mimetypes.guess_extension(content_type)
		path += ext

		with open(path, 'wb') as f:
			for chunk in rep.iter_content(chunk_size=8192):
				f.write(chunk)


def parse_imgs(imgs, root):
	seen = set()
	for img in imgs:
		org = img['original']
		src = img['src']
		file_type = img['type']

		if (org or src or None) is None:
			continue

		if org in seen or src in seen:
			continue

		seen.add(org)
		seen.add(src)

		src = org or src

		parsed_src = urlparse(src)
		if parsed_src.hostname is None:
			continue

		if bool(parsed_src.scheme) is False:
			parsed_src = parsed_src._replace(**{"scheme": "http"})
			src = parsed_src.geturl()

		filename = base64.b64encode(src.encode(
			"utf-8")).decode().replace('/', '_')
		path = os.path.join(root, filename)

		if any(f.startswith(filename) for f in os.listdir(root)):
			# File exists
			# Can't use os.path.exists because we don't know the file ext yet
			continue

		yield src, path


def get_folder(url):
	folder = os.path.join(
		root,
		base64.b64encode(url.encode("utf-8")).decode().replace('/', '_')
	)

	if not os.path.exists(folder):
		os.mkdir(folder)

	with open(os.path.join(folder, "website.txt"), "w") as f:
		f.write(url)

	return folder


class TLSAdapter(requests.adapters.HTTPAdapter):

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = ctx
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)


root = os.path.abspath("pictures")
if not os.path.exists(root):
	os.mkdir(root)

url_pattern = re.compile(
	r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)")
img_link = re.compile(
	"<img[^>]*(?:original|(?:data-)?src)=(?:\"|')([^ ]+)(?:\"|')[^>]*>")

urls = []

# while True:
# 	url = getClip()
# 	if url == 'STOP':
# 		break
# 	if url not in urls:
# 		if re.match(url_pattern, url):
# 			urls.append(url)
# 			print('Added', url)
# 	time.sleep(0.1)

with open('links.txt', 'r') as f:
	for line in f:
		url = line.strip()
		if re.match(url_pattern, url):
			urls.append(url)

options = Options()
options.add_argument("start-maximized")
options.add_argument("--log-level=2")
# options.add_experimental_option("excludeSwitches", ["enable-logging"])
options.headless = True
driver = webdriver.Chrome(service=Service(
	ChromeDriverManager().install()), options=options)
driver.implicitly_wait(15)


session = requests.Session()
session.mount('https://', TLSAdapter())

# js = (
# 	'var node = document.createElement("img");'
# 	'document.body.appendChild(node);'
# 	'node.style="max-width: 100%; height: auto; position: absolute; z-index: 100;";'
# 	'return node;'
# )

js = (
	'var items = [];'
		'for(item of document.querySelectorAll("img")){'
		'	var attrs = {};'
		'	for(attr of arguments[0]){'
		'		attrs[attr] = item.getAttribute(attr)'
		'	}'
		'	items.push(attrs);'
		'}'
		'return items;'
)

headers = {
		'Referer': '',
		'Connection': 'Keep-Alive',
		'Sec-Fetch-Dest': 'image',
		'Sec-Fetch-Mode': 'no-cors',
		'Sec-Fetch-Site': 'same-site',
		'User-Agent': driver.execute_script("return navigator.userAgent;")
}

for url in urls:
	if re.match(url_pattern, url):
		print(f'Parsing url: {url}')

		count = 0

		folder = get_folder(url)

		try:
			r = get_url(url)
		except Exception as e:
			print('Error on main:', url, e)
			continue

		referer = urlparse(url).netloc
		headers['Referer'] = referer

		cookies = driver.get_cookies()
		for cookie in cookies:
			session.cookies.set(cookie['name'], cookie['value'])

		imgs = driver.execute_script(js, ('original', 'src', 'type'))
		for src, path in parse_imgs(imgs, folder):
			try:
				ddl_requests(src, path, headers)
			except SSLError as e:
				print('SSLError on', src, ':', e)
			except Exception as e:
				print('Error on', src, ':', e)
				breakpoint()
			else:
				count += 1

		print(f'Downloaded {count} imgs')

	else:
		print(url, "is not an url!")
driver.quit()
