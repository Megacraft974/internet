import requests
from requests.exceptions import *
import json
import os
from datetime import datetime

base_url = "http://localhost"
# base_url = "https://tetrazero.com"

def add_task(name, type, data):
	url = base_url + "/cgi-bin/tasks.py?action=add"
	url += "&name=" + name
	url += "&type=" + type
	url += "&data=" + data

	print(url)
	print(requests.get(url).content)

def delete_task(created):
	url = base_url + "/cgi-bin/tasks.py?action=delete"
	url += "&created=" + created

	print(url)
	print(requests.get(url).content)

if os.path.exists("last_tasks"):
	with open("last_tasks", 'r') as f:
		last_tasks = json.load(f)
else:
	last_tasks = {"date":datetime.now().isoformat()}

# add_task("add_torrent", "torrent", "some_url")
# add_task("add_torrent", "torrent", "some_other_url")
# add_task("start_an_app", "app_start", "app_name_2")
# delete_task("2022-02-20T19:57:19.593475")

last_tasks = {"date":datetime.now().isoformat()}
print(last_tasks)
# url = "https://tetrazero.com/cgi-bin/tasks.py?since=" + last_tasks["date"]
url = base_url + "/cgi-bin/tasks.py?action=get&since=" + last_tasks["date"]
print(url)
try:
	r = requests.get(url)
	r.raise_for_status()
except HTTPError as e:
	print(e)
except Exception:
	raise

print(r.content)