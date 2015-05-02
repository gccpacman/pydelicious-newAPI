#!/usr/bin/env python
#
# This file is in the public domain.
import sys
try:
    # distutils extension (non-stdlib)
    from setuptools import setup, Command
except:
    from distutils.core import setup
    Command = None
import pydelicious


requires = ['feedparser']
if sys.version[0] == 2 and sys.version[1] <= 4:
    requires += [ 'elementtree >= 1.2' ]
elif sys.version[0] == 2 and sys.version[1] >= 5:
    # integrated into the standard library as xml.etree.*
    pass 

distopts = dict(
    name = 'pydelicious',
    version = pydelicious.__version__,
    license = pydelicious.__license__,
    description = pydelicious.__description__,
    long_description = pydelicious.__long_description__,

    author = pydelicious.__author__,
    author_email = pydelicious.__author_email__,
    url = pydelicious.__url__,

    requires = requires,
)

if Command:

    class Test(Command):
        """Distutils Command to run API tests"""

        description = 'Run pydelicious API tests.'
        user_options = []

        def initialize_options(self): pass
        def finalize_options(self): pass

        def run(self):
            from tests import main
            main.test_api()

    # TODO: need to see this work...
    #dependency_links = [
    #    "http://feedparser.org/feedparser.py#egg=feedparser-latest"
    #]

    distopts.update(dict(
        cmdclass = {
            'test': Test,
        },
        packages = ['pydelicious','pydelicious.tools'],
        package_dir = { 
            'pydelicious': 'pydelicious',
            'pydelicious.tools': 'tools' },
        # setuptools dist.opts extensions:
        install_requires = requires,
        entry_points = {
            'console_scripts': [
                'dlcs = pydelicious.tools.dlcs:_main',
                'dlcs_feeds = pydelicious.tools.dlcs_feeds:_main'
            ]
        }
    ))

else:

    print >>sys.stderr,'no setuptools detected, proceeding without installing `dlcs`'

    distopts.update(dict(
        packages = ['pydelicious'],
        package_dir = { 'pydelicious': 'pydelicious' },
        #provides = 'pydelicious (%s)' % (pydelicious.__version__)
        # FIXME: what class for distutils?
        cmdclass = {},
        scripts = ['tools/dlcs.py'], # FIXME: but how to get it on PATH?
    ))


setup(**distopts)

