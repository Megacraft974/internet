import multiprocessing
import os
import sqlite3
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image


class Lister:
    proxies = {
        'http': 'socks5h://127.0.0.1:9150',
        'https': 'socks5h://127.0.0.1:9150'
    }
    headers = {
        'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
    AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36'
    }
    def __init__(self) -> None:
        

        self.dbpath = 'onions.db'
        self.dbconnect()

        imgs = []
        # with open('onions.txt', 'r') as f:
        #     data = f.read().split('___')[0].split('\n')
        #     data = (url for url in data if url.strip() != '')
        #     with multiprocessing.Pool() as p:
        #         for p_out in p.map(self.parse_imgs, data):
        #             if p_out is None:
        #                 continue
        #             for img in p_out:
        #                 if img not in imgs:
        #                     imgs.append(img)
        # print(len(imgs), 'found')
        # with open('out.txt', 'w') as f:
        #     for img in imgs:
        #         f.write(img)
        #         f.write('\n')
        with open('out.txt', 'r') as f:
            imgs = f.read().split('\n')
        
        with multiprocessing.Pool() as p:
            p.map(self.download_img, imgs)
                
        
    def dbconnect(self, create=True):
        if create:
            if not os.path.exists(self.dbpath):
                self.dbcreate()
                return
        self.con = sqlite3.connect(self.dbpath)
        self.cur = self.con.cursor()

    def dbcreate(self):
        open(self.dbpath, 'w').close()
        self.dbconnect(create=False)

        commands = ('CREATE TABLE "onions" (\
                        "onion"	TEXT NOT NULL UNIQUE,\
                        "title"	TEXT,\
                        "tag"	TEXT,\
                        "desc"	TEXT\
                    );',)
        
        for c in commands:
            self.cur.execute(c)
        self.con.commit()

    def register_url(self, onion, title=None, tag=None, desc=None):
        sql = 'SELECT EXISTS(SELECT 1 FROM onions WHERE onion=?);'
        self.cur.execute(sql, (onion,))
        exists = bool(self.cur.fetchone()[0])
        if exists:
            return
        else:
            sql = 'INSERT INTO onions VALUES (?, ?, ?, ?)'
            self.cur.execute(sql, (onion, title, tag, desc))
            self.con.commit()

    @classmethod
    def get_url(cls, addr):
        print('-', addr)
        try:
            r = requests.get(addr, proxies=cls.proxies, headers=cls.headers, timeout=30)
        except:
            return None
        else:
            return r.text

    def parse_url(self, addr):
        page = self.get_url(addr)

    @classmethod
    def parse_imgs(cls, addr):
        out = []
        url_data = urlparse(addr)
        if url_data.path and len(url_data.path) > 1 and url_data.netloc:
            data = cls.parse_imgs(f'{url_data.scheme}://{url_data.netloc}')
            if data is not None:
                out.extend(data)
        data = cls.get_url(addr)
        if data is None:
            return
        soup = BeautifulSoup(data, 'html.parser')
        for img in soup.find_all('img'):
            link = urljoin(addr, img.get('src'))
            if link not in out:
                out.append(link)
        return out

    @classmethod
    def download_img(cls, addr):
        print('-', addr)
        try:
            r = requests.get(addr, proxies=cls.proxies, headers=cls.headers, timeout=30)
        except:
            return None
        else:
            url = urlparse(addr)
            file = os.path.basename(url.path)
            folder = os.path.join('imgs', url.netloc)
            file = os.path.join(folder, file)
            
            if not os.path.exists(folder):
                os.mkdir(folder)
            
            with open(file, 'wb') as f:
                f.write(r.content)

if __name__ == "__main__":
    Lister()
