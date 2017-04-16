html-archiver
=============

html-archiver is a Python module for creating a self-contained HTML archive
of a web page.  It inlines everything on the page – CSS, JavaScript, images –
so you have an entire copy of the page in a single file.

For a while I've used the `page archiving tool`_ on Pinboard, which takes a
similar approach: inline CSS and JavaScript, grab a local copy of images,
base64-encode certain elements.  I wrote this because I wanted a couple of
extra features:

*  A tool that didn't rely on a third-party service
*  Support for saving resources in ``url()`` values in CSS (e.g. webfonts)
*  A single-page output -- Pinboard saves images as separate files, and serves
   them alongside the HTML

It isn't perfect -- if you want a true archival copy, you'd be better off
saving all the resources individually, and mimicing the web server layout --
but this is really aimed at making quick and cheap copies.

.. _page archiving tool: https://pinboard.in/tour/#archive

Usage
*****

It can be invoked from the command line:

.. code-block:: console

   $ python3 html_archiver.py "http://example.org/foo/bar"

or from Python:

.. code-block:: python

   from html_archiver import HTMLArchiver

   a = HTMLArchiver()
   a.archive_url("http://example.org/foo/bar")

Features
********

html-archiver attempts to produce a self-contained HTML archive.  As well
as downloading the HTML from a page, it:

*  Downloads any CSS and JavaScript dependencies.  For example, the following:

   .. code-block:: html

      <link rel="stylesheet" type="text/css" href="/css/style.css">

      <script type="text/javascript" src="/js/app.js"></script>

   would be replaced with:

   .. code-block:: html

      <style>
        p { color: red; } ...
      </style>

      <script type="text/javascript">
        function hello_world() { console.log("Hello world!"); } ...
      </script>

*  Replaces any images with base64-encoded `data URIs`_.  For example, the
   following:

   .. code-block:: html

      <img src="/images/rainbow.jpg">

   would be replaced with:

   .. code-block:: html

      <img src="data:image/jpeg;base64,4QPaRXhp...">

   **Note:** This only works for images supplied in the ``src`` attribute;
   the ``srcset`` attribute is not supported.  See `issue #1`_

*  Any CSS rules that have a ``url()`` value are also replaced with
   base64-encoded data URIs.

*  For pages that require login, you can pass a custom ``Session`` object
   with appropriate cookies to ``HTMLArchiver``, and it will use that session
   to download the page.  For example:

   .. code-block:: python

      from archiver import HTMLArchiver
      from requests import Session

      sess = Session()
      sess.post('https://example.org/login', auth=('username', 'password'))

      archiver = HTMLArchiver(sess=sess)
      archiver.archive('https://example.org/logged_in_page')

.. _data URIs: https://en.wikipedia.org/wiki/Data_URI_scheme
.. _issue #1: https://github.com/alexwlchan/html-archiver/issues/1

Installation
************

Clone this repository and install dependencies with pip:

.. code-block:: console

   $ git clone https://github.com/alexwlchan/html-archiver.git
   $ cd html-archiver
   $ virtualenv env
   $ source env/bin/activate
   $ pip install -r requirements.txt

I develop and test against Python 2.7 and Python 3.3+.

Issues
******

If you find a bug, or a page that html-archiver misinterprets, please file an
issue `on the GitHub repo`_.

.. _on the GitHub repo: https://github.com/alexwlchan/html-archiver/issues/new


License
*******

MIT.
