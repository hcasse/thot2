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

"""Parser classes based on RE."""

import os.path
import re
import sys

import thot.doc as doc
import thot.common as common

DEBUG = False

############### Word Parsing #####################

def handleVar(man, match):
	id = match.group('varid')
	val = man.doc[id]
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, man.factory.makeWord(val)))

def handleRef(man, match):
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, man.factory.makeRef(match.group("ref"))))

def handleDouble(man, match):
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, doc.Word("#")))

def handle_term(man, word):
	"""Handle a hashed word."""
	res = doc.Tag(word, man.doc)
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, res))

def handleSharp(man, match):
	handle_term(man, match.group("term"))

def handleParent(man, match):
	handle_term(man, match.group("pterm"))


__words__ = [
	(handleVar,
		common.VAR_RE,
		"""use of a variable (replaced by the variable value)."""),
	(handleRef,
		"@ref:(?P<ref>[^@]+)@",
		"""reference to a labeled element."""),
	(handleDouble,
		"##",
		"""single '#'."""),
	(handleParent,
		"#\((?P<pterm>[^)\s]+)\)",
		"""definition of a term."""),
	(handleSharp,
		"#(?P<term>\w+)",
		"""reference to a defined term.""")
]
INITIAL_WORDS = [(f, e) for (f, e, _) in __words__]

def handleText(man, line, suffix = ' '):

	# init RE_WORDS
	if man.words_re == None:
		text = ""
		i = 0
		for (fun, wre) in man.words:
			if text != "":
				text = text + "|"
			text = text + "(?P<a" + str(i) + ">" + wre + ")"
			i = i + 1
		man.words_re = re.compile(text)

	# look in line
	match = man.words_re.search(line)
	while match:
		idx = int(match.lastgroup[1:])
		fun, wre = man.words[idx]
		word = line[:match.start()]
		if word:
			man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, doc.Word(word)))
		line = line[match.end():]
		fun(man, match)
		match = man.words_re.search(line)

	# end of line
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, doc.Word(line + suffix)))


############### Line Parsing ######################

def handleComment(man, match):
	pass

def handleAssign(man, match):
	man.doc.set_symbol(match.group(1), match.group(2))

def handleUse(man, match):
	name = match.group(1).strip()
	man.use(name)

def handleInclude(man, match):
	path = match.group(1).strip()
	if not os.path.isabs(path):
		path = os.path.join(os.path.dirname(man.file_name), path)
	try:
		file = open(path)
		man.parseInternal(file, path)
	except IOError as e:
		raise common.ParseException('%s:%d: cannot include "%s": %s' % (man.file_name, man.line_num, path, e))

def handleCaption(man, match):
	par = doc.Par()
	man.push(par)
	man.getParser().parse(man, match.group(1))
	while par != man.get():
		man.pop()
	man.pop()
	for item in man.iter():
		if item.setCaption(par):
			return
	raise common.ParseException("caption unsupported here")


def handleLabel(man, match):
	for item in man.iter():
		if item.acceptLabel():
			man.doc.addLabel(match.group(1), item)
			return
	common.onWarning(man.message("label %s out of any container" % match.group(1)))


__lines__ = [
	(handleComment,
		"^@@.*",
		"""comment."""),
	(handleAssign,
		"^@([a-zA-Z_0-9]+)\s*=(.*)",
		"""definition of a variable."""),
	(handleUse,
		"^@use\s+(\S+)",
		"""use of a module."""),
	(handleInclude,
		'^@include\s+(.*)',
		"""inclusion of a THOT file."""),
	(handleCaption,
		'^@caption\s+(.*)',
		"""assignment of a caption to the previous element."""),
	(handleLabel,
		'^@label\s+(.*)',
		"""assignment of a label for references to the previous element.""")
]
INITIAL_LINES = [(f, re.compile(e)) for (f, e, _) in __lines__]

class Syntax:
	"""Base class of all syntaxes added to the parser."""
	
	def get_doc(self):
		"""Get the documentation for the syntax, a sequence of pairs
		(RE, description) where RE is a pseudo-regular expression
		describing the syntax and description is the descritpion of the
		syntax (possibly multi-line)."""
		return [("", "")]

	def get_lines(self):
		"""Get the pairs (function, RE) to parse lines."""
		return []
	
	def get_words(self):
		"""Get the pairs (function, RE) to parse words."""
		return []


class DefaultParser:

	def parse(self, handler, line):
		line = handler.doc.reduce_vars(line)
		done = False
		for (fun, re) in handler.lines:
			match = re.match(line)
			if match:
				fun(handler, match)
				done = True
				break
		if not done:
			handleText(handler, line)


class Manager:
	item = None
	items = None
	parser = None
	#doc = None
	lines = None
	words = None
	words_re = None
	added_lines = None
	added_words = None
	line_num = None
	file_name = None

	def __init__(self, document, ui):
		self.item = document
		self.doc = document
		self.parser = DefaultParser()
		self.items = []
		self.lines = INITIAL_LINES
		self.words = INITIAL_WORDS
		self.added_lines = []
		self.added_words = []
		self.ui = ui

	def get_doc(self):
		return self.doc
	
	def get_var(self, id, d):
		v = self.doc.getVar(id, deflt)
		if v != None:
			return v
		else:
			return d

	def get(self):
		return self.item

	def debug(self, msg):
		"""Used to output message."""
		print("DEBUG: %s" % msg)

	def send(self, event):
		if DEBUG:
			self.debug("send(%s)" % event) 
		self.item.onEvent(self, event)

	def iter(self):
		"""Generate an iterator on the stack of items (from top to bottom)."""
		yield self.item
		for i in xrange(len(self.items) - 1, -1, -1):
			yield self.items[i]
	
	def top(self):
		"""Return the top item of the element stack."""
		return self.item
	
	def push(self, item):
		self.items.append(self.item)
		self.item = item
		item.setFileLine(self.file_name, self.line_num)
		if DEBUG:
			self.debug("push(%s)" % item)
			self.debug("stack = %s" % self.items)

	def pop(self):
		self.item = self.items.pop()
		if DEBUG:
			self.debug("pop(): %s" % self.item)
			self.debug("stack = %s" % self.items)		

	def forward(self, event):
		if DEBUG:
			self.debug("forward(%s)" % event)
		self.pop()
		self.send(event)

	def setParser(self, parser):
		self.parser = parser

	def getParser(self):
		return self.parser

	def parseInternal(self, file, name):
		prev_line = self.line_num
		prev_file = self.file_name
		self.line_num = 0
		self.file_name = name
		for line in file:
			self.line_num += 1
			if line[-1] == '\n':
				line = line[0:-1]
			self.parser.parse(self, line)
		self.line_num = prev_line
		self.file_name = prev_file

	def reparse(self, str):
		self.parser.parse(self, str)

	def parse(self, file, name = '<unknown>'):
		try:
			self.parseInternal(file, name)
			self.send(doc.Event(doc.L_DOC, doc.ID_END))
			self.doc.clean()
		except common.ParseException as e:
			common.onError(self.message(e))

	def message(self, msg):
		"""Generate a message prefixed with error line and file."""
		return "%s:%d: %s" % (self.file_name, self.line_num, msg)

	def addLine(self, line):
		"""A syntax working on lines. The line parameter is pair
		(f, re) with f the function to call when the RE re is found."""
		self.added_lines.append(line)
		self.lines.append(line)

	def addWord(self, word):
		self.added_words.append(word)
		self.words.append(word)
		self.words_re = None

	def setSyntax(self, lines, words):

		# process lines
		self.lines = []
		self.lines.extend(INITIAL_LINES)
		self.lines.extend(self.added_lines)
		self.lines.extend(lines)

		# process words
		self.words = []
		self.words.extend(INITIAL_WORDS)
		self.words.extend(self.added_words)
		self.words.extend(words)
		self.words_re = None

	def warn(self, msg):
		"""Display a warning with file and line."""
		common.onWarning(self.message(msg))

	def error(self, msg):
		"""Display an error with file and line."""
		common.onError(self.message(msg))

	def use(self, name):
		"""Use a module in the current parser."""
		path = self.doc["THOT_USE_PATH"]
		mod = common.load_module(name, path)
		if mod == None:
			common.onError('cannot load module %s' % name)
		if mod in self.doc.get_uses():
			return
		self.doc.use(mod)
		if "init" in mod.__dict__:
			mod.init(self)

		# new syntax?
		if "__syntax__" in mod.__dict__:
			lines = []
			words = []
			if "__lines__" in mod.__dict__:
				lines = mod.__lines__
			if "__words__" in mod.__dict__:
				words = mod.__words__
			if "__syntaxes__" in mod.__dict__:
				for s in mod.__syntaxes__:
					lines = lines + s.get_lines()
					words = words + s.get_words()
			self.setSyntax(
				[(l[0], re.compile(l[1])) for l in lines],
				[(w[0], w[1]) for w in words])
		
		# simple extension
		else:
			if"__lines__" in  mod.__dict__:
				for line in mod.__lines__:
					self.addLine((line[0], re.compile(line[1])))
			if "__words__" in mod.__dict__:
				for word in mod.__words__:
					self.addWord((word[0], word[1]))
			if "__syntaxes__" in mod.__dict__:
				for s in mod.__syntaxes__:
					for (f, r) in s.get_lines():
						self.addLine((f, re.compile(r)))
					for w in s.get_words():
						self.addWord(w)


class BlockParser:
	old = None
	block = None
	re = None

	def __init__(self, man, block, re):
		self.old = man.getParser()
		man.setParser(self)
		self.block = block
		self.re = re
		man.send(doc.ObjectEvent(doc.L_PAR, doc.ID_NEW, self.block))

	def parse(self, man, line):
		if self.re.match(line):
			man.setParser(self.old)
		else:
			self.block.add(line)


	
