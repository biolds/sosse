import os
import re
from hashlib import md5
from time import sleep
from traceback import format_exc
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.db import models


class Document(models.Model):
    url = models.TextField(unique=True)
    title = models.TextField()
    content = models.TextField()

    def __str__(self):
        return self.url

    def _absolutize_url(self, p):
        if re.match('[a-zA-Z]+:', p):
            return p

        url = urlparse(self.url)

        if p.startswith('/'):
            new_path = p
        else:
            new_path = os.path.dirname(url.path)
            new_path += '/' + p

        url = url._replace(path=new_path)
        return url.geturl()

    def index(self, content):
        content = content.decode('utf-8')
        parsed = BeautifulSoup(content, 'html5lib')
        self.title = parsed.title.string or self.url

        text = ''
        for string in parsed.strings:
            s = string.strip(' \t\n\r')
            if s != '':
                if text != '':
                    text += '\n'
                text += s

        self.content = text

        # extract links
        for a in parsed.find_all('a'):
            url = self._absolutize_url(a.get('href'))
            UrlQueue.queue(url)

        for meta in parsed.find_all('meta'):
            if meta.get('http-equiv', '').lower() == 'refresh' and meta.get('content', ''):
                # handle redirect
                dest = meta.get('content')

                if ';' in dest:
                    dest = dest.split(';', 1)[1]

                if dest.startswith('url='):
                    dest = dest[4:]

                dest = self._absolutize_url(dest)
                UrlQueue.queue(dest)
                    

class QueueWhitelist(models.Model):
    url = models.TextField(unique=True)

    def __str__(self):
        return self.url


class UrlQueue(models.Model):
    url = models.TextField(unique=True)
    error = models.TextField(blank=True, default='')
    error_hash = models.TextField(blank=True, default='')

    def __str__(self):
        return self.url

    def set_error(self, err):
        self.error = err
        if err == '':
            self.error_hash = ''
        else:
            self.error_hash = md5(err.encode('utf-8')).hexdigest()

    @staticmethod
    def queue(url):
        for w in QueueWhitelist.objects.all():
            if url.startswith(w.url):
                break
        else:
            return

        UrlQueue.objects.get_or_create(url=url)

    @staticmethod
    def crawl():
        url = UrlQueue.objects.filter(error='').first()
        if url is None:
            return False

        try:
            print('(%i) %s ...' % (UrlQueue.objects.count(), url.url))

            doc, _ = Document.objects.get_or_create(url=url.url)
            if url.url.startswith('http://') or url.url.startswith('https://'):
                r = requests.get(url.url)
                r.raise_for_status()
                doc.index(r.content)

            doc.save()
                
            UrlQueue.objects.filter(id=url.id).delete()
        except Exception as e:
            url.set_error(format_exc())
            url.save()
            print(format_exc())
        return True
