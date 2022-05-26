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

"""Provides generation from Thot to HTML.
This module is used by a bunch of back-ends."""

import thot.common as common
import thot.doc as doc


class Manager:
	"""Interface linking and friend creation."""

	def add_friend(self, path):
		"""Called to an existing file as friend file.
		Return the effective path of the friend in the generation output."""
		return None

	def new_friend(self, id = ""):
		"""Create a new friend file. Return the corresponding path."""
		return None

	def get_number(self, node):
		"""Get the number associated with the node. Return None
		if there is no number."""
		return None

	def get_ref(self, node):
		"""Get the anchor associated with the node. Return None
		if there is no anchor."""
		return None

	def write(self, text):
		"""Write the text to output."""
		pass


def escape_cdata(s):
	"""Escape in the string s characters that are invalid in CDATA
	of XML text."""
	return common.escape(s)

def escape_attr(s):
	"""Escape in the string s characters that are invalid in attribute
	of XML elements."""
	return common.escape(s, True)


def gen_word(man, node):
	man.write(escape_cdata(node.toText()))

def gen_container(man, node):
	for item in node.content:
		gen(man, item)

def gen_par(man, node):
	man.write('<p>\n')
	gen_container(man, node)
	man.write('</p>\n')

def gen_header(man, node):
	level = str(node.getLevel() + 1)
	man.write('<h' + level + '>')
	man.write('<a name="' + man.get_ref(node).split('#')[1] + '"></a>')
	man.write(man.get_number(node))
	gen_container(man, node.getTitle())
	man.write('</h' + level + '>\n')
	gen_container(man, node)

STYLES = {
	doc.STYLE_BOLD: 		('<b>', '</b>'),
	doc.STYLE_STRONG: 		('<strong>', '</strong>'),
	doc.STYLE_ITALIC: 		('<i>', '</i>'),
	doc.STYLE_EMPHASIZED:	('<em>', '</em>'),
	doc.STYLE_UNDERLINE: 	('<u>', '</u>'),
	doc.STYLE_SUBSCRIPT: 	('<sub>', '</sub>'),
	doc.STYLE_SUPERSCRIPT: 	('<sup>', '</sup>'),
	doc.STYLE_MONOSPACE: 	('<tt>', '</tt>'),
	doc.STYLE_STRIKE: 		('<strike>', '</strike>'),
	doc.STYLE_BIGGER:		('<big>', '</big>'),
	doc.STYLE_SMALLER:		('<small>', '</small>'),
	doc.STYLE_CITE:			('<cite>', '</cite>'),
	doc.STYLE_CODE:			('<code>', '</code>')
}

def gen_style(man, node):
	try:
		open, close = STYLES[node.get_style()]
		man.write(open)
		gen_container(man, node)
		man.write(close)
	except KeyError:
		raise common.BackException("unknown style " + node.get_style())

LISTS = {
	'ul': ('<ul>\n', '<li>', '</li>\n', '</ul>\n'),
	'ol': ('<ol>\n', '<li>', '</li>\n', '</ol>\n')
}

def gen_list(man, node):
	try:
		lo, io, ic, lc = LISTS[node.get_kind()]
	except KeyError:
		raise common.BackException("unknown list %s" % node.get_kind())
	man.write(lo)
	for item in node.getItems():
		man.write(io)
		gen_container(man, item)
		man.write(ic)
	man.write(lc)

MAP = {
	doc.Header:	gen_header,
	doc.List:	gen_list,
	doc.Style:	gen_style,
	doc.Par:	gen_par,
	doc.Word:	gen_word
}

def gen(man, node):
	"""Generate the given node to the output, possibly using."""
	MAP[node.__class__](man, node)

