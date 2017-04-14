#!/usr/bin/env python
# -*- encoding: utf-8

import base64
import os
import re
import warnings
from urllib.parse import urljoin, urlparse, unquote_plus

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


def archive_css(css_string, base_url):
    """
    Given a block of CSS, find any instances of the `url()` data type
    that refer to remote resources and replace them with base64-encoded data.
    """
    bad_urls = set()
    cached_resources = {}

    # It would be nice to do this with a proper CSS parser, but all the ones
    # I've tried are missing modern CSS features, e.g. ignore URIs in
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
        extension = os.path.splitext(urlparse(resource_url).path)[1]
        extension = extension[1:]  # Lose the leading .
        media_type = DATA_MEDIA_TYPES[extension]

        try:
            data = cached_resources[resource_url]
        except KeyError:
            if resource_url in bad_urls:
                continue
            import q; q.q(resource_url)
            resp = requests.get(resource_url, stream=True)
            if resp.status_code == 200:
                encoded_string = base64.b64encode(resp.raw.read())
                data = 'data:%s;base64,%s' % (
                    media_type, encoded_string.decode())
                cached_resources[resource_url] = data
            else:
                warnings.warn('Unable to save resource %r [%d]' % (
                    resource_url, resp.status_code))
                bad_urls.add(resource_url)
                continue

        css_string = css_string.replace(match.group('url'), data)

    return css_string
