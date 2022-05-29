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

"""Standard HTML back-end."""

from glob import iglob as glob
import html as my_html
import os
import os.path
import re
import shutil
import sys
import urllib.parse as urlparse

import thot.common as common
import thot.doc as doc
import thot.html as html
from thot import i18n



#------ Page management ------

class PageHandler:
	"""Provide support for generating pages."""

	def gen_head(self):
		"""Called to generate head part of HTML file."""
		pass

	def gen_toc(self):
		"""Called to generate the menu."""
		pass
	
	def gen_content(self):
		"""Called to generate the content."""
		pass

	def gen_footnotes(self):
		"""Called to generate the foot notes."""
		pass

	def get_title(self):
		"""Get the title of the document."""
		return None

	def get_authors(self):
		"""Called to generate list of authors."""
		return None
		
	def get_encoding(self):
		"""If any, get encoding."""
		return None

	def get_toc_label(self):
		"""Get the label for the word "Table of Content"."""
		return ""

	def get_doc(self):
		"""Get the current document."""
		return None

	def get_ref(self, node):
		"""Get the reference to the given node."""
		return None

	def write(self, text):
		"""Output the given text."""
		pass


class Page:
	"""Abstract class for page generation."""

	def gen_toc_entry(self, handler, node, indent):
		"""Generate a content entry (including numbering, title and link)."""
		
		handler.write('%s<a href="%s">' % (indent, handler.get_ref(node)))
		handler.write(handler.get_number(node))
		handler.write(' ')
		html.gen_container(handler, node.get_title())
		handler.write('</a>\n')

	def expand_toc(self, handler, node, level, indent):
		"""Expand recursively the content and to the given level."""
		if node.getHeaderLevel() >= level:
			return
		one = False
		for child in node.getContent():
			if child.getHeaderLevel() >= 0:
				if not one:
					one = True
					handler.write('%s<ul class="toc">\n' % indent)
				handler.write("%s<li>\n" % indent)
				self.gen_toc_entry(handler, child, indent)
				self.expand_toc(handler, child, level, indent + "  ")
				handler.write("%s</li>\n" % indent)
		if one:
			handler.write('%s</ul>\n' % indent)

	def expand_toc_to(self, handler, node, path, level, indent):
		"""Expand, not recursively, the content until reaching the end of the path.
		From this, expand recursively the sub-nodes."""
		if not path:
			self.expand_toc(handler, node, level, indent)
		else:
			one = False
			for child in node.getContent():
				if child.getHeaderLevel() >= 0:
					if not one:
						one = True
						handler.write('%s<ul class="toc">\n' % indent)
					handler.write("%s<li>\n" % indent)
					self.gen_toc_entry(handler, child, indent)
					if path[0] == child:
						self.expand_toc_to(handler, child, path[1:], level, indent + '  ')
					handler.write("%s</li>\n" % indent)
			if one:
				handler.write('%s</ul>\n' % indent)
				
	def gen_toc(self, handler, path = [], level = 100):
		"""Generate the content without expanding until reaching the path
		(of headers) with an expanding maximum level.
		"""
		handler.write('<div class="toc">\n')
		handler.write('<h1><a name="toc">' + html.escape_cdata(handler.get_toc_label()) + '</name></h1>\n')
		self.expand_toc_to(handler, handler.get_doc(), path, level, '  ')
		handler.write('</div>\n')

	def gen_authors(self, authors, handler):
		"""Generate the list of authors."""
		if authors:
			authors = common.scanAuthors(authors)
			first = True
			for author in authors:
				if first:
					first = False
				else:
					self.out.write(', ')
				email = ""
				if 'email' in author:
					email = author['email']
					out.write('<a href="mailto:' + escape_attr(email) + '">')
				out.write(html.escape_cdata(author['name']))
				if email:
					out.write('</a>')		

	def apply(self, handler):
		"""Called to generate a page."""
		pass


class PlainPage(Page):
	"""Simple plain page."""
	
	def apply(self, handler):
		title = handler.get_title()
		authors = handler.get_authors()

		# output header
		handler.write('<!DOCTYPE HTML>\n')
		handler.write('<html>\n')
		handler.write('<head>\n')
		handler.write("	<title>")
		if title:
			handler.write(html.escape_attr(title))
		handler.write("</title>\n")
		if authors:
			handler.write('	<meta name="AUTHOR" content="' + html.escape_attr(authors) + '">\n')		# env['AUTHORS']
		handler.write('	<meta name="GENERATOR" content="Thot - HTML">\n');
		encoding = handler.get_encoding()
		if not encoding:
			encoding = "UTF-8"
		handler.write('	<meta http-equiv="Content-Type" content="text/html; charset=' + html.escape_attr(encoding) + '">\n')		# env['ENCODING']
		handler.gen_head()
		handler.write('</head>\n<body>\n<div class="main">\n')
		
		# output the title
		handler.write('<div class="header">\n')
		handler.write('	<div class="title">')
		if title:
			handler.write(html.escape_attr(title))
		handler.write('</div>\n')
		handler.write('	<div class="authors">')
		self.gen_authors(authors, handler)
		handler.write('</div>\n')
		handler.write('</div>')
		
		# output the table of content
		handler.gen_toc()
		
		# output the content
		handler.write('<div class="page">\n')
		handler.gen_content()
		handler.gen_footnotes()
		handler.write('</div>\n')		

		# output the footer
		handler.write("</div>\n</body>\n</html>\n")


template_re = re.compile("<thot:([^/]+)\/>")

class TemplatePage(Page):
	"""Page supporting template in HTML. The template may contain
	the following special elements:
	* <thot:title> -- document title,
	* <thot:authors> -- list of authors,
	* <thot:menu> -- table of content of the document,
	* <thot:content> -- content of the document.
	"""
	path = None
	
	def __init__(self, path):
		self.path = path

	def apply(self, handler, out):
		map = {
			"authors": 	self.gen_authors,
			"content": 	handler.gen_content,
			"header":  	handler.gen_head,
			"title":   	self.gen_title,
			"toc": 		handler.gen_toc
		}
		global template_re

		try:
			tpl = open(self.path, "r")
			n = 0
			for line in tpl.readlines():
				n = n + 1
				f = 0
				for m in template_re.finditer(line):
					gen.out.write(line[f:m.start()])
					f = m.end()
					try:
						kw = m.group(1)
						map[kw](out)
					except KeyError as e:
						common.onError("unknown element %s at %d" % (kw, n))					
				gen.out.write(line[f:])
			
		except IOError as e:
			common.onError(str(e))



#------ Policy classes ------

class Policy(html.Manager, PageHandler):
	"""Generator for HTML output."""

	def __init__(self, doc, ui):
		self.doc = doc
		self.db = doc.get_base()
		self.ui = ui
		self.root_dir = self.db.get_rootdir()
		self.out_dir = os.path.abspath((doc["THOT_OUT_PATH"]))
		self.in_place = self.root_dir == self.out_dir
		self.id = os.path.basename(os.path.splitext(doc.get_name())[0])
		self.import_path = None
		self.template = self.get_template()
		self.run()

	def get_doc(self):
		"""Get the current document."""
		return self.doc

	def get_template(self):
		"""Get the template of page."""
		self.template = self.doc['HTML_TEMPLATE']
		if self.template != None:
			self.template = TemplatePage(str(self.template))
		else:
			self.template = PlainPage()
		return self.template

	def get_authors(self):
		return self.doc['AUTHORS']

	def make_out_path(self, suff = ""):
		"""Build output path name."""
		if self.in_place:
			path = os.path.splitext(self.doc.get_name())[0]
		else:
			path = os.path.join(self.out_dir,
				os.path.relpath(self.doc.get_name(), self.root_dir))
		return path + suff + ".html"

	def open_out(self, path = None):
		"""Open an output file."""
		if not path:
			path = self.make_out_path()
		self.out_path = path
		try:
			self.out = open(self.out_path, "w")
		except OSError as e:
			raise common.BackException(e)

	def close_out(self):
		"""Close the current output path."""
		self.out.close()

	def get_import(self):
		"""Get or create the import directory."""
		if self.import_path != None:
			return self.import_path
		elif not self.in_place:
			self.import_path = self.root_dir
		else:
			self.import_path = os.path.join(self.root_dir, "%s-import" % self.id)
		if not os.path.isdir(self.import_path):
			try:
				os.makedirs(self.import_path)
			except OSError as e:
				raise BackException(str(e))
		else:
			try:
				for p in glob(os.path.join(self.import_path, "*gen-*.*")):
					os.remove(p)
			except OSError as e:
				raise BackException(str(e))
		return self.import_path
			
	def add_friend(self, path):
		path = os.abspath(path)
		if self.in_place and path.is_prefix(self.root_dir):
			return path
		else:
			ipath = self.get_import()
			if path.is_prefix(self.root_dir):
				rpath = path[len(self.root_dir)+1:]
			else:
				rpath = os.path.basename(path)
			try:
				# could be optimized to avoid copy
				tpath = os.path.join(ipath, rpath)
				os.makedirs(os.path.dirname(tpath), exist_ok = True)
				shutil.copyfile(path, tpath)
				return tpath
			except OSError as e:
				raise BackException(str(e))

	def new_friend(self, name = "", suffix = None):
		ipath = self.get_import()
		if suffix == None:
			path = os.path.join(ipath, name)
			return path
		else:
			if name == None:
				name = "thot-gen"
			else:
				name = "%s-gen" % name
			n = 0
			while True:
				path = os.path.join(ipath, "%s-%d.%s" % (name, n, suffix))
				if not os.exist(path):
					return path
				n = n + 1

	def get_number(self, node):
		return node.get_info("number")

	def get_title(self):
		return self.doc['TITLE']
	
	def get_encoding(self):
		return self.doc["ENCODING"]

	def write(self, text):
		self.out.write(text)

	def get_toc_label(self):
		return self.db.get_translator(self.doc).get(i18n.ID_CONTENT)

	def make_ref(self, nums):
		"""Generate a reference from an header number array."""
		return ".".join([str(i) for i in nums])


class AllInOne(Policy):
	"""Simple page policy doing nothing: only one page."""

	def __init__(self, doc, ui):
		Policy.__init__(self, doc, ui)

	def gen_refs(self, path):
		"""Generate and return the references for the given generator."""
		self.make_refs([1], { }, self.doc, path)

	def make_refs(self, nums, others, node, path):
		"""Traverse the document tree and generate references in the given map."""
		
		# number for header
		num = node.numbering()
		if num == 'header':
			r = self.make_ref(nums)
			node.set_info("number", r)
			node.set_info("ref", path + "#" + r)
			nums.append(1)
			for item in node.getContent():
				self.make_refs(nums, others, item, path)
			nums.pop()
			nums[-1] = nums[-1] + 1
		
		# number for embedded
		else:
			if self.doc.get_label_for(node):
				if num:
					if num not in others:
						others[num] = 1
						n = 1
					else:
						n = others[num] + 1
					r = "%s-%d" % (num, n)
					node.set_info("number", r)
					node.set_info("ref", path + "#" + r)
					others[num] = n
			for item in node.getContent():
				self.make_refs(nums, others, item, path)
	
	def gen_toc(self):
		if self.current == None:
			self.template.gen_toc(self, [], 0)
		else:
			self.templaten.gen_toc(self, [self.current], 100)
		
	def gen_content(self):
		for node in self.doc.getContent():
			html.gen(self, node)

	def run(self):
		self.open_out()
		self.gen_refs(self.out_path)
		self.doc.pregen(self.db)
		self.template.apply(self)
		self.close_out()

	def get_ref(self, node):
		ref = node.get_info("ref")
		if not ref:
			return None
		path, anchor = ref.split('#')
		cpath = os.path.commonpath([path, self.out_path])
		return path[len(cpath):] + '#' + anchor


class PerChapter(Policy):
	"""This page policy ensures there is one page per chapter."""
	node = None
	
	def __init__(self, doc, ui):
		Policy.__init__(self, doc, ui)

	def gen_refs(self):
		"""Generate and return the references for the given generator."""
		self.make_refs([1], { }, self.doc, self.make_out_path())

	def make_refs(self, nums, others, node, path):
		"""Traverse the document tree and generate references in the given map."""
		
		# number for header
		num = node.numbering()
		if num == 'header':
			if node.header_level == 0:
				path = self.make_out_path("-%d" % (nums[0] - 1))
			r = self.make_ref(nums)
			node.set_info("number", r)
			node.set_info("ref", path + "#" + r)
			nums.append(1)
			for item in node.getContent():
				self.make_refs(nums, others, item, path)
			nums.pop()
			nums[-1] = nums[-1] + 1
		
		# number for embedded
		else:
			if self.doc.get_label_for(node):
				if num:
					if num not in others:
						others[num] = 1
						n = 1
					else:
						n = others[num] + 1
					r = "%s-%d" % (num, n)
					node.set_info("number", r)
					node.set_info("ref", path + "#" + r)
					others[num] = n
			for item in node.getContent():
				self.make_refs(nums, others, item, path)

	def gen_toc(self):
		self.template.gen_toc(self, [self.current], 100)
		
	def gen_content(self):
		if self.current == None:
			for node in self.doc.getContent():
				if node.getHeaderLevel() == 0:
					break
				html.gen(self, node)
		else:
			html.gen(self, self.current)

	def get_ref(self, node):
		ref = node.get_info("ref")
		if not ref:
			return None
		path, anchor = ref.split('#')
		cpath = os.path.commonpath([path, self.out_path])
		return path[len(cpath):] + '#' + anchor

	def run(self):
		chapters = []

		# generate main page
		path = self.make_out_path()
		self.ui.print_command("generating %s" % path)
		self.open_out(path)
		self.gen_refs()
		self.doc.pregen(self.db)
		self.current = None
		for node in self.doc.getContent():
			if node.getHeaderLevel() == 0:
				chapters.append(node)
		self.template.apply(self)
		self.close_out()
		self.ui.print_success()

		# generate chapter pages
		for i in range(0, len(chapters)):
			path = self.make_out_path("-%d" % i)
			self.ui.print_command("generating %s" % path)
			self.open_out(path)
			self.current = chapters[i]
			self.template.apply(self)
			self.close_out()
			self.ui.print_success()


class PerSection(Policy):
	"""This page policy ensures there is one page per section."""
	node = None
	
	def __init__(self, doc, ui):
		Policy.__init__(self, doc, ui)

	def gen_refs(self):
		"""Generate and return the references for the given generator."""
		self.pages = [(self.make_out_path(), self.doc, [])]
		self.make_refs([1], { }, self.doc, 0, [])

	def make_refs(self, nums, others, node, pagenum, toc):
		"""Traverse the document tree and generate references in the given map."""
		
		# number for header
		if node.numbering() == 'header':
			path = self.make_out_path("-%d" % pagenum)
			toc = toc + [node]
			pagenum = pagenum + 1
			r = self.make_ref(nums)
			node.set_info("number", r)
			node.set_info("ref", path + "#" + r)
			nums.append(1)
			self.pages.append((path, node, toc))
			for item in node.getContent():
				pagenum = self.make_refs(nums, others, item, pagenum, toc)
			nums.pop()
			nums[-1] = nums[-1] + 1
		
		# number for embedded
		else:
			if self.doc.get_label_for(node):
				if num:
					if num not in others:
						others[num] = 1
						n = 1
					else:
						n = others[num] + 1
					r = "%s-%d" % (num, n)
					node.set_info("number", r)
					node.set_info("ref", path + "#" + r)
					others[num] = n
			for item in node.getContent():
				pagenum = self.make_refs(nums, others, item, pagenum, toc)

		return pagenum

	def gen_toc(self):
		self.template.gen_toc(self, self.current[1], 1)
		
	def gen_content(self):
		for node in self.current[0].getContent():
			if node.getHeaderLevel() < 0:
				html.gen(self, node)

	def get_ref(self, node):
		ref = node.get_info("ref")
		if not ref:
			return None
		path, anchor = ref.split('#')
		cpath = os.path.commonpath([path, self.out_path])
		return path[len(cpath):] + '#' + anchor

	def run(self):
		self.gen_refs()
		self.doc.pregen(self.db)
		for (path, node, toc) in self.pages:
			self.ui.print_command("generating %s" % path)
			self.open_out(path)
			self.current = (node, toc)
			self.template.apply(self)
			self.close_out()
			self.ui.print_success()


#------ plug-in interface ------

def output(doc, ui):
	org = doc['HTML_ONE_FILE_PER']
	if org == 'document' or not org:
		AllInOne(doc, ui)
	elif org == 'chapter':
		PerChapter(doc, ui)
	elif org == 'section':
		PerSection(doc, ui)
	else:
		raise BackException('one_file_per %s structure is not supported' % self.struct)


__short__ = "back-end for HTML output"
__description__ = \
"""Produces one or several HTML files. Auxiliary files (images, CSS, etc)
are stored in a directory named DOC-imports where DOC corresponds to the
the processed document DOC.thot.

Following variables are supported:
""" + common.make_var_doc([
	("HTML_ONE_FILE_PER",	"generated files: one of document (default), chapter, section"),
	("HTML_SHORT_ICON",		"short icon path for HTML file"),
	("HTML_STYLES",			"CSS styles to use (':' separated)"),
	("HTML_TEMPLATE",		"template used to generate pages")
])

