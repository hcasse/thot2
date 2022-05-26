#
# Thot2 -- document generator
# Copyright (C) 2009  <hugues.casse@laposte.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Module providing several facilities to the rest of the application.
"""

import html
import imp
import os
import os.path
import re
import sys
import traceback

from html import escape

THOT_VERSION = "2.0"

class ThotException(Exception):
	"""Exception of the Thot system.
	Any back-passed to the Thot system must inherit this exception.
	Other exceptions will not be caught."""
	
	def __init__(self, msg):
		self.msg = msg
	
	def __str__(self):
		return self.msg
	
	def __repr__(self):
		return self.msg


class ParseException(ThotException):
	"""This exception may be thrown by any parser encountering an error.
	File and line information will be added by the parser."""
	
	def __init__(self, msg):
		ThotException.__init__(self, msg)


class BackException(ThotException):
	"""Exception thrown by a back-end."""
	
	def __init__(self, msg):
		ThotException.__init__(self, msg)


class CommandException(ThotException):
	"""Thrown if there is an error during a command call."""
	
	def __init__(self, msg):
		ThotException.__init__(self, msg)


IS_VERBOSE = False
ENCODING = "UTF-8"


#------ Environment ------

VAR_RE = "@\((?P<varid>[a-zA-Z_0-9]+)\)"
VAR_REC = re.compile(VAR_RE)

class Environment:
	"""Implements an anvironment, that os, a map associating keys
	with values."""

	def __init__(self, parent = None):
		self.parent_env = parent

	def get_name(self):
		"""Get the name of the environment."""
		return "<anonymous>"

	def get_symbol(self, key):
		"""Get the symbol with the corresponding key.
		Return None if the symbol does not exist."""
		if self.parent_env != None:
			return self.parent.get_symbol(key)
		else:
			return None

	def set_symbol(self, key, value):
		"""Set the value associated with a key."""
		pass

	def reduce_vars(self, text):
		"""Reduce variables in the given text."""

		m = VAR_REC.search(text)
		while m:
			val = str(self.get_symbol(m.group('varid')))
			text = text[:m.start()] + val + text[m.end():]
			m = VAR_REC.search(text)
		return text

	def get_symbols(self):
		"""Get the symbols in this environment."""
		return {}

	def get_parent_environment(self):
		"""Get the parent environment."""
		return self.parent_env

	def __getitem__(self, key):
		return self.get_symbol(key)

	def __setitem__(self, key, value):
		self.set_symbol(key, value)


EMPTY_ENV = Environment()

class OSEnvironment(Environment):
	"""Environment reflecting variables in the environment."""

	def __init__(self):
		Environment.__init__(self)

	def get_name(self):
		return "OS"

	def get_symbol(self, key):
		return os.getenv(key)

	def get_symbols(self):
		return os.environ

OS_ENV = OSEnvironment()


class MapEnvironment(Environment):
	"""Simple environment with a map."""

	def __init__(self, parent, name = "<anonymous>"):
		Environment.__init__(self, parent)
		self.map = {}
		self.name = name

	def get_name(self):
		return self.name

	def get_symbol(self, key):
		try:
			return self.map[key]
		except KeyError:
			if self.parent_env == None:
				return
			else:
				return self.parent_env.get_symbol(key)

	def set_symbol(self, key, value):
		self.map[key] = value

	def get_symbols(self):
		return self.map


def load_module(name, paths):
	"""Load a module by its name and a collection of paths to look in
	and return its object."""
	try:
		for path in paths.split(":"):
			path = os.path.join(path, name + ".py")
			if os.path.exists(path):
				return imp.load_source(name, path)
			else:
				path = path + "c"
				if os.path.exists(path):
					return imp.load_compiled(name, path)
		return None
	except Exception as e:
		tb = sys.exc_info()[2]
		traceback.print_tb(tb)
		raise ThotException("cannot open module '%s': %s" % (path, str(e)))


STANDARD_VARS = [
	("AUTHORS",			"authors of the document (',' separated, name <email>)"),
	("LANG",			"lang of the document"),
	("LOGO",			"logos of the supporting organization"),
	("ORGANIZATION",	"organization producing the document"),
	("SUBTITLE",		"sub-title of the document"),
	("THOT_FILE",		"used to derivate the THOT_OUT_PATH if not set"),
	("THOT_OUT_PATH",	"output directory path"),
	("TITLE",			"title of the document"),
]


def make_var_doc(custom):
	"""Generate documentation text for variables (for __description__
	building). The documented variables includes standard variables
	and custom variables."""
	vars = STANDARD_VARS + custom
	vars.sort()
	imax = max([len(i) for (i, _) in vars])
	d = ""
	for (i, id) in vars:
		d += "%s:%s %s\n" % (i, " " * (imax - len(i)), id)
	return d


AUTHOR_RE = re.compile('(.*)\<([^>]*)\>\s*')
def scanAuthors(text):
	"""Scan the author text to get structured representation of authors.
	text -- text containing author declaration separated by ','
	and with format "NAME <EMAIL>"
	Return a list of authors where each author dictionary
	containing 'name' and 'email' keys."""

	authors = []
	words = text.split(',')
	for word in words:
		author = {}
		match = AUTHOR_RE.match(word)
		if not match:
			author['name'] = word
		else:
			author['name'] = match.group(1)
			author['email'] = match.group(2)
		authors.append(author)
	return authors
