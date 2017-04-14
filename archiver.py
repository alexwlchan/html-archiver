#!/usr/bin/env python
# -*- encoding: utf-8

import base64
import os
import re
import warnings
from urllib.parse import urljoin, urlparse, unquote_plus

from bs4 import BeautifulSoup
import requests


DATA_MEDIA_TYPES = {
    'png': 'image/png',
    'gif': 'image/gif',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'svg': 'image/svg-xml',
    'woff': 'application/font-woff',
    'woff2': 'font/woff2',
    'eot': 'font/eot',
    'ttf': 'font/ttf',
}


class HTMLArchiver:

    def __init__(self, sess=None):
        if sess is None:
            self.sess = requests.Session()

        #: URLs for resources we've tried to cache but failed
        self.bad_urls = set()

        #: Cached resources
        self.cached_resources = {}

    def archive_url(self, url):
        """
        Given a URL, return a single-page HTML archive.
        """
        return self.archive_html(self.sess.get(url).text, base_url=url)

    def archive_html(self, html_string, base_url):
        """
        Given a block of HTML, return a single-page HTML archive.
        """
        soup = BeautifulSoup(html_string, 'html.parser')

        # Make sure there's a <meta charset="utf-8"> tag in the <head>,
        # because this uses UTF-8.
        head = soup.find('head')
        for meta_tag in head.find('meta'):
            if 'charset' in meta_tag.attrs:
                break
        else:  # no break
            meta_tag = soup.new_tag(name='meta')
            meta_tag.attrs['charset'] = 'utf-8'
            head.insert(0, meta_tag)

        soup = self._archive_js_scripts(soup, base_url=base_url)
        soup = self._archive_style_tags(soup, base_url=base_url)
        soup = self._archive_link_tags(soup, base_url=base_url)
        soup = self._archive_img_tags(soup, base_url=base_url)

        return str(soup)

    def _get_resource(self, url):
        if url in self.bad_urls:
            return None
        try:
            return self.cached_resources[url]
        except KeyError:
            resp = self.sess.get(url, stream=True)
            if resp.status_code == 200:
                self.cached_resources[url] = resp
                return self.cached_resources[url]
            else:
                warnings.warn(
                    'Unable to fetch %r [%d]' % (url, resp.status_code)
                )
                self.bad_urls.add(url)
                return None

    def _get_base64_encode(self, url):
        extension = os.path.splitext(urlparse(url).path)[1]
        extension = extension[1:]  # Lose the leading .
        try:
            media_type = DATA_MEDIA_TYPES[extension]
        except KeyError:
            warnings.warn('Unable to determine media_type for %r' % url)
            return None

        resp = self._get_resource(url)
        if resp is None:
            return None
        encoded_string = base64.b64encode(resp.raw.read())
        return 'data:%s;base64,%s' % (media_type, encoded_string.decode())

    def _archive_js_scripts(self, soup, base_url):
        """
        Archive all the <script> tags in a soup.
        """
        for js_tag in soup.find_all('script'):
            if js_tag.attrs.get('type') != 'text/javascript':
                continue
            if js_tag.attrs.get('src') is None:
                continue

            new_tag = soup.new_tag(name='script')
            resource_url = urljoin(base_url, js_tag.attrs['src'])

            resp = self._get_resource(resource_url)
            if resp is None:
                continue

            new_tag.string = '\n' + resp.text.strip() + '\n'
            new_tag.attrs['type'] = 'text/javascript'
            js_tag.replace_with(new_tag)
        return soup

    def _archive_style_tags(self, soup, base_url):
        """
        Archive all the <style> tags in a soup.
        """
        for style_tag in soup.find_all('style'):
            css_string = style_tag.string
            css_string = self.archive_css(css_string, base_url=base_url)
            style_tag.string = css_string
        return soup

    def _archive_link_tags(self, soup, base_url):
        """
        Archive all the <link> tags in a soup.
        """
        for link_tag in soup.find_all('link', attrs={'rel': 'stylesheet'}):
            if link_tag.get('href') is None:
                continue
            if not link_tag['href'].endswith('.css'):
                continue

            style_tag = soup.new_tag(name='style')
            resource_url = urljoin(base_url, link_tag['href'])

            resp = self._get_resource(resource_url)
            if resp is None:
                continue

            css_string = resp.text.strip()
            css_string = self.archive_css(css_string,
                base_url=link_tag['href'])
            style_tag.string = '\n' + css_string + '\n'
            link_tag.replace_with(style_tag)
        return soup

    def _archive_img_tags(self, soup, base_url):
        """
        Archive all the <img> tags in a soup.
        """
        for img_tag in soup.find_all('img'):
            if img_tag.get('src') is None:
                continue

            resource_url = urljoin(base_url, img_tag['src'])
            data = self._get_base64_encode(resource_url)
            img_tag['src'] = data
        return soup

    def archive_css(self, css_string, base_url):
        """
        Given a block of CSS, find any instances of the `url()` data type
        that refer to remote resources and replace them with
        a base64-encoded data URI.
        """
        # It would be nice to do this with a proper CSS parser, but all the
        # ones I've tried are missing modern CSS features, e.g. ignore URIs in
        # a @font-face rule.
        for match in re.finditer(r'url\((?P<url>[^\)]+)\)', css_string):
            resource_url = match.group('url')
            resource_url = resource_url.strip('"').strip("'")

            # Something to do with SVG resources that are identified elsewhere
            # in the stylesheet
            resource_url = unquote_plus(resource_url)
            if resource_url.startswith('#'):
                continue

            # Any existing data: URIs are already self-contained and don't
            # need changing.
            if resource_url.startswith('data:'):
                continue

            # Determine the media type for the data: URI
            resource_url = urljoin(base_url, resource_url)
            data = self._get_base64_encode(resource_url)
            if data is not None:
                css_string = css_string.replace(match.group('url'), data)

        return css_string
