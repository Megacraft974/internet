"""
Very simple tool, get links from a file and successively open them in a web browser
"""
import requests
import threading
import os
import re
import webbrowser

filepath = os.path.expanduser('~/AppData/Roaming/.minecraft/mods/Hidden/modpack/modpack.txt')
root = os.path.dirname(os.path.abspath(filepath))
max_threads = 1
headers = {
    'Host': 'www.curseforge.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

def ddl_thread(url, thread=False):
    if not thread:
        t = threading.Thread(target=ddl_thread, args=(url, True))
        t.start()
        return t

    try:
        print('---------')
        r = requests.get(url, allow_redirects=True, headers=headers)
        print('---------E', r.status_code)
    except Exception as e:
        print(e)
    else:
        filename = None
        cd = r.headers.get('content-disposition')
        if cd is not None:
            search = re.findall('filename=(.+)', cd)
            if len(search) > 0:
                filename = search[0]

        if filename is None:
            print('No filename', url)
            return
            filename = url.split('/')[-1]

        print(url, filename)
        filepath = os.path.join(root, filename)
        with open(filepath, 'wb') as f:
            f.write(r.content)

threads = []
with open(filepath, 'r') as f:
    for line in f:
        if line == '' or not ' - ' in line:
            continue
        project, url = line.replace('\n', '').split(' - ')
        if url.startswith('https://www.curseforge.com/'):
            url += '/file'
        webbrowser.open(url)
        input('Next')

print('Done')