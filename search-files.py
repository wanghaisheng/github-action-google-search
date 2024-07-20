import os
import re
import sys
import logging
import asyncio
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from tldextract import extract
from urllib.parse import urlparse, unquote
from datetime import datetime, timedelta

# Disable warnings for SSL verification
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("tldextract").setLevel(logging.CRITICAL)

class PyMeta:
    def __init__(self, search_engine, target, file_type, timeout, conn_timeout=3, max_results=50, max_concurrent_requests=5):
        self.search_engine = search_engine
        self.file_type = file_type.lower()
        self.conn_timeout = conn_timeout
        self.max_results = max_results
        self.timeout = timeout
        self.target = target
        self.results = []
        self.regex = re.compile(r"https?://[^\)]+{}[^\)]+\." + self.file_type.format(self.target))
        self.url = {
            'google': 'https://www.google.com/search?q=site:{}+filetype:{}&num=100&start={}',
            'bing': 'http://www.bing.com/search?q=site:{}%20filetype:{}&first={}'
        }
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def search(self):
        async with ClientSession() as session:
            tasks = []
            for start in range(0, self.max_results, 100):
                tasks.append(self.fetch_and_parse(session, self.url[self.search_engine].format(self.target, self.file_type, start)))

            await asyncio.gather(*tasks)

    async def fetch_and_parse(self, session: ClientSession, url: str):
        async with self.semaphore:
            try:
                async with session.get(url, timeout=self.conn_timeout) as response:
                    if response.status != 200:
                        logging.warning(f'Failed to fetch {url}: {response.status}')
                        return

                    page_content = await response.text()
                    self.page_parser(page_content)
            except Exception as e:
                logging.error(f'Error fetching {url}: {str(e)}')

    def page_parser(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        for link in soup.find_all('a', href=True):
            self.results_handler(link)

    def results_handler(self, link):
        url = str(link['href'])
        if self.regex.match(url):
            self.results.append(url)
            logging.debug(f'Added URL: {url}')

def main():
    search_engine = 'google'  # Or 'bing'
    target = 'example'  # Example search term
    file_type = 'pdf'  # Desired file type
    timeout = 30  # Timeout in seconds

    pymeta = PyMeta(search_engine, target, file_type, timeout)
    asyncio.run(pymeta.search())

if __name__ == "__main__":
    main()
