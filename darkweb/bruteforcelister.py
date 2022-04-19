#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import os
import multiprocessing
import time
import re
import requests
import string

class AddressLister:
    def __init__(self):
        self.validChars = list(string.ascii_lowercase) + [str(x) for x in range(2, 8)]
        self.addressLength = 56
        self.tld = ".onion"
        self.prefix = ''
        self.timeout = 5
        self.workers = os.cpu_count()
        self.verbose = 1
        self.chunksize = 2
        self.proxies = {
            'http': 'socks5h://127.0.0.1:9150',
            'https': 'socks5h://127.0.0.1:9150'
        }
        self.headers = {
            'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
        AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36'
        }
        self.filename = "sites.txt"

        self.title_pattern = re.compile("<title.*?>(.+?)</title>", re.IGNORECASE)

    def start_pools(self, start = ''):
        addresses = self.addressGenerator(start)
        c = 0
        last = time.time()
        with multiprocessing.Pool(self.workers) as p:
            for lvl, e in p.imap(self.addressesChecker, addresses, self.chunksize):
                if c & 0xFFF == 0:
                    speed = c / (time.time() - last)
                    print(e + ' - ' + str(round(speed,2)) + ' links/sec')
                    c = 1
                    last = time.time()
                else:
                    c += 1
                if lvl is not None and self.verbose >= lvl:
                    print(e + '\n', end="")
        p.join()
        
    # Gets site title if site is up
    def getSiteTitle(self, addr):
        try:
            r = requests.get(addr, proxies=self.proxies, headers=self.headers, 
                            timeout=self.timeout).text
            try:
                title = re.findall(self.title_pattern,r)[0]
            except IndexError:
                title = ""
            return title
        except:
            return None

    def checkSite(self, addr):
        try:
            r = requests.head(addr, proxies=self.proxies, headers=self.headers, 
                            timeout=self.timeout)
            assert r.status_code < 400
        except:
            return False
        else:
            return True

    def addressGenerator(self, start):
        def generator(start):
            if len(start) == self.addressLength:
                yield start
                return

            for l in self.validChars:
                for addr in generator(start + l):
                    yield addr

        for addr in generator(start):
            yield 'http://' + addr + self.tld

    def addressesChecker(self, address):
        if self.checkSite(address):
            title = self.getSiteTitle(address)
            if self.verbose >= 1:
                return (1, "Found site " + address)
            with open(self.filename, "a") as myfile:
                # Getting current date and time
                n = datetime.datetime.now()
                # Creating a standard string
                addrStr = str(n) + " " + address + " " + title + "\n"
                # Writing to our file
                myfile.write(addrStr)
        else:
            if self.verbose >= 2:
                return (2, address + " is down!")
        return (None, address)

if __name__ == '__main__':
    m = AddressLister()
    start = ''
    m.start_pools(start)