This project is exported from google code:https://code.google.com/p/pydelicious/source/checkout
but since old delicious api stop working now, I'm trying to fix it.
If you have an good idea, it is free to send a pull request.


pydelicious
===========
From del.icio.us to Python. Based on work done by Frank Timmermann\ [#]_. 
See `license.txt`__.

Installation::

    % python setup.py install

And either import the (documented) class::

  >>> from pydelicious import DeliciousAPI
  >>> api = DeliciousAPI('username', 'password', 'encoding')

or use the functions on the module, listed below.
Please do `report <http://code.google.com/p/pydelicious/issues/>`_ any bugs.

Overview
--------
Access to the del.icio.us web service API is implemented in `pydelicious.py`__.
In addition the script `tools/dlcs.py`__ can manage a local collection of 
bookmarks. 

The **API class** can be used directly::

  >>> from pydelicious import DeliciousAPI; from getpass import getpass
  >>> pwd = getpass('Pwd:')
  Pwd:
  >>> a = DeliciousAPI('user', pwd)
  >>> # Either succeeds or raises DeliciousError or subclass:
  >>> a.posts_add("http://my.com/", "title", extended="description", tags="my tags")
  >>> len(a.posts_all()['posts'])
  1
  >>> a.tags_get() # or: a.request('tags/get')
  {'tags': [{'count': '1', 'tag': 'my'}, {'count': '1', 'tag': 'tags'}]}
  >>> a.posts_update()
  {'update': {'time': (2008, 11, 28, 2, 35, 51, 4, 333, -1)}}
  >>> # Either succeeds or raises DeliciousError or subclass:
  >>> a.posts_delete("http://my.com/")
  >>> len(a.posts_all()['posts'])
  0

Or by calling one of the methods on the module. These are functions
that wrap common API calls. The signature is ``'user', 'passwd'`` followed by 
the API method arguments.

- `add(usr, passwd, url, title) <./doc/pydelicious.html#-add>`__
- `get(usr, passwd, url) <./doc/pydelicious.html#-get>`__
- `get_update(usr, passwd) <./doc/pydelicious.html#-get_update>`__
- `get_all(usr, passwd) <./doc/pydelicious.html#-get_all>`__
- `get_tags(usr, passwd) <./doc/pydelicious.html#-get_tags>`__
- `delete(usr, passwd, url) <./doc/pydelicious.html#-delete>`__
- `rename_tag(usr, passwd, old, new) <./doc/pydelicious.html#-rename_tag>`__

These are short functions for `getrss`__ calls:

- `get_popular(tag) <./doc/pydelicious.html#-get_popular>`__
- `get_userposts(user) <./doc/pydelicious.html#-get_userposts>`__
- `get_tagposts(tag) <./doc/pydelicious.html#-get_tagposts>`__
- `get_urlposts(url) <./doc/pydelicious.html#-get_urlposts>`__

__ : ./doc/pydelicious.html#-getrss


Documentation
-------------
For code documentation see `doc/pydelicious`__ or `doc/dlcs.py`__.
For TODO's, progress reports, etc. see `HACKING`__.

Note that for non-pydelicious related questions there is also a
`del.icio.us user discussion list at yahoo`__.

Historical
----------
Originally written by Frank Timmermann and hosted at:
<http://deliciouspython.python-hosting.com/> (defunkt).

----

.. [#] Google Code, ``pydelicious`` (http://code.google.com/p/pydelicious/).

.. __: ./license.txt
.. __: ./pydelicious.py
.. __: ./tools/dlcs.py
.. __: ./doc/pydelicious.html
.. __: ./doc/dlcs.html
.. __: ./HACKING.rst
.. __: http://tech.groups.yahoo.com/group/ydn-delicious/
