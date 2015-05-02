#!/usr/bin/env python
"""dlcs - Manage a del.icio.us bookmark collection from the command-line.


Overview
--------
`dlcs` is a simple wrapper around pydelicious.DeliciousAPI. If offers
some facilities to get data from your online bookmark collection and
to perfom operations. See::

    % dlcs --help

This tool enables quick access but the server communication may be slow and
when doing multiple expensive requests del.icio.us may throttle you and
return 503's. This all depends on your collection size (posts/tags/bundles)
ofcourse. In any case, the post and tag lists are stored locally and some
changes to your collection may not be noticed until you clear this cache
since posts/update does not notice any edits.

Quickstart
----------
Just start `dlcs` using::

    % dlcs -u <username>

Post any URL using::

    % dlcs postit <URL>

Configuration
-------------
Your username and password can be stored in an INI formatted configuration
file under the section name 'dlcs'. The default location is ~/.dlcs-rc
but this can be changed using command line options. If no username or
password are provided `dlcs` will guess the username and prompt for the
password.

Limitation
----------
- Bundle sizes are restricted by the maximum URL size [xxx:length?], the
  del.icio.us interface allows bigger bundles.

Integration
-----------
When using curses based browsers you may have to miss the javascript
bookmarklets since most TUI browsers don't support these. That is why dlcs 
has a command `postit` that takes the URL and fires up your favorite editor 
to offer the same functionality.

To bookmark HTTP URLs with lynx, put the following line in your lynx.cfg::

    EXTERNAL:http:dlcs postit %s

For the elinks browser, create a uri_passing rule in the configuration file.
Something like the following::

    set document.uri_passing.dlcs = "bash -c \"dlcs postit %c\""

License
-------
Same as `pydelicious`, FreeBSD or Simplified BSD license.
See license.txt for details and the copyright holders.

TODO
----
- adapt to new meta attr's
- catch DeliciousErrors
- Output formatting (--outf)
- Pretty JSON printer
- Append recent posts (and tags) to cache
- Some intelligent statistics on the tag collection (tag size, usage)
- Other users, is it possible to: list all posters for a URL, all tags for a URL? Popular tags?
- There are no commands to work on date lists (but 'req' could)
- Tag relations,
- Tag value, could a simple algorithm weigh the value of a specific tag (combination)?
"""
import sys
import os
import optparse
import getpass
import time
import locale
import codecs
import math
from os.path import expanduser, getmtime, exists, abspath
from ConfigParser import ConfigParser
import pydelicious
from pydelicious import DeliciousAPI, dlcs_parse_xml, PyDeliciousException, \
    dlcs_feed
from pprint import pformat    

try:
    # Python >= 2.4
    assert set and frozenset
except AssertionError:
    # Python < 2.6
    from sets import Set as set

try:
    # Python >= 2.5
    from hashlib import md5
except ImportError:
    from md5 import md5

try:
    from simplejson import dumps as jsonwrite, loads as jsonread
except:
    try:
        from json import read as jsonread, write as jsonwrite
    except:
        print >>sys.stderr, "No JSON decoder installed"


__cmds__ = [
    'bundle',
    'bundleadd',
    'bundleremove',
    'bundles',
    'clearcache',
    'deletebundle',
    'deleteposts',
    'findposts',
    'findtags',
    'getbundle',
    'getposts',
    'gettags',
    'help',
    'info',
    'mates',
    'post',
    'postit',
    'posts',
    'postsupdate',
    'recent',
    'rename',
    'req',
    'stats',
    'tag',
    'tags',
    'tagged',
    'untag',
]


DEBUG = 0
if 'DLCS_DEBUG' in os.environ:
    DEBUG = int(os.environ['DLCS_DEBUG'])
    pydelicious.DEBUG = DEBUG

if 'DLCS_CONFIG' in os.environ:
    DLCS_CONFIG = os.environ['DLCS_CONFIG']
elif exists(abspath('./.dlcs-rc')):
    DLCS_CONFIG = abspath('./.dlcs-rc')
else:
    DLCS_CONFIG = expanduser('~/.dlcs-rc')

NEW_CONFIG = not os.path.exists(DLCS_CONFIG)

ENCODING = locale.getpreferredencoding()

__usage__ = """%prog [options] [command] [args...] """ + """
command can be one of:
 %s

Use `help [command]` to get more information about a command."""\
    % (", ".join(__cmds__))

__options__ = [
    (('-c', '--config'), {"default":DLCS_CONFIG,
      "help":"Use custom config file [%%default%s]" % 
      {False:'',True:' (new)'}[NEW_CONFIG]}),
    (('-C', '--keep-cache'), {'dest':'keep_cache','action':'store_true','default':False,
        'help':"Don't update locally cached file(s) if they're out of date."}),
    (('-e', '--encoding'),{'default':ENCODING,
        'help':"Use custom character encoding [locale: %default]"}),
    (('-u', '--username'),{
        'help':"del.icio.us username (defaults to config or loginname)"}),
    (('-p', '--password'),{
        'help':"Password for the del.icio.us user (usage not recommended, but this will override the config)"}),
    (('-I', '--ignore-case'),{'dest':'ignore_case','action':'store_true','default':False,
        'help':"Ignore case for string searches"}),
    (('-d', '--dump'),{'default':False,
        'help':"Dump entire response (`req` only)"}),
    (('-o', '--outf'),{'choices':['text','json','prettyjson'],'default':'text',
        'help':"Output formatting"}),
    (('-s', '--shared'),{'default':True,
        'help':"When posting a URL, set the 'shared' parameter."}),
    (('-r', '--replace'),{'default':False,
        'help':"When posting a URL, set the 'replace' parameter."}),
    (('-v', '--verboseness'),{'default':0,
        'help':"TODO: Increase or set DEBUG (defaults to 0 or the DLCS_DEBUG env. var.)"})
]

def parse_argv_split(options, argv, usage="%prog [args] [options]"):
    """Parse argument vector to a tuple with an arguments list and an
       option dictionary.
    """
    parser = optparse.OptionParser(usage)

    optnames = []
    has_default = []
    for opt in options:
        parser.add_option(*opt[0], **opt[1])
        # remember destination name
        if 'dest' in opt[1]:
            optnames.append(opt[1]['dest'])
        else:
            optnames.append(opt[0][1][2:]) # strip dest. name from long-opt
        # remember opts with defaults (in case def. is neg.)
        if 'default' in opt[1]:
            has_default.append(optnames[len(optnames)-1])

    optsv, args = parser.parse_args(argv)

    # create dictionary for opt values by using dest. names
    opts = {}
    for name in optnames:
        v = getattr(optsv, name)
        if v or name in has_default:
            opts[name] = v

    return parser, opts, args

def prettify_json(json, level=0):

    """Formats a JSON string to separated, indented lines.
    """
    #TODO: prettify json
    return json

    lines = []
    prefix = '\t'*level
    line_buffer = ''

    for c in json:
        if c in ',':
            lines.append(prefix + line_buffer + c)
            line_buffer = ''

        elif c in '[{(':
            for line in prettify_json:
                lines.append()

        else:
            line_buffer += c

    return "\n".join(lines)

# TODO: write output formatting for text
def output_text(data):
    return "\n\n".join([txt_post(p) for p in data])

def output_rst(data):
    return "\n\n".join([rst_post(p) for p in data])

def output_json(data):
    return jsonwrite(data)

def output_prettyjson(data):
    return prettify_json(jsonwrite(data))

def output(cmd, opts, data):
    return data
    #TODO:
    #return globals()['output_'+opts['outf']](data)

# Debugwrappers
def shortrepr(object):
    if type(object) is type([]):
        return "[" + ", ".join(map(shortrepr, object)) + "]"
    elif type(object) is type(()):
        return "(" + ", ".join(map(shortrepr, object)) + ")"
    elif type(object) is type(''):
        if len(object) > 20: return repr(object[:20]) + "..."
        else: return repr(object)
    else:
        return str(object)

debugindent = {}
debugmidline = {}

class MethodWrapper:
    def __init__(self, name, method, base, log):
        self.name = name
        self.method = method
        self.base = base
        self.log = log

    def __call__(self, *args):
        indent = debugindent[self.log]
        if debugmidline[self.log]:
            self.log.write("\n")

        self.log.write("%s%s \x1b[32m%s\x1b[0m%s: " %
                       (indent, repr(self.base), self.name, shortrepr(args)))
        self.log.flush()
        debugmidline[self.log] = 1

        debugindent[self.log] = indent + "  "

        try:
            result = apply(self.method, args)

            if not debugmidline[self.log]:
                basename = self.base.__class__.__name__
                self.log.write("%s%s.\x1b[32m%s\x1b[0m: " %
                               (indent, basename, self.name))
            self.log.write("\x1b[36m%s\x1b[0m\n" % shortrepr(result))
            self.log.flush()
            debugmidline[self.log] = 0

        finally:
            debugindent[self.log] = indent
        return result

class DebugWrapper:
    def __init__(self, base, log):
        self.__dict__["__base__"] = base
        self.__dict__["__log__"] = log
        if not debugindent.has_key(log):
            debugindent[log] = ""
            debugmidline[log] = 0

    def __getattr__(self, name):
        base = self.__dict__["__base__"]
        log = self.__dict__["__log__"]
        value = getattr(base, name)
        if callable(value) and name[:2] != "__":
            return MethodWrapper(name, value, base, log)
        else:
            return value

    def __setattr__(self, name, value):
        base = self.__dict__["__base__"]
        setattr(base, name, value)


### Main

def main(argv):

    """This will prepare al input data and call a command function to perform
    the operations. Default command is `info()`.

    Configuration file is loaded and used to store username/password.
    """

    global DEBUG

    if not argv:
        argv = sys.argv[1:]

    ### Parse argument vector
    optparser, opts, args = parse_argv_split(__options__, argv, __usage__)

    if opts['verboseness']:
        v = int(opts['verboseness'])
        DEBUG = v
        pydelicious.DEBUG = v

    # First argument is command
    if len(args) > 0:
        cmdid = args.pop(0)
    else:
        cmdid = 'info'

    if not cmdid in __cmds__:
        optparser.exit("Command must be one of %s" % ", ".join(__cmds__))

    ### Parse config file
    conf = ConfigParser()
    conf_file = opts['config']
    # reads whatever it can or nothing:
    conf.read(conf_file)

    # Check for section and initialize using options if needed
    if not 'dlcs' in conf.sections():
        # initialize a new configuration?
        if not 'username' in opts:
            opts['username'] = os.getlogin()

        if not 'password' in opts:
            opts['password'] = getpass.getpass("Password for %s: " % opts['username'])

        conf.add_section('dlcs')
        conf.set('dlcs', 'username', opts['username'])

        v = raw_input("Save password to config (%s)? [Y]es/No: " % conf_file)
        if v in ('y','Y',''):
            conf.set('dlcs', 'password', opts['password'])

        conf.write(open(conf_file, 'w'))

    if not 'local-files' in conf.sections():        
        # Other default settings:
        conf.add_section('local-files')
        conf.set('local-files', 'tags', expanduser("~/.dlcs-tags.xml"))
        conf.set('local-files', 'posts', expanduser("~/.dlcs-posts.xml"))
        conf.write(open(conf_file, 'w'))
    #return "Config written. Just run dlcs again or review the default config first."


    ### Merge config items under 'dlcs' with opts
    # conf provides defaults, command line options override
    options = dict(conf.items('dlcs'))
    options.update(opts)

    if not 'password' in options:
        options['password'] = getpass.getpass("Password for %s: " % options['username'])


    # Force output encoding
    sys.stdout = codecs.getwriter(options['encoding'])(sys.stdout)
    # TODO: run tests, args = [a.decode(options['encoding']) for a in args]

    # DeliciousAPI instance to pass to the command functions
    dlcs = DeliciousAPI(options['username'], options['password'],
        codec=options['encoding'])

    # TODO: integrate debugwrapper if DEBUG:
    if DEBUG > 2:
        dlcs = DebugWrapper(dlcs, sys.stderr)

    ### Defer processing to command function
    cmd = getattr(sys.modules[__name__], cmdid)
    try:
        return cmd(conf, dlcs, *args, **options)
    except PyDeliciousException, e:
        print >> sys.stderr, e
    except pydelicious.DeliciousError, e:
        print >> sys.stderr, e

### Command functions

def help(conf, dlcs, cmd='', **opts):

    """Prints the docstring for a command or DeliciousAPI method.
    """

    thismod = sys.modules[__name__]

    if cmd == 'command':
        print "Available commands: %s " % ", ".join(__cmds__)

    elif cmd == 'api':
        print "Available API paths: %s " % ", ".join(DeliciousAPI.paths.keys())

    elif cmd in DeliciousAPI.paths.keys():
        # cmd is an API path
        print DeliciousAPI.paths[cmd].__doc__

    elif not hasattr(thismod, cmd):
        print "No such command or API path: %s" % (cmd,)

    elif not hasattr(getattr(thismod, cmd), '__doc__'):
        print "No docstring for %s" % (cmd,)

    elif cmd:
        print getattr(thismod, cmd).__doc__

    else:
        print thismod.__doc__
        # XXX: mage help work again in new dist
        # print pydelicious.tools.dlcs.__doc__

def info(conf, dlcs, **opts):

    """Default command.
    """

    u = dlcs.posts_update()['update']['time']
    print "Posts last updated on: %s (UTC)" % time.strftime("%c", u)

    posts_file = conf.get('local-files', 'posts')
    if exists(posts_file):
        postsupd = getmtime(posts_file)
        print "Cached post list on: %s (local)" % time.strftime("%c", time.localtime(postsupd))
    else:
        print "Need to cache post list"

    tags_file = conf.get('local-files', 'tags')
    if exists(tags_file):
        tagsupd = getmtime(tags_file)
        print "Cached tag list on: %s (local)" % time.strftime("%c", time.localtime(tagsupd))
    else:
        print "Need to cache tag list"

    if (exists(tags_file) and u > time.gmtime(tagsupd)) or (exists(posts_file) and u > time.gmtime(postsupd)):
        print "Cache is out of date"

def stats(conf, dlcs, **opts):

    """Statistics
    """

    posts = cached_posts(conf, dlcs, opts['keep_cache'])
    tags = cached_tags(conf, dlcs, opts['keep_cache'])

    # TODO: Some more intel gathering on tags would be nice
    print "Tags: %s" % len(tags['tags'])
    print "Posts: %s" % len(posts['posts'])

    # Tag usage per post
    taggedhigh = 0
    taggedlow = 0
    for post in posts['posts']:
        tags = len(post['tag'].split(' '))
        if not taggedlow or tags < taggedlow:
            taggedlow = tags
        if not taggedhigh or tags > taggedhigh:
            taggedhigh = tags

    print "Tags per post (min/max): %s/%s" % (taggedlow, taggedhigh)

def req(conf, dlcs, path, **opts):

    """Request data from a (URI-)path using pydelicious.DeliciousAPI. E.g.::

        % dlcs req posts/get?tag=energy
        % dlcs req --outf=raw tags/bundles/all
        % dlcs req -d posts/update

    The `raw` option causes the response XML to be printed as JSON, `dump`
    prints the entire HTTP XML response. Note that since the v1 API is not RESTful
    you can change data using this function too. E.g.::

        % dlcs req tags/bundles/delete?bundle=foo
        % dlcs req "tags/bundles/set?bundle=foo&tags=bar%20baz"

    Remember to URL encode and use shell-escaping on the paths.
    """

    if 'dump' in opts and opts['dump']:
        fl = dlcs.request_raw(path)
        print http_dump(fl)

    else:
        data = dlcs.request(path)
        print output(`req`, opts, data)

def post(conf, dlcs, url, description, extended, *tags, **opts):

    """Do a standard post to del.icio.us::

        % dlcs post "URL" "DESCRIPTION" "EXTENDED" tag1 tag2...
    """

    tags = " ".join(tags)

    replace = 'no'
    if 'replace' in opts:
        replace = opts['replace']

    shared = 'yes'
    if 'shared' in opts:
        shared = opts['shared']

    dlcs.posts_add(replace=replace,
        shared=shared,
        description=description,
        extended=extended,
        url=url,
        tags=tags)

    print '* Post: "%s <%s>"' % \
        (description, url)

def postit(conf, dlcs, url, shared='yes', replace='no', **opts):

    """Create and edit posts.
    """

    assert 'EDITOR' in os.environ, \
        "postit needs the environmental variable 'EDITOR' set"

    description, extended, tags = '', '', []

    # Use ConfigParser as key/value parser
    conf = ConfigParser()
    tmpf = os.tmpnam() + '.ini'
    os.mknod(tmpf)
    tmpfl = open(tmpf, 'w+')

    # Prepare dictionary for use in ini file
    p = { 'description': description, 'extended': extended,
        'tag': " ".join(tags),
        'shared': shared, 'replace': replace, }

    # get post data (if available)
    posts = dlcs.posts_get(url=url)
    if posts['posts']:
        p.update(posts['posts'][0])
        p['replace'] = 'Yes'

    # Fill ini file
    conf.add_section(url)
    for key in p:
        if key in ('href',):#hash', 'meta', 'href', 'time'):
            continue
        if isinstance(p[key], bool):
            if p[key]:
                p[key] = 'Yes'
            else:                
                p[key] = 'No'
        conf.set(url, key, p[key].encode(opts['encoding']))
    tmpfl.write('# This is a temporary representation for bookmark <%s>\n' % url)
    tmpfl.write('# Only description, extended, shared, replace and tags are mutable.\n\n')
    conf.write(tmpfl)
    tmpfl.close()

    #Let user edit file
    mtime = os.stat(tmpf)[8]

    os.system("%s %s" % (os.environ['EDITOR'], tmpf))

    if mtime == os.stat(tmpf)[8]:
        return "! No changes, aborted"

    # Parse data back into locals
    conf.read(tmpf)

    opts['shared'] = conf.get(url, 'shared').lower()
    opts['replace'] = conf.get(url, 'replace').lower()

    description = conf.get(url, 'description')
    extended = conf.get(url, 'extended')
    tags = conf.get(url, 'tag').split(' ')
    if conf.has_option(url, 'href'):
        url = conf.get(url, 'href')

    # Let post handle rest of command
    post(conf, dlcs, url, description, extended, *tags, **opts)

def posts(conf, dlcs, *urls, **opts):

    """Either prints the ALL URLs or posts of given urls.
    """

    posts = cached_posts(conf, dlcs, opts['keep_cache'])
    for post in posts['posts']:
        if urls and not post['href'] in urls:
            continue
        else:
            print output('posts', opts, post)

def postsupdate(conf, dlcs, **opts):

    """Print last update time.
    """

    u = dlcs.posts_update()
    print str(u['update']['time'])

def updateposts(conf, dlcs, **opts):

    """TODO: Retrieve 15 most recent posts and add to local cache,
    (after which it will be considered up-to-date again).
    """

    fl = dlcs.posts_recent(_raw=True)
    print fl
    append_cache(fl, opts)

def getposts(conf, dlcs, *urls, **opts):

    """Print the posts for the given URLs in JSON.
    """

    out = []
    if not urls:
        print >>sys.stderr, "dlcs: getposts: No arguments"

    for url in urls:
        posts = dlcs.posts_get(url=url)['posts']

        if not len(posts)>0:
            print >>sys.stderr,"No posts for %s" % (url,)

        else:
            out.extend(posts)

    print output('getposts', opts, out)

def findposts(conf, dlcs, keyword, **opts):

    """Search all text fields of all posts for the keyword and print machting URLs.

        % dlcs findposts keyword
    """

    posts = cached_posts(conf, dlcs, opts['keep_cache'])
    for post in posts['posts']:
        fields = post['tag']+post['href']+post['description']+post['extended']

        if opts['ignore_case']:
            if fields.lower().find(keyword.lower()) > -1:
                print post['href']

        elif fields.find(keyword) > -1:
            print post['href']

def deleteposts(conf, dlcs, *urls, **opts):

    """Delete one or more URLs.
    """

    for url in urls:
        dlcs.posts_delete(url)
        print '* Deleted "%s"' % (url)

def recent(conf, dlcs, **opts):

    """Fetch the 15 most recent posts.
    """

    rs = dlcs.posts_recent()
    for post in rs['posts']:
        print post['href']

def rename(conf, dlcs, oldtag, *newtags, **opts):

    """rename a tag to one or more tags.

        % dlcs rename oldtag newtag(s)
    """

    new = " ".join(newtags)
    dlcs.tags_rename(oldtag, new)
    print '* "%s" -> "%s"' % (oldtag, new)

def bundle(conf, dlcs, name, *tags, **opts):

    """Bundle some tags under a name, replaces previous bundle contents::

        % dlcs bundle bundlename tag(s)
    """

    tags = " ".join(tags)
    dlcs.bundles_set(name, tags)
    print '* "%s" -> "%s"' % (name, tags)

def bundles(conf, dlcs, **opts):

    """Retrieve all bundles and print their names.
    """

    bundles = dlcs.bundles_all()['bundles']
    for bundle in bundles:
        print bundle['name'],

    print

def getbundle(conf, dlcs, name, **opts):

    """Retrieve all tags within a bundle.
    """

    bundles = dlcs.bundles_all()['bundles']
    for bundle in bundles:
        if bundle['name'] == name:
            print bundle['tags']
            return

def deletebundle(conf, dlcs, name, **opts):

    """Delete an entire bundle.
    """

    dlcs.bundles_delete(name)
    print '* delete bundle "%s"' % (name)

def bundleadd(conf, dlcs, name, *tags, **opts):

    """Add one or more tags to a bundle. Retrieves current bundles, adds the
    tags to the indicated bundle and posts it back to del.icio.us::

        % dlcs bundleadd bundlename tag(s)
    """

    tags = " ".join(tags)

    bundles = dlcs.bundles_all()['bundles']
    for bundle in bundles:
        if bundle['name'] == name:
            tags += ' '+bundle['tags']
            dlcs.bundles_set(name, tags)
            print '* "%s" -> "%s"' % (name, tags)
            return

def bundleremove(conf, dlcs, name, *tags, **opts):

    """Remove one or more tags from a bundle. Retrieves current bundles, removes
    the tags from the indicated bundle and posts it back to del.icio.us::

        % dlcs bundleremove bundlename tag(s)
    """

    bundles = dlcs.bundles_all()['bundles']
    for bundle in bundles:
        if bundle['name'] == name:
            curcontents = bundle['tags'].split(' ')
            for tag in tags:
                if tag in curcontents: curcontents.remove(tag)
                else: print >>sys.stderr, "%s not in bundle %s" % (tag, name)
            dlcs.bundles_set(name, curcontents)
            print '* "%s" -> "%s"' % (name,
                ", ".join(curcontents))
            return

def tag(conf, dlcs, tags, *urls, **opts):

    """Tag all URLs with the given tag(s)::

        % dlcs tag "tag1 tag2" http://... http://...

    This will retrieve the post for each URL, add the given tags and then
    replace the post at del.icio.us. URLs not in the collection cause
    a message to stderr and are ignored.
    """

    for url in urls:
        posts = dlcs.request('posts/get', url=url)
        if not posts['posts']:
            print >>sys.stderr, '* URL "%s" not in collection' % (url)

        else:
            post = posts['posts'][0]
            if not 'extended' in post:
                post['extended'] = ""
            if not 'tag' in post:
                post['tag'] = ""
            if not 'shared' in post:
                post['shared'] = "True"

            # XXX: del.icio.us takes care of duplicates...
            post['tag'] += ' '+tags

            dlcs.posts_add(replace="yes",
                shared=post['shared'],
                description=post['description'],
                extended=post['extended'],
                url=post['href'],
                tags=post['tag'],
                time=post['time'])

            print '* tagged "%s" with "%s"' % (url,
                post['tag'])

def untag(conf, dlcs, tags, *urls, **opts):

    """Reverse of tag, remove given tags from the given URLs.
    Tags and URLs not found are reported on stderr and ignored.
    Provide only tag names without URL to completely remove them from
    the collection.
    Setting --ignore-case will lowercase all tags for the given URLs.
    """

    if opts['ignore_case']:
        tags = [t.lower() for t in tags.split(' ')]
    else:
        tags = tags.split(' ')

    urls = list(urls)

    if not urls:
        posts = cached_posts(conf, dlcs, opts['keep_cache'])

        for post in posts['posts']:
            for tag in tags:
                if opts['ignore_case']:
                    post['tag'] = post['tag'].lower()
                if tag in post['tag'].split(' '):
                    urls.append(post['href'])

    for url in urls:
        # TODO: fetching posts is inefficient and ignoring the localcache:
        # Must have indexed access to fields in localcache
        posts = dlcs.request('posts/get', url=url)
        if not posts['posts']:
            print >>sys.stderr, '* URL "%s" not in collection' % (url)

        else:
            post = posts['posts'][0]
            if not 'extended' in post:
                post['extended'] = ""
            if not 'tag' in post:
                post['tag'] = ""
            if not 'shared' in post:
                post['shared'] = "True"

            if opts['ignore_case']:
                tagged = post['tag'].lower().split(' ')
            else:                    
                tagged = post['tag'].split(' ')
            untagged = []

            for tag in tags:
                if tag in tagged:
                    tagged.remove(tag)
                    untagged.append(tag)

            if not untagged:
                print >>sys.stderr, '* Tags "%s" not found on URL "%s"' % (tags, url)
                continue

            post['tag'] = " ".join(tagged)

            dlcs.posts_add(replace="yes",
                shared=post['shared'],
                description=post['description'],
                extended=post['extended'],
                url=post['href'],
                tags=post['tag'],
                time=post['time'])

            print '* untagged "%s" from "%s"' % (" ".join(untagged),
                url)

def tagged(conf, dlcs, *tags, **opts):

    """Request all posts for a tag or overlap of tags. Print URLs.

        % dlcs tagged tag [tag2 ...]
    """

    posts = cached_posts(conf, dlcs, opts['keep_cache'])
    for post in posts['posts']:

        if opts['ignore_case']:
            post_tags = post['tag'].lower().split(' ')
            tags = map(lambda t: t.lower(), tags)
        else:
            post_tags = post['tag'].split(' ')

        for tag in tags:
            if '+' in tag:
                andq = tag.split('+')
                if Set(post_tags).issuperset(Set(andq)):
                    print post['href']
            elif tag in post_tags:
                print post['href']


def tags(conf, dlcs, *count, **opts):

    """Print all tags, optionally filtered by their count.

        % dlcs tags [[ '>' | '<' | '=' ] count]
    """

    tags = cached_tags(conf, dlcs, opts['keep_cache'])

    if count:
        if not count[0].isdigit():
            assert len(count) == 1
            count = count[0][0], count[0][1:]
        count = list(count)
        number = int(count.pop())
        if count:
            count = count[0]
        else:
            count = '='

    for tag in tags['tags']:
        if count:
            tc = int(tag['count'])
            if count == '=':
                if tc == number:
                    print tag['tag'],
            elif count == '>':
                if tc > number:
                    print tag['tag'],
            elif count == '<':
                if tc < number:
                    print tag['tag'],
        else:            
            print tag['tag'],

def tagrel(conf, dlcs, *tags, **opts):

    """Print related tags.

    Finds all posts tagged `tags` and gather other tags for post.
    """

    reltags = []

    posts = cached_posts(conf, dlcs, opts['keep_cache'])
    for post in posts['posts']:

        if opts['ignore_case']:
            post_tags = post['tag'].lower().split(' ')
            tags = map(lambda t: t.lower(), tags)
        else:
            post_tags = post['tag'].split(' ')


        for tag in tags:
            if '+' in tag:
                andq = tag.split('+')
                if Set(post_tags).issuperset(Set(andq)):
                    for ntag in post['tag'].split(' '):
                        if ntag != tag and not ntag in reltags:
                            reltags.append(ntag)
            elif tag in post_tags:
                for ntag in post['tag'].split(' '):
                    if ntag != tag and not ntag in reltags:
                        reltags.append(ntag)

    for tag in reltags:
        print tag,

def gettags(conf, dlcs, *tags, **opts):

    """Print info about tag.
    """

    if opts['ignore_case']:
        tags = [t.lower() for t in tags]

    for tag in cached_tags(conf, dlcs, opts['keep_cache'])['tags']:
        if tag['tag'] in findtags or \
                (opts['ignore_case'] and tag['tag'].lower() in findtags):
            print jsonwrite(tag)

def findtags(conf, dlcs, *tags, **opts):

    """Search all tags for (a part of) a tag.
    """

    for tag in cached_tags(conf, dlcs, opts['keep_cache'])['tags']:
        tag = tag['tag']

        for findtag in tags:
            if opts['ignore_case']:
                if tag.lower().find(findtag.lower()) > -1:
                    print tag

            elif tag.find(findtag) > -1:
                print tag

def clearcache(conf, dlcs, *clear, **opts):

    """Delete all locally cached data::

        % dlcs clear [tags | posts]
    """

    if not clear:
        clear = ['tags', 'posts']

    if 'tags' in clear:
        try:
            tags = conf.get('local-files', 'tags')
            os.unlink(tags)
            print "* Deleted '%s'" % tags
        except: pass

    if 'posts' in clear:
        try:
            posts = conf.get('local-files', 'posts')
            os.unlink(posts)
            print "* Deleted '%s'" % posts
        except: pass

def mates(conf, dlcs, *args, **opts):

    """The following was adapted from delicious_mates.
    http://www.aiplayground.org/artikel/delicious-mates/

        % dlcs mates [max_mates[, min_bookmarks[, min_common]]]

    """
   
    max_mates, min_bookmarks, min_common = map(int, opts['mates'].split(','))

    delicious_users = {}
    posts = cached_posts(conf, dlcs, opts['keep_cache'])
    print "Getting mates for collection of %i bookmarks" % len(posts['posts'])

    print "\nUsers for each bookmark:"
    for i, post in enumerate(posts['posts']):

        hash = md5.md5(post['href']).hexdigest()
        #urlfeed = pydelicious.dlcs_feed('urlinfo', urlmd5=hash)
        posts = dlcs_feed('url', count='all', format='rss', urlmd5=hash)
        usernames = [e['author'] for e in posts['entries']]

        print "    %i. %s (%i)" % (i+1, post['href'], len(usernames))
       
        for username in usernames:
            if username != dlcs.user:
                delicious_users.setdefault(username, (0.0, 0))
                (weight, num_common) = delicious_users[username]
                new_weight = weight + 1.0/math.log(len(usernames)+1.0)
                delicious_users[username] = (new_weight, num_common + 1)
    
    print "\n%i candidates from list of %i users" % (max_mates, len(delicious_users))
    friends = {}
    for (username, (weight, num_common)) in value_sorted(delicious_users):
        if num_common >= min_common:

            num_bookmarks = float([e['summary'] for e in 
                dlcs_feed('user_info', format='rss', username='mpe')['entries'] 
                if e['id'] == 'items'][0])

            print "    %s (%i/%i)" % (username, num_common, num_bookmarks),
            if num_bookmarks >= min_bookmarks:
                friends[username] = (weight*(num_common/num_bookmarks), num_common, num_bookmarks)
                if len(friends) >= max_mates:
                    break
            else:
                print
            time.sleep(1)
    
    print "\nTop %i del.icio.us mates:" % max_mates
    print "username".ljust(20), "weight".ljust(20), "# common bookmarks".ljust(20), "# total bookmarks".ljust(20), "% common"
    print "--------------------------------------------------------------------------------------------"
    for (username, (weight, num_common, num_total)) in value_sorted(friends)[:max_mates]:
        print username.ljust(20),
        print ("%.5f" % (weight*100)).ljust(20),
        print str(num_common).ljust(20),
        print str(int(num_total)).ljust(20),
        print "%.5f" % ((num_common/num_total)*100.0)



### Utils
def http_dump(fl):

    """Format fileobject wrapped in urllib.addinfourl as HTTP message string
    and return.
    """

    return "\r\n".join([
        str(fl.code) +" "+ fl.msg,
        "".join(fl.headers.headers),
        fl.read().strip()])

def cache_file(fn, data):
    open(fn, 'w').write(data.read())

def cache_append_posts(fl, ):
    pass

def cached_tags(conf, dlcs, noupdate=False):
    """
    Make sure the tag list is cached locally. Updates when the file is
    older than the last time the posts where updated (according to
    del.icio.us posts/update, which only notes new posts, not any updates).
    """
    tags_file = conf.get('local-files', 'tags')
    if not exists(tags_file):
        print >>sys.stderr, "cached_tags: Fetching new tag list..."
        cache_file(tags_file, dlcs.tags_get(_raw=True))
    else:
        if not noupdate:
            lastupdate = dlcs.posts_update()['update']['time']
            if time.gmtime(getmtime(tags_file)) < lastupdate:
                print >>sys.stderr, "cached_tags: Updating tag list..."
                cache_file(tags_file, dlcs.tags_get(_raw=True))
        elif DEBUG: print >>sys.stderr, "cached_tags: Forced read from cached file..."
    tags = dlcs_parse_xml(open(tags_file))
    return tags

def cached_posts(conf, dlcs, noupdate=False):
    """
    Same as cached_tags but for the post list.
    """
    posts_file = conf.get('local-files', 'posts')
    if not exists(posts_file):
        print >>sys.stderr, "cached_posts: Fetching new post list..."
        cache_file(posts_file, dlcs.posts_all(_raw=True))
    else:
        if not noupdate:
            lastupdate = dlcs.posts_update()['update']['time']
            if time.gmtime(getmtime(posts_file)) < lastupdate:
                print >>sys.stderr, "cached_posts: Updating post list..."
                cache_file(posts_file, dlcs.posts_all(_raw=True))
        elif DEBUG: print >>sys.stderr, "cached_posts: Forced read from cached file..."
    posts = dlcs_parse_xml(open(posts_file))
    return posts

def value_sorted(dic):
    """
    Return dic.items(), sorted by the values stored in the dictionary.
    """
    l = [(num, key) for (key, num) in dic.items()]
    l.sort(reverse=True)
    l = [(key, num) for (num, key) in l]
    return l


def _main():    
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print >>sys.stderr, "User interrupt"

# Entry point
if __name__ == '__main__':
    _main()
