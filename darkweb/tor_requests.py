import requests
import json

proxies = {
    'http': 'socks5h://127.0.0.1:9150',
    'https': 'socks5h://127.0.0.1:9150'
}
headers = {
    'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36'
}

url = "http://donionsixbjtiohce24abfgsffo2l4tk26qx464zylumgejukfq2vead.onion/"
url = "http://underdiriled6lvdfgiw4e5urfofuslnz7ewictzf76h4qb73fxbsxad.onion/"
data = requests.get(url ,proxies=proxies, headers=headers).text

print(data)