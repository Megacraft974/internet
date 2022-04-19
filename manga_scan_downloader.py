import os
import urllib.parse
import re
import queue
import time
import threading
import json
import shutil
import zipfile

import base64
import hashlib

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By

from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
from lxml import etree
import lxml.html

data_list = []

# Webtoons.com

if True:
	headers = {
		'Cookie': 'pagGDPR=true;',
		'Referer': 'https://www.webtoons.com'
	}

	urls = [
		('https://www.webtoons.com/en/fantasy/1hp-club/list?title_no=2960', 2),
		('https://www.webtoons.com/en/action/the-gamer/list?title_no=88', 10),
	]

	data_global = {
		'title': './/title',
		'xpth': {
			'main_list': '//*[@id="_listUl"]',
			'main_list_item': 'a',
			'img_list': '//*[@id="_imageList"]',
			'img_list_item': 'img',
		},
		'img_url': 'data-url',
		'img_desc': 'alt',
		'headers': headers
	}

	data_list.extend([({'url': url + f'&page={i}'} | data_global) for url, page in urls for i in range(1, page+1)])

# Manhwaz.com // parse directly img link? -> range // Parser blocked

if True:
	urls = [
		"https://manhwaz.com/webtoon/the-magic-in-this-other-world-is-too-far-behind"
	]

	data_global = {
		'title': './/title',
		'xpth': {
			'main_list': '/html/body/div[1]/div[2]/div/div/div[1]/div[3]/ul',
			'main_list_item': 'a',
			'img_list': '//*[@id="chapter_content"]',
			'img_list_item': '*/img'
		},
		'img_url': 'src',
		'img_desc': 'alt',
		'headers': {}
	}

	data_list.extend([({'url': url} | data_global) for url in urls])

# Sololeveling.fr

if True:
	headers = {
		'Referer': 'https://www.sololeveling.fr/'
	}

	urls = [
		"https://www.sololeveling.fr/"
	]

	data_global = {
		'title': '/html/body/div/div/div/div/div/main/article/div/header/h1',
		'xpth': {
			'main_list': '/html/body/div/div/div/div/div/main/article/div/div/div[2]/ul/li/ul',
			'main_list_item': 'a',
			'img_list': '/html/body/div/div/div/div/div/main/article/div/div',
			'img_list_item': '*/img'
		},
		'img_url': 'src',
		'img_desc': 'title',
		'headers': headers
	}

	data_list.extend([({'url': url} | data_global) for url in urls])

# Readmanganato.com

if True:
	headers = {
		'Referer': 'https://readmanganato.com/'
	}

	urls = [
		# "https://readmanganato.com/manga-mh989642", # Chr-47
		# "https://readmanganato.com/manga-ax951880", # Tales Of Demons And Gods
		# "https://readmanganato.com/manga-je987087", # The Max Level Hero Has Returned!
		# "https://readmanganato.com/manga-ci980191", # A Returner's Magic Should Be Special
		"https://readmanganato.com/manga-bf979214", # Versatile Mage
		# "https://readmanganato.com/manga-ej981992", # I Am The Sorcerer King
		# "https://readmanganato.com/manga-eu982203", # Tomb Raider King
		"https://readmanganato.com/manga-to970571", # Kimetsu no Yaiba
		"https://readmanganato.com/manga-cb980036" # The World Of Otome Games Is Tough For Mobs
	]

	data_global = {
		'title': '/html/body/div[1]/div[3]/div[1]/div[2]/div[2]/h1',
		'xpth': {
			'main_list': '/html/body/div[1]/div[3]/div[1]/div[3]/ul',
			'main_list_item': 'a',
			'img_list': '/html/body/div[1]/div[3]',
			'img_list_item': 'img'
		},
		'img_url': 'src',
		'img_desc': 'alt',
		'headers': headers
	}

	data_list.extend([({'url': url} | data_global) for url in urls])

# magakakalot.tv

if True:
	urls = [
		"https://ww3.mangakakalot.tv/manga/manga-bs978875",
	]

	data_global = {
		'title': '/html/body/div[1]/div[2]/div[1]/div[3]/ul/li[1]/h1',
		'xpth': {
			'main_list': '/html/body/div[1]/div[2]/div[1]/div[9]/div/div[2]',
			'main_list_item': 'span[1]/a',
			'img_list': '//*[@id="vungdoc"]',
			'img_list_item': 'img[@class="img-loading"]'
		},
		'img_url': 'data-src',
		'img_desc': 'alt',
		'headers': {}
	}

	data_list.extend([({'url': url} | data_global) for url in urls])

# Hash function - "sha1" or "b64"
HASH_FUNCTION = "b64"

# Folder output
OUTPUT = "~/Documents/webtoons"
OUTPUT = os.path.normpath(os.path.expanduser(OUTPUT))

# Ddl threads
USE_THREADS = True
MAX_THREADS = 3
USE_CACHE = True
RELOAD_MAIN = False
TIMEOUT = 15

# Parser - "lxml" or "bs4"
USE_PARSER = "lxml"

# Download library - "selenium" or "requests"
USE_DDL = "requests"

# Logs
LOG_PARSE = True
LOG_DDL = True
LOG_DDL_FULL = False
LOG_ARCHIVE = True


class MangaDownloader():
	def __init__(self, data_list):
		self.data_list = data_list
		
		if not os.path.exists(OUTPUT):
			os.mkdir(OUTPUT)

		self.threads, self.archive_threads = [], []
		
		self.event = threading.Event() # File downloaded event
		self.stop_event = threading.Event() # Archive thread stop event
		self.que = queue.Queue()

		self.LOG_DDL_last = time.time()
		self.LOG_DDL_count = 0

		if USE_DDL == "selenium":
			ddl = SeleniumDownloader
		elif USE_DDL == "requests":
			ddl = RequestsDownloader

		with ddl() as self.downloader:
			for data in self.data_list:
				try:
					self.handle_data(data)
				except Exception as e:
					print(f'Error on url {data["url"]}: {e}')

			if USE_THREADS:
				self.stop()

		print("Done!")

	def __call__(self, data):
		return self.handle_data(data)

	def __enter__(self):
		pass

	def __exit__(self, *args):
		return True

	def handle_data(self, data):
		link_data, title = self.parse_url(data)
		if title is None:
			return
		root, img_folder, downloaded = self.prepare_files(link_data, title)

		if USE_THREADS:
			self.init_threads(root, link_data, title)

		if not downloaded:
			for link, imgs in reversed(list(link_data.items())):
				for l_data in imgs:
					# file = ''.join(l for l in l_data['desc'] if l.isalnum() or l in "_-") + ".jpg"
					file = self.format_text(l_data['desc']) + ".jpg"
					folder = os.path.normpath(os.path.join(img_folder, self.format_text(l_data['path'])))
					if not os.path.exists(folder):
						os.mkdir(folder)
					path = os.path.join(folder, file)
					args = (l_data['url'], path, data['headers'])
					if USE_THREADS:
						self.que.put(args)
					else:
						self.ddl(*args)
				if USE_THREADS:
					self.que.put("UPDATE")
				else:
					self.create_archives(root, link_data, title)


		if USE_THREADS:
			self.event.set()
		else:			
			self.create_archives(root, link_data, title)

	def stop(self):
		for i in range(MAX_THREADS*2):
			self.que.put("STOP")

		print("Stopping...")

		alive_threads = lambda: list(filter(lambda e: e.is_alive(), self.threads))
		while len(alive_threads()) > 0:
			print(len(alive_threads()), "/", len(self.threads), "threads left")
			t = next(iter(alive_threads()), None)
			if t is not None:
				t.join()

		print("Done downloading")

		self.stop_event.set()
		self.event.set()
		for t in self.archive_threads:
			t.join()

	def init_threads(self, root, link_data, title):
		
		for i in range(max(0, MAX_THREADS - len(self.threads))):
			t = threading.Thread(target=self.ddl_thread_worker, daemon=True)
			t.start()
			self.threads.append(t)

		t = threading.Thread(target=self.archive_thread, args=(root, link_data, title), daemon=True)
		t.start()
		self.archive_threads.append(t)

	def prepare_files(self, link_data, title):
		link_count = sum(len(e) for e in link_data.values())
		print(link_count, 'links found, downloading...')

		root = os.path.join(OUTPUT, title)
		if not os.path.exists(root):
			os.mkdir(root)

		for sub in ("images", "archives"):
			path = os.path.join(root, sub)
			if not os.path.exists(path):
				os.mkdir(path)

		img_folder = os.path.join(root, "images")

		return root, img_folder, False

	def parse_url(self, data):
		link_data = {}
		if LOG_PARSE:
			print(f"Parsing url: {data['url']}")
		p = self.get(data['url'], h=data['headers'], force_url=True, no_cache=RELOAD_MAIN)
		if p is None:
			return {}, None

		if USE_PARSER == "lxml":
			p_tree = etree.ElementTree(lxml.html.fromstring(p))
			main_list = p_tree.xpath(data['xpth']['main_list'])[0]

			links = [c.xpath(data['xpth']['main_list_item'])[0] for c in main_list]
			if USE_DDL == "requests":
				links = [child.get('href') for child in links]
			elif USE_DDL == "selenium":
				links = [p_tree.getpath(child) for child in links]

			links = [urljoin(data['url'], l) for l in links]

			title = p_tree.xpath(data['title'])[0].text

		elif USE_PARSER == "bs4":
			p_soup = BeautifulSoup(p, 'html.parser')
			main_list = p_soup.find("li", {"id": "ceo_latest_comics_widget-3"}).ul.find_all("a")
			links = [child for child in main_list]
			if USE_DDL == "requests":
				links = [child['href'] for child in links]
			elif USE_DDL == "selenium":
				# TODO
				raise NotImplementedError("bs4 parser not implemented with selenium!")
			title = p_soup.title.text

		# title = ''.join(l for l in title if l.isalnum() or l in "_ -")
		title = self.format_text(title)

		last_log = time.time()
		for i, link in enumerate(links):
			l = self.get(link, h=data['headers'])
			if l is None:
				continue
	
			if LOG_PARSE and (time.time()-last_log > 5 or i == len(links)-1):
				print(f"Parsed: {i+1} / {len(links)}")
				last_log = time.time()

			if USE_PARSER == "lxml":
				l_tree = etree.ElementTree(lxml.html.fromstring(l))
				l_data = []
				root = l_tree.xpath(data['xpth']['img_list'])[0]
				for i, child in enumerate(root.xpath(data['xpth']['img_list_item'])):
					if child.tag == 'img':
						tmp = {
							'url': child.get(data['img_url']),
							'desc': str(i) + "-" + child.get(data['img_desc']),
							'path': f'Chapter {str(len(links) - len(link_data))}'
						} 

						l_data.append(tmp)
					else:
						print(link, child, child.tag)
						raise Exception

			elif USE_PARSER == "bs4":
				l_soup = BeautifulSoup(l, 'lxml')
				l_data = []
				for i, child in enumerate(l_soup.find("main").article.div.div.find_all("img")):
					l_data.append(
						{
							'url': child['src'],
							'desc': str(i) + "-" + child['alt'],
							'path': str(len(link_data))
						} 
					)

			if l_data == []:
				print(link, l_tree.xpath(data['xpth']['img_list'])[0].xpath(data['xpth']['img_list_item']))
				raise Exception
			link_data[link] = l_data

		return link_data, title

	def b64_hash(self, url):
		return base64.b64encode(url.encode("utf-8")).decode().replace('/', '_')

	def sha1_hash(self, url):
		return hashlib.sha1(url.encode("utf-8")).hexdigest()

	def get(self, url, h={}, force_url=False, no_cache=False):
		if USE_CACHE:
			if HASH_FUNCTION == "b64":
				url_hash = self.b64_hash(url)
			elif HASH_FUNCTION == "sha1":
				url_hash = self.sha1_hash(url)

			path = os.path.join("website_hashes", url_hash)

		if USE_CACHE and not no_cache and os.path.exists(path):
			with open(path, 'r', encoding="utf-8") as f:
				p = f.read()
			return p

		else:
			try:
				p = self.downloader.get(url, h, force_url=force_url)
				
			except Exception as e:
				print(f'Error on url: {url}: {e}')
				return None

			else:
				if USE_CACHE:
					with open(path, 'w', encoding="utf-8") as f:
						f.write(p)
				return p

	def ddl(self, url, path, h={}):
		if not os.path.exists(path):
			if LOG_DDL_FULL:
				print("Downloading:", url)
			if LOG_DDL:
				self.LOG_DDL_count += 1
				if time.time()-self.LOG_DDL_last > 5:
					print(f"Downloaded: {self.LOG_DDL_count} images ({path}: {url}")
					self.LOG_DDL_last = time.time()
					self.LOG_DDL_count = 0
			try:
				r = self.downloader.get(url, h=h, decode=False)
			except Exception as e:
				if url in str(e):
					print("Error:", e)
				else:
					print("Error on url:", url, "-", e)
			else:
				with open(path, 'wb') as f:
					f.write(r)

	def ddl_thread_worker(self):
		while True:
			data = self.que.get()
			if data == "STOP":
				return
			elif data == "UPDATE":
				self.event.set()
			else:
				self.ddl(*data)

	def create_archives(self, root, data, title):
		def create_thread(archive_path, imgs):
			with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as z:
				padding = len(str(len(imgs)))
				for i, l_data in enumerate(imgs):
					# file = ''.join(l for l in l_data['desc'] if l.isalnum() or l in "_-") + ".jpg"
					file = self.format_text(l_data['desc']) + ".jpg"
					folder = self.format_text(l_data['path'])
					path = os.path.join(img_folder, folder, file)
					arcname = str(i).zfill(padding) + '.jpg'
					z.write(path, arcname=arcname)

		threads = []
		all_exists = True

		img_folder = os.path.join(root, "images")
		for i, tmp in enumerate(reversed(list(data.items()))):
			link, imgs = tmp
			complete = True

			dirpath = os.path.join(
					img_folder, 
					self.format_text(imgs[0]['path']) # TODO - Do not crash if no img found
				)
			if not os.path.exists(dirpath):
				os.mkdir(dirpath)
				files = []
			else:
				files = os.listdir(dirpath)
			for l_data in imgs:
				# file = ''.join(l for l in l_data['desc'] if l.isalnum() or l in "_-") + ".jpg"
				file = self.format_text(l_data['desc']) + ".jpg"
				if file not in files:
					complete = False
					all_exists = False
					# print(f'{file} not in {files}')
					break

			if complete: # All files have been downloaded
				archive_path = os.path.join(root, "archives", f'{title}-{str(i+1).zfill(len(str(len(data))))}.cbz')
				if not os.path.exists(archive_path):
					if LOG_ARCHIVE:
						print(f"Writing archive {i+1}/{len(data)}: {archive_path}")
					t = threading.Thread(target=create_thread, args=(archive_path, imgs), daemon=True)
					threads.append(t)
					t.start()

		for t in threads:
			if t.is_alive():
				t.join()

		if all_exists:
			print("All archives created for title:", title, len(data.keys()))
		return all_exists

	def archive_thread(self, *args):
		global root	
		while not self.stop_event.is_set():
			stop = self.create_archives(*args)
			if stop or self.stop_event.is_set():
				break
			self.event.wait()

	def format_text(self, text):
		return ''.join(l for l in text if l.isalnum() or l in " _-")

class IteratorDownloader():
	def __init__(self, url, fields):
		self.url, self.fields = url, fields

		self.que = queue.Queue()
		self.archive_event = threading.Event()
		self.archive_thread = None
		self.stop = False
		self.threads = []
		self.avoid = {}

		if USE_DDL == "selenium":
			ddl = SeleniumDownloader
		elif USE_DDL == "requests":
			ddl = RequestsDownloader

		root, img_folder = self.prepare_files()

		with ddl() as self.downloader:
			self.init_threads(img_folder, root)

			for f in self.iterator():
				url = self.url.format(**f)
				file = self.get_filename(f)

				path = os.path.join(img_folder, file)
				args = (url, path, f)
				
				self.que.put(args)
			for i in range(max(1, MAX_THREADS)):
				self.que.put("STOP")

			self.download_all()
			self.create_archives(img_folder, root)

			self.finish()

	def __enter__(self):
		pass

	def __exit__(self, *args):
		return True

	def init_threads(self, img_folder, root):
		self.archive_thread = threading.Thread(target=self.archive_thread_worker, args=(img_folder, root), daemon=True)
		self.archive_thread.start()

		if USE_THREADS:
			for i in range(MAX_THREADS):
				t = threading.Thread(target=self.ddl_thread_worker, daemon=True)
				t.start()
				self.threads.append(t)

	def ddl(self, url, path, f, h={}):
		if not os.path.exists(path):
			if f['chapter'] in self.avoid and self.avoid[f['chapter']] < f['episode']:
				return "OUT"

			if self.stop:
				return "OUT"

			if LOG_DDL:
				print("Downloading:", url)
			try:
				r = self.downloader.get(url, h=h, decode=False)
			except requests.exceptions.HTTPError as e:
				if e.response is not None and e.response.status_code == 404:
					if f['chapter'] in self.avoid:
						if self.avoid[f['chapter']] > f['episode']:
							self.avoid[f['chapter']] = f['episode']
					else:
						print("Completed chapter:", f['chapter'])
						self.avoid[f['chapter']] = f['episode']

					return "OK"
				else:
					print("Error on url:", url, "-", e)
					if isinstance(e, NewConnectionError):
						return "CANCEL"
					return "ERROR"
			except Exception as e:
				print("Error on url:", url, "-", e)
			else:
				with open(path, 'wb') as file:
					file.write(r)

			return "OK"

	def ddl_thread_worker(self):
		while True:
			data = self.que.get()
			if data == "STOP":
				return
			status = self.ddl(*data)
			if status == "OK":
				self.archive_event.set()
			elif status == "RETRY":
				self.que.put(data)
			elif status == "CANCEL":
				self.stop = True
				break

	def create_archives(self, img_folder, root):
		files = os.listdir(img_folder)

		for chap, max_eps in list(self.avoid.items()):
			complete = True
			for eps in range(self.fields['episode'][0], max_eps):
				file = self.get_filename({'':fields['title'], 'chapter': chap, 'episode': eps})
				if file not in files:
					complete = False
					break
			if complete: # All files have been downloaded
				archive_path = os.path.join(root, "archives", f'{self.fields["title"]}-{chap}.cbz')
				if not os.path.exists(archive_path):
					if LOG_ARCHIVE:
						print(f"Writing archive: {archive_path}")
					with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as z:
						eps_padding = len(str(max_eps))
						for eps in range(self.fields['episode'][0], max_eps):
							file = f"{fields['title']}-chapter{str(chap).zfill(4)}-episode{str(eps).zfill(eps_padding)}.jpg"
							path = os.path.join(img_folder, file)
							z.write(path, arcname=file)

	def archive_thread_worker(self, *args):
		while not self.stop:
			self.archive_event.wait()
			self.create_archives(*args)
		self.create_archives(*args)

	def download_all(self):
		if not USE_THREADS:
			self.ddl_thread_worker()

	def prepare_files(self):
		root = os.path.join(OUTPUT, "iterator")
		if not os.path.exists(root):
			os.mkdir(root)

		for sub in ("images", "archives"):
			path = os.path.join(root, sub)
			if not os.path.exists(path):
				os.mkdir(path)

		img_folder = os.path.join(root, "images")

		return root, img_folder

	def get_filename(self, arg):
		return "-".join("".join(map(str, e)) for e in arg.items()) + ".jpg"

	def iterator(self):
		for chap in range(self.fields['chapter'][0], self.fields['chapter'][1]+1):
			for ep in range(self.fields['episode'][0], self.fields['episode'][1]+1):
				yield {'': fields['title'], 'chapter': chap, 'episode': ep}

	def finish(self):
		if len(self.threads) == 0:
			return

		for t in self.threads:
			t.join()

		print("Everything downloaded!")

		self.stop = True
		self.archive_thread.join()

class RequestsDownloader:
	def __init__(self):
		self.session = requests.Session()

	def get(self, url, h={}, decode=True, **_):
		r = self.session.get(url, headers=h, timeout=TIMEOUT)
		r.raise_for_status()
		
		out = r.content
		if decode:
			out = out.decode(encoding='UTF-8', errors='replace')

		return out

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.session.close()

class SeleniumDownloader:
	def __init__(self, *_):
		executable_path = r'C:\Program Files\geckodriver\geckodriver.exe'
		opts = webdriver.FirefoxOptions()
		# opts.headless = True
		self.driver = webdriver.Firefox(executable_path=executable_path,options=opts)
		self.driver.implicitly_wait(15)

	def __enter__(self):
		return self

	def get(self, url, *_, force_url=False):
		if force_url:
			self.driver.get(url)
		else:
			self.driver.back()
			self.driver.find_element(By.XPATH, url).click()

		return self.driver.page_source

	def __exit__(self, *args):
		self.driver.quit()


url = "https://lelscans.net/mangas/fairy-tail/{chapter:02d}/{episode}.jpg"
url = "https://lelscans.net/mangas/solo-leveling/{chapter}/{episode}.jpg"
fields = {
	"title": "Solo-Leveling",
	"chapter": (1, 179),
	"episode": (1, 100)
}

# with IteratorDownloader(url, fields) as i:
# 	pass

with MangaDownloader(data_list) as m:
	pass