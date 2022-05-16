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

"""Dokuwiki syntax plugin"""
import re

import thot.common as common
import thot.doc as doc
import thot.highlight as highlight
import thot.tparser as tparser

def computeDepth(text):
	depth = 0
	for c in text:
		if c == ' ':
			depth = depth + 1
		elif c == '\t':
			depth = depth + 8
	return depth

ESCAPES = [ '(', ')', '+', '.', '*', '/', '?', '^', '$', '\\', '|' ]
def escape_re(str):
	res = ""
	for c in str:
		if c in ESCAPES:
			res = res + "\\" + c
		else:
			res = res + c
	return res

ENTITIES_INIT = [
	('<->',	0x2194),
	('->',	0x2192),
	('<-',	0x2190),
	('<=>',	0x21d4),
	('=>',	0x21d2),
	('<=',	0x21d0),
	('>>',	0x00bb),
	('<<',	0x00ab),
	('---',	0x2014),
	('--',	0x2013),
	('(c)',	0x00a9),
	('(tm)',0x2122),
	('(r)',	0x00ae),
	('...',	0x22ef)
]
ENTITIES = { }
ENTITIES_RE = ""
for (s, c) in ENTITIES_INIT:
	ENTITIES[s] = c
	if ENTITIES_RE != "":
		ENTITIES_RE = ENTITIES_RE + "|"
	ENTITIES_RE = ENTITIES_RE + escape_re(s)


SMILEYS = {
	'8-)' :         'icon_cool.gif',
	'8-O' :         'icon_eek.gif',
	'8-o' :         'icon_eek.gif',
	':-(' :         'icon_sad.gif',
	':-)' :         'icon_smile.gif',
	'=)' :          'icon_smile2.gif',
	':-/' :         'icon_doubt.gif',
	':-\\' :        'icon_doubt2.gif',
	':-?' :         'icon_confused.gif',
	':-D' :         'icon_biggrin.gif',
	':-P' :         'icon_razz.gif',
	':-o' :         'icon_surprised.gif',
	':-O' :         'icon_surprised.gif',
	':-x' :         'icon_silenced.gif',
	':-X' :         'icon_silenced.gif',
	':-|' :         'icon_neutral.gif',
	';-)' :         'icon_wink.gif',
	'^_^' :         'icon_fun.gif',
	':?:' :         'icon_question.gif',
	':!:' :         'icon_exclaim.gif',
	'LOL' :         'icon_lol.gif',
	'FIXME' :       'fixme.gif',
	'DELETEME' :    'delete.gif',
	'#;<P' :        'icon_kaddi.gif'
}
SMILEYS_RE = ""
for smiley in SMILEYS.keys():
	if SMILEYS_RE != "":
		SMILEYS_RE = SMILEYS_RE + "|"
	SMILEYS_RE = SMILEYS_RE + escape_re(smiley)


### specific blocks ###
class FileBlock(doc.Block):

	def __init__(self):
		doc.Block.__init__(self, "file")

	def dumpHead(self, tab):
		print("%sblock.file(" % tab)

	def gen(self, gen):
		gen.genEmbeddedBegin(self)
		type = gen.getType()
		if type == 'html':
			gen.genVerbatim('<pre class="file">\n')
			for line in self.content:
				gen.genText(line + "\n")
			gen.genVerbatim('</pre>\n')
		elif type == 'latex':
			gen.genVerbatim('\\begin{verbatim}\n')
			for line in self.content:
				gen.genText(line + "\n")
			gen.genVerbatim('\\end{verbatim}\n')
		elif type == 'docbook':
			gen.genVerbatim('<screen>\n')
			for line in self.content:
				gen.genText(line + "\n")
			gen.genVerbatim('</screen>\n')
		else:
			common.onWarning('%s back-end is not supported by file block' % type)
		gen.genEmbeddedEnd(self)


class NonParsedBlock(doc.Block):

	def __init__(self):
		doc.Block.__init__(self, "raw")

	def dumpHead(self, tab):
		print("%sblock.nonparsed(" % tab)

	def gen(self, gen):
		gen.genEmbeddedBegin(self)
		type = gen.getType()
		if type == 'html':
			gen.genVerbatim('<p>\n')
			for line in self.content:
				gen.genText(line + "\n")
			gen.genVerbatim('</>\n')
		elif type == 'latex':
			for line in self.content:
				gen.genText(line + "\n")
		elif type == 'docbook':
			gen.genVerbatim('<para>\n')
			for line in self.content:
				gen.genText(line + "\n")
			gen.genVerbatim('</para>\n')
		else:
			common.onWarning('%s back-end is not supported by file block' % type)
		gen.genEmbeddedEnd(self)


### code parse ###
END_CODE = re.compile("^\s*<\/code>\s*$")
END_FILE = re.compile("^\s*<\/file>\s*$")
END_NOWIKI = re.compile("^\s*<\/nowiki>\s*$")

INDENT_RE = re.compile("  \s*(.*)$")
class IndentParser:
	old = None
	block = None

	def __init__(self, man, match):
		self.old = man.getParser()
		man.setParser(self)
		self.block = highlight.CodeBlock(man, '')
		man.send(doc.ObjectEvent(doc.L_PAR, doc.ID_NEW, self.block))
		self.block.add(match.group(1))

	def parse(self, man, line):
		match = INDENT_RE.match(line)
		if match:
			self.block.add(match.group(1))
		else:
			man.setParser(self.old)
			self.old.parse(man, line)


### word processing ###
def processLink(man, target, text):
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW_LINK, doc.Link(target)))
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, text))
	man.send(doc.CloseEvent(doc.L_WORD, doc.ID_END_LINK, "link"))

def handleStyle(man, style):
	man.send(doc.StyleEvent(style))

def handleOpenStyle(man, style):
	man.send(doc.OpenStyleEvent(style))

def handleFootNote(man, match):
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW_STYLE, doc.FootNote()))

def handleCloseStyle(man, style):
	man.send(doc.CloseStyleEvent(style))

def handleURL(man, match):
	processLink(man, match.group(0), doc.Word(match.group(0)))

def handleEMail(man, match):
	processLink(man, "mailto:" + match.group(0), doc.Word(match.group(0)))

def handleLineBreak(man, match):
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, doc.LineBreak()))

def handleSmiley(man, match):
	image = doc.Image(man.doc.getVar("THOT_BASE") + "smileys/" + SMILEYS[match.group(0)])
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, image))

def handleEntity(man, match):
	glyph = doc.Glyph(ENTITIES[match.group(0)])
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, glyph))

def handleLink(man, match):
	target = match.group('target')
	label = match.group('label')
	if not label:
		label = target
	processLink(man, target, doc.Word(label))

def handleFigure(man, match):
	image = match.group("image")
	width = match.group("image_width")
	if width != None:
		width = int(width)
	height = match.group("image_height")
	if height != None:
		height = int(height)
	label = match.group("image_label")
	if label == None:
		caption = None
	else:
		caption = doc.Par()
		caption.append(doc.Word(label))
	left = len(match.group("left"))
	right = len(match.group("right"))
	if left == right:
		align = doc.ALIGN_CENTER
	elif left > right:
		align = doc.ALIGN_RIGHT
	else:
		align = doc.ALIGN_LEFT
	man.send(doc.ObjectEvent(doc.L_PAR, doc.ID_NEW,
		doc.Figure(image, width, height, caption, align)))

def handleImage(man, match):
	if match.group("left") or match.group("right"):
		handleFigure(man, match)
	else:
		image = match.group("image")
		width = match.group("image_width")
		if width != None:
			width = int(width)
		height = match.group("image_height")
		if height != None:
			height = int(height)
		label = match.group("image_label")
		if label == None:
			caption = None
		else:
			caption = doc.Par()
			caption.append(doc.Word(label))
		man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW,
			doc.Image(image, width, height, caption)))


def handleNonParsed(man, match):
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, doc.Word(match.group('nonparsed')[:-2])))


def handlePercent(man, match):
	man.send(doc.ObjectEvent(doc.L_WORD, doc.ID_NEW, doc.Word(match.group('percent'))))


### lines processing ###
def handleNewPar(man, match):
	man.send(doc.ObjectEvent(doc.L_PAR, doc.ID_END, doc.Par()))

def handleHeader(man, match):
	level = 6 - len(match.group(1))
	title = match.group(2)
	man.send(doc.ObjectEvent(doc.L_HEAD, doc.ID_NEW, doc.Header(level)))
	tparser.handleText(man, title)
	man.send(doc.Event(doc.L_HEAD, doc.ID_TITLE))

def handleList(man, kind, match):
	depth = computeDepth(match.group(1))
	man.send(doc.ItemEvent(kind, depth))
	tparser.handleText(man, match.group(3))

def handle_def(man, match):
	depth = computeDepth(match.group(1))
	man.send(doc.DefEvent(doc.ID_NEW_DEF, depth))
	tparser.handleText(man, match.group(3))
	man.send(doc.DefEvent(doc.ID_END_TERM))
	tparser.handleText(man, match.group(4))

def handleCode(man, match):
	lang = ""
	line = None
	opts = match.group(2)
	if opts:
		for opt in opts.split(','):
			if opt == "line":
				line = 1
			elif opt.startswith("line="):
				try:
					line = int(opt[5:])
				except ValueError:
					raise common.ParseException("bad line number: %s" % opt)
			else:
				lang = opt
	tparser.BlockParser(man, highlight.CodeBlock(man, lang, line), END_CODE)

def handleFile(man, match):
	tparser.BlockParser(man, FileBlock(), END_FILE)

def handleNoWiki(man, match):
	tparser.BlockParser(man, NonParsedBlock(), END_NOWIKI)

TABLE_SEP = re.compile('\^|\||%%')
def handleRow(man, match):
	table = doc.Table()
	if match.group(4) == '^':
		kind = doc.TAB_HEADER
	else:
		kind = doc.TAB_NORMAL
	row = doc.Row(kind)
	table.content.append(row)
	man.send(doc.ObjectEvent(doc.L_PAR, doc.ID_NEW_ROW, table))
	row = match.group(1)
	object = None
	while row:

		# look kind
		if row[0] == '^':
			kind = doc.TAB_HEADER
		else:
			kind = doc.TAB_NORMAL
		row = row[1:]

		# find end
		pref = ""
		match = TABLE_SEP.search(row)
		while match and match.group() == "%%":
			p = row.find("%%", match.end())
			if p < 0:
				pref = pref + row[:match.end()]
				row = row[match.end():]
			else:
				pref = pref + row[:p + 2]
				row = row[p + 2:]
			match = TABLE_SEP.search(row)
		if match:
			last = match.start()
		else:
			last = len(row)
		cell = pref + row[:last]
		row = row[last:]

		# dump object if required
		if cell == '' and object:
			#object.span += 1
			object.setInfo(doc.INFO_HSPAN, object.getInfo(doc.INFO_HSPAN, 0) + 1)
			continue
		if object:
			man.send(doc.ObjectEvent(doc.L_PAR, doc.ID_NEW_CELL, object))
			tparser.handleText(man, text)

		# strip and find align
		total = len(cell)
		cell = cell.lstrip()
		left = total - len(cell)
		total = len(cell)
		cell = cell.rstrip()
		right = total - len(cell)
		if left < right:
			align = doc.TAB_LEFT
		elif left > right:
			align = doc.TAB_RIGHT
		else:
			align = doc.TAB_CENTER

		# generate cell
		object = doc.Cell(kind, align, 1)
		text = cell

	# dump final object
	man.send(doc.ObjectEvent(doc.L_PAR, doc.ID_NEW_CELL, object))
	tparser.handleText(man, text)

def handleHLine(man, match):
	man.send(doc.ObjectEvent(doc.L_PAR, doc.ID_NEW, doc.HorizontalLine()))

def handleIndent(man, match):
	if match.group(1):
		IndentParser(man, match)
	else:
		man.send(doc.ObjectEvent(doc.L_PAR, doc.ID_END, doc.Par()))

def handleQuote(man, match):
	man.send(doc.QuoteEvent(len(match.group(1))))
	tparser.handleText(man, match.group(2))

__short__ = "syntax for Dokuwiki format"
__description__ = \
"""This module provides syntax for Dokuwiki format (https://www.dokuwiki.org/wiki:syntax).
"""
__syntax__ = True

__words__ = [
	(lambda man, match: handleStyle(man, "bold"),
		"\*\*",
		"""open and close bold text."""),
	(lambda man, match: handleStyle(man, "italic"),
		"\/\/",
		"""open and close italic text."""),
	(lambda man, match: handleStyle(man, "underline"),
		"__",
		"""open and close underlined text."""),
	(lambda man, match: handleStyle(man, "monospace"),
		"''",
		"""open and close monospaced text."""),
	(lambda man, match: handleOpenStyle(man, "subscript"),
		"<sub>",
		"""open subscript text."""),
	(lambda man, match: handleCloseStyle(man, "subscript"),
		"<\/sub>",
		"""close subscript text."""),
	(lambda man, match: handleOpenStyle(man, "superscript"),
		"<sup>",
		"""open superscript text."""),
	(lambda man, match: handleCloseStyle(man, "superscript"),
		"<\/sup>",
		"""close superscript text."""),
	(lambda man, match: handleOpenStyle(man, "deleted"),
		"<del>",
		"""open deleted text."""),
	(lambda man, match: handleCloseStyle(man, "deleted"),
		"<\/del>",
		"""close deleted text."""),
	(handleFootNote,
		'\(\(',
		"""open footnote."""),
	(lambda man, match: handleCloseStyle(man, "footnote"),
		"\)\)",
		"""close footnote;"""),
	(handlePercent,
		'%%(?P<percent>([^%]|%[^%])*)%%',
		"""text area without formatting."""),
	(handleURL,
		"(http|ftp|mailto|sftp|https):\S+",
		"""URL inserted in the text (producing an hyper-reference)."""),
	(handleEMail,
		"([a-zA-Z0-9!#$%&'*+-/=?^_`{|}~.]+@[-a-zA-Z0-9.]+[-a-zA-Z0-9])",
		"""EMail address inserted in the text (producing an hyper-reference)."""),
	(handleLink,
		"\[\[(?P<target>[^\]|]*)(\|(?P<label>[^\]]*))?\]\]",
		"""link to the given target displaying the given label (if any)."""),
	(handleImage,
		"{{(?P<left>\s*)(?P<image>[^}?\s]+)(\?(?P<image_width>[0-9]+)?(x(?P<image_height>[0-9]+))?)?(?P<right>\s*)(\|(?P<image_label>[^}]*))?}}",
		"""insertion of an image with possible width, height, label and aligned according spaces at left or at right."""),
	(handleSmiley,
		SMILEYS_RE,
		"""insertion of smileys."""),
	(handleEntity,
		ENTITIES_RE,
		"""insertion of special characters."""),
	(handleLineBreak,
		"\\\\\\\\",
		"""insertion of linebrak."""),
	(handleNonParsed,
		"%%(?P<nonparsed>([^%]*%)*)%",
		"""non-parsed text area"""),
]

__lines__ = [
	(handleHeader,
		"^(?P<pref>={1,6})(.*)(?P=pref)",
		"""section header which level is inversely proportional to the number of '='."""),
	(handleNewPar,
		"^$",
		"""begin of a new paragraph."""),
	(lambda man, match: handleList(man, "ul", match),
		"^((  |\t)\s*)\*(.*)",
		"""bulleted list item (number of blank characters gives the depth)."""),
	(lambda man, match: handleList(man, "ol", match),
		"^((  |\t)\s*)-(.*)",
		"""numbered list item (number of blank characters gives the depth)."""),
	(handle_def,
		"^((  |\t)\s*)\?([^:]*):(.*)",
		"""definition item."""),
	(handleCode,
		"^\s*<code(\s+(\S+))?\s*>\s*",
		"""code area (ended by </code>)."""),
	(handleFile,
		"^\s*<file>\s*",
		"""file content area (ended by </file>)."""),
	(handleNoWiki,
		"^\s*<nowiki>\s*",
		"""area without markup (ended by </nowiki>)"""),
	(handleRow,
		"^((\^|\|)(.*))(\^|\|)\s*$",
		"""row of a table (cells introduced by '^' are considered as headers)."""),
	(handleHLine,
		"^-----*\s*$",
		"""horizontal bar."""),
	(handleIndent,
		"  \s*(.*)$",
		"""text considered as excerpt."""),
	(handleQuote,
		"^(>+)(.*)$",
		"""quoted text."""),
	(handleFigure,
		"^\s*{{(?P<left>\s*)(?P<image>[^}?\s|]+)(\?(?P<image_width>[0-9]+)?(x(?P<image_height>[0-9]+))?)?(?P<right>\s*)(\|(?P<image_label>[^}]*))?}}\s*$",
		"""insertion of an image as a a figure with possible width, height, label and aligned according spaces at left or at right.""")
]

def init(man):
	man.defs = { }

