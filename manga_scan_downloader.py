import requests
from bs4 import BeautifulSoup, Tag
import base64
import os
import re
import queue
import threading

url = "https://www.sololeveling.fr/"

def b64_hash(url):
	return base64.b64encode(url.encode()).decode()

def get(url):
	url_hash = b64_hash(url)
	path = os.path.join("website_hashes", url_hash)
	if os.path.exists(path):
		with open(path, 'r') as f:
			p = f.read()
		return p
	else:
		r = requests.get(url)
		r.raise_for_status()

		p = r.content.decode()
		with open(path, 'w') as f:
			f.write(p)
		return p

def ddl(url, path, s=None):
	if not os.path.exists(path):
		print("Downloading:", l_data['alt'])
		try:
			if s is None:
				s = requests
			r = s.get(l_data['src'])
			r.raise_for_status()
		except Exception as e:
			print(l_data['alt'], "- on url:", l_data['src'], "-", e, e.args)
		else:
			with open(path, 'wb') as f:
				f.write(r.content)

def ddl_thread_worker(que):
	while True:
		data = que.get()
		if data == "STOP":
			return
		ddl(*data)

data = {}

p = get(url)

p_soup = BeautifulSoup(p, 'html.parser')
links = [child['href'] for child in p_soup.find("li", {"id": "ceo_latest_comics_widget-3"}).ul.find_all("a")]

for link in links:
	l = get(link)
	l_soup = BeautifulSoup(l, 'lxml')
	l_data = [
		{
			'src': child['src'],
			'alt': child['alt']
		} for child in l_soup.find("main").article.div.div.find_all("img")
	]

	data[link] = l_data

	print(link, len(l_data))

root = os.path.join("mangas", p_soup.title.text)
if not os.path.exists(root):
	os.mkdir(root)

USE_THREADS = False
MAX_THREADS = 3

if USE_THREADS:
	que = queue.Queue()
	threads = []
	for i in range(MAX_THREADS):
		t = threading.Thread(target=ddl_thread_worker, args=(que,), daemon=True)
		t.start()
		threads.append(t)

with requests.Session() as s:
	for link, imgs in data.items():
		for l_data in imgs:
			file = l_data['alt'] + ".jpg"
			path = os.path.join(root, file)
			if USE_THREADS:
				que.put((url, path, s))
			else:
				ddl(url, path, s)

if USE_THREADS:
	for i in range(MAX_THREADS):
		que.put("STOP")

	for t in threads:
		t.join()

print("Done!")