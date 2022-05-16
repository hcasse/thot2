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
"""Definition of document base."""

import datetime
import locale
import os
import os.path

import thot
from thot.common import *
from thot.ui import *


class DB(MapEnvironment, UI):
	"""Manage common information between documents of a documentation
	base."""

	def __init__(self, rootdir = None, env = None):
		if env == None:
			env =  OS_ENV
		MapEnvironment.__init__(self, env, "DB")
		if rootdir == None:
			rootdir = os.getcwd()
		self.rootdir = rootdir
		self.langs = { }
		self["THOT_VERSION"] = THOT_VERSION
		self["ENCODING"] = locale.getpreferredencoding()
		self["THOT_BASE"] = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'share/thot') + '/'
		self["THOT_LIB"] = os.path.abspath(os.path.dirname(thot.__file__))
		self["THOT_USE_PATH"] = self["THOT_LIB"] + "/mods/"
		self["THOT_DATE"] = str(datetime.datetime.today())
	def get_rootdir(self):
		"""Get the root directory."""
		return self.get_rootdir()

	def set_rootdir(self, path):
		"""Set the root directory."""
		self.rootdir = path

	def get_link(self, id, path = None):
		""""Get the link corresponding to the given identifier.
		If the path is given, the returned link path is relative
		to this path."""
		return None

	def new_friend(self, id = None, doc = None, path = None):
		"""Create a new friend file to write to in the output.
		If an identifier is given, this will allow to perform lazy
		update. Return the path to the friend file.
		IF a path is given the returned path is relative to this path."""
		return None

	def declare_friend(self, path, rel_path = None):
		"""Declare an existing file as friend. The possible new path
		to the friend is returned. If rel_path is given, the returned
		path is relative to this path."""
		return None

	def get_translator(self, lang):
		"""Get the translator for the given language."""
		pass

	def get_translator(self, doc):
		"""Get the translator for the given document."""
		lang = doc.get_symbol("LANG")
		if lang == None:
			lang = self.get_symbol("LANG")
			if lang == None:
				lang, _ = locale.getdefaultlocale()
		try:
			return self.langs[lang]
		except:
			t = i18n.get_translator(lang)
			self.langs[lang] = t
			return t
