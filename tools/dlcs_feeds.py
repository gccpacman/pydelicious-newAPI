#!/usr/bin/env python
try:
	from hashlib import md5
except ImportError:
	from md5 import md5
from itertools import chain
import locale
import optparse
import os
from pprint import pprint, pformat
import re
import sys

import pydelicious


#ENCODING = locale.getpreferredencoding()

__usage__ = """%prog [options] [command] [args...] """

__options__ = [
#	(('-e', '--encoding'),{'default':ENCODING,
#		'help':"Use custom character encoding [locale: %default]"}),
	(('-C', '--clear-screen'),{'action':'store_true'}),
	(('-L', '--list-feeds'),{'action':'store_true','help':'List available feeds for given parameters. '}),
	(('-f', '--format'),{'default':'rss'}),
	(('-k', '--key'),{}),
	(('-l', '--url'),{}),
	(('-H', '--urlmd5'),{}),
	(('-t', '--tag'),{'dest':'tags','action':'append'}),
	(('-u', '--username'),{}),
#	(('-v', '--verboseness'),{'default':0,
#		'help':"TODO: Increase or set DEBUG (defaults to 0 or the DLCS_DEBUG env. var.)"})
]

def parse_argv(options, argv, usage="%prog [args] [options]"):
	parser = optparse.OptionParser(usage)
	for opt in options:
		parser.add_option(*opt[0], **opt[1])
	optsv, args = parser.parse_args(argv)

	if optsv.url and not optsv.urlmd5:
		optsv.urlmd5 = md5(optsv.url).hexdigest()
	if optsv.tags:
		optsv.tag = ' '.join(optsv.tags)
	else:
		optsv.tag = None
	
	return parser, optsv, args

find_patterns = re.compile('%\(([^)]*)\)s').findall

def feeds_for_params(**params):
	kandidates = {}
	"Feed paths that need more parameters. "
	matches = []
	"Feed paths that match current paramters. "
	params = set([p for p in params if type(params[p]) != type(None)])
	for name, path in pydelicious.delicious_v2_feeds.items():
		ptrns = set(find_patterns(path))
		if ptrns > params:
			kandidates[name] = params.difference(ptrns)
		elif ptrns == params:
			matches.append(name)
	return matches, kandidates

def main(argv):
	optparser, opts, args = parse_argv(__options__, argv, __usage__)
	kwds = {}
	for k in ('format','username','tag','urlmd5','key'):
		v = getattr(opts, k)
		if type(v) != type(None):
			kwds[k] = v
	if opts.clear_screen:
		if os.name == 'posix':
			os.system('clear')
		else:
			os.system('cls')
	matches, candidates = feeds_for_params(**kwds)
	if opts.list_feeds:
		print >>sys.stderr,"Feeds for current parameters (%s)" % kwds
		if matches:
			print "Exact matches:"
		for m in matches:
			print '\t'+m+':', pydelicious.delicious_v2_feeds[m] % kwds
		if candidates:
			print "Candidates:"
		for m in candidates:
			print '\t'+pydelicious.delicious_v2_feeds[m]
		sys.exit()
	path = args and args.pop(0)
	if not path:
		if len(matches) == 1:
			path = matches[0]
			print >>sys.stderr, "Setting path to %s" % path
		elif matches:
			print >>sys.stderr, "Multiple paths for given parameters, see -L"
			sys.exit()
	assert path in pydelicious.delicious_v2_feeds
	return pydelicious.dlcs_feed(path, **kwds)

def _main():
	try:
		print sys.exit(main(sys.argv[1:]))
	except KeyboardInterrupt:
		print >>sys.stderr, "User interrupt"

# Entry point
if __name__ == '__main__':
	_main()
# vim:noet:	
