import requests

url = 'http://192.168.1.1/ws'
myobj = {"service":"sah.Device.Information","method":"createContext","parameters":{"applicationName":"webui","username":"admin","password":"LukjTCEe"}}
x = requests.post(url, data = myobj)

print(x.text)

import requests
import json

url = 'http://192.168.1.1/ws'
payload = {"service":"sah.Device.Information","method":"createContext","parameters":{"applicationName":"webui","username":"admin","password":"LukjTCEe"}}
headers = {'Host': '192.168.1.1',
'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
'Accept': '*/*',
'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
'Accept-Encoding': 'gzip, deflate',
'Authorization': 'X-Sah-Login',
'Content-Type': 'application/x-sah-ws-4-call+json',
'Content-Length': '143',
'Origin': 'http://192.168.1.1',
'Connection': 'keep-alive',
'Referer': 'http://192.168.1.1/',
'Cookie': 'UILang=fr; lastKnownIpv6TabState=visible; e5068e88/accept-language=fr,fr-FR'}
r = requests.post(url, data=json.dumps(payload), headers=headers)
print(r.content)
