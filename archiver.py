#!/usr/bin/env python
# -*- encoding: utf-8

import base64
import os
import re
import sys
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
        # Make sure there's a <meta charset="utf-8"> tag in the <head>,
        # because this uses UTF-8.
        soup = BeautifulSoup(html_string, 'html.parser')
        head = soup.find('head')
        for meta_tag in head.find('meta'):
            if 'charset' in meta_tag.attrs:
                break
        else:  # no break
            html_string = html_string.replace(
                '<head>', '<head><meta charset="utf-8">')

        html_string = self._archive_js_scripts(
            html_string=html_string,
            soup=soup,
            base_url=base_url)
        html_string = self._archive_style_tags(
            html_string=html_string,
            soup=soup,
            base_url=base_url)
        html_string = self._archive_link_tags(
            html_string=html_string,
            soup=soup,
            base_url=base_url)
        html_string = self._archive_img_tags(
            html_string=html_string,
            soup=soup,
            base_url=base_url)

        return html_string

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

    def _archive_js_scripts(self, html_string, soup, base_url):
        """
        Archive all the <script> tags in a soup.
        """
        for js_tag in soup.find_all('script'):
            if js_tag.attrs.get('type') != 'text/javascript':
                continue
            if js_tag.attrs.get('src') is None:
                continue

            resource_url = urljoin(base_url, js_tag['src'])

            resp = self._get_resource(resource_url)
            if resp is None:
                continue

            match = re.search(
                r'<script .*?src=(?P<qu>[\'"]?)%s(?P=qu)[^>]*></script>' % (
                    re.escape(js_tag['src'])), html_string
            )
            assert match is not None, js_tag['src']

            new_tag = soup.new_tag(name='script')
            new_tag.string = '\n' + resp.text.strip() + '\n'
            new_tag.attrs['type'] = 'text/javascript'
            html_string = html_string.replace(match.group(0), str(new_tag))
            assert match.group(0) not in html_string
        return html_string

    def _archive_style_tags(self, html_string, soup, base_url):
        """
        Archive all the <style> tags and style attributes in a soup.
        """
        for style_tag in soup.find_all('style'):
            orig_css_string = style_tag.string
            css_string = self.archive_css(orig_css_string, base_url=base_url)

            match = re.search(
                r'<style(?P<attrs>[^>]+)>\s*?%s\s*?</style>' % (
                    re.escape(orig_css_string)),
                html_string
            )
            assert match is not None, orig_css_string
            html_string = html_string.replace(
                match.group(0),
                '<style>\n' + css_string + '\n</style>'
            )
            assert match.group(0) not in html_string

        for desc in soup.descendants:
            try:
                if desc.attrs.get('style') is None:
                    continue
            except AttributeError:
                continue
            orig_css_string = desc.attrs['style']
            css_string = self.archive_css(orig_css_string, base_url=base_url)
            if orig_css_string != css_string:
                match = re.search(
                    r'style=(?P<quot>[\'"]?)%s(?P=quot)' % (
                        re.escape(orig_css_string)), html_string
                )
                assert match is not None, orig_css_string
                html_string = html_string.replace(
                    match.group(0), 'style=%s%s%s' % (
                        match.group('quot'), css_string, match.group('quot')))
                assert match.group(0) not in html_string

        return html_string

    def _archive_link_tags(self, html_string, soup, base_url):
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

            match = re.search(
                r'<link .*?href=(?P<quot>[\'"]?)%s(?P=quot)[^>]*>' % (
                    re.escape(link_tag['href'])), html_string
            )
            assert match is not None, link_tag['href']
            style_tag.string = '\n' + css_string + '\n'
            html_string = html_string.replace(match.group(0), str(style_tag))
            assert match.group(0) not in html_string

        return html_string

    def _archive_img_tags(self, html_string, soup, base_url):
        """
        Archive all the <img> tags in a soup.
        """
        for img_tag in soup.find_all('img'):
            if img_tag.get('src') is None:
                continue

            resource_url = urljoin(base_url, img_tag['src'])
            data = self._get_base64_encode(resource_url)

            match = re.search(
                r'<img .*?src=(?P<quot>[\'"]?)%s(?P=quot)[^>]*>' % (
                    re.escape(img_tag['src'])), html_string
            )
            assert match is not None, img_tag['src']
            img_tag['src'] = data
            html_string = html_string.replace(match.group(0), str(img_tag))
            assert match.group(0) not in html_string
        return html_string

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


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: %s <url>' % os.path.basename(__file__))
    archiver = HTMLArchiver()
    print(archiver.archive_url(sys.argv[1]))
