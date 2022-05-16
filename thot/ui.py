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

"""Human user interface."""

import os.path
import re
import sys

from thot.common import *
import thot.tparser as tparser


# ANSI coloration
def supports_ansi():
	plat = sys.platform
	supported_platform = plat != 'Pocket PC' and \
		(plat != 'win32' or 'ANSICON' in os.environ)
	is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
	return supported_platform and is_a_tty

IS_ANSI = supports_ansi()

NORMAL = "\033[0m"
"""Switch back console display to normal mode."""
BOLD = "\033[1m"
"""Switch console display to bold."""
FAINT = "\033[2m"
"""Switch console display to faint."""
ITALIC = "\033[3m"
"""Switch console display to italic."""
UNDERLINE = "\033[4m"
"""Switch console display to underline."""
BLACK = "\033[30m"
"""Switch console display to foreground black."""
RED = "\033[31m"
"""Switch console display to foreground red."""
GREEN = "\033[32m"
"""Switch console display to foreground green."""
YELLOW = "\033[33m"
"""Switch console display to foreground yellow."""
BLUE = "\033[34m"
"""Switch console display to foreground blue."""
MAGENTA = "\033[35m"
"""Switch console display to foreground magenta."""
CYAN = "\033[36m"
"""Switch console display to foreground cyan."""
WHITE = "\033[37m"
"""Switch console display to foreground white."""
BACK_BLACK = "\033[40m"
"""Switch console display to background black."""
BACK_RED = "\033[41m"
"""Switch console display to background red."""
BACK_GREEN = "\033[42m"
"""Switch console display to background green."""
BACK_YELLOW = "\033[43m"
"""Switch console display to background yellow."""
BACK_BLUE = "\033[44m"
"""Switch console display to background blue."""
BACK_MAGENTA = "\033[45m"
"""Switch console display to background magenta."""
BACK_CYAN = "\033[46m"
"""Switch console display to background cyan."""
BACK_WHITE = "\033[47m"
"""Switch console display to background white."""


# execution context
class NullStream:
	"""Stream that prints nothings."""
	
	def write(self, line):
		pass


null_stream = NullStream()

class UI:
	"""A context is used to configure the execution of an action."""
	out = sys.stdout
	err = sys.stderr
	command_ena = False
	info_ena = True
	quiet = False
	complete_quiet = False
	action = None
	flushed = False
	verbose = False

	def set_verbose(self, verb):
		"""Enable/disable verbosity."""
		self.verbose = verb

	def say(self, f):
		"""Display a verbose messafe. f is a function that is called
		if verbosity is enabled."""
		if self.verbose:
			f(self.err)
	
	def handle_action(self):
		"""Manage a pending action display."""
		if self.action and not self.flushed:
			sys.stderr.write("\n")
			self.flushed = True
	
	def print_command(self, cmd):
		"""Print a command before running it."""
		if not self.quiet and self.command_ena:
			self.handle_action()
			sys.stderr.write(CYAN + "> " + str(cmd) + NORMAL + "\n")
			sys.stderr.flush()
	
	def print_info(self, info):
		"""Print information line about built target."""
		if not self.quiet and self.info_ena:
			self.handle_action()
			sys.stderr.write(BOLD + BLUE + str(info) + NORMAL + "\n")
			sys.stderr.flush()

	def print_def(self, term, desc):
		"""Print a definition made of term and a description."""
		if not self.quiet and self.info_ena:
			self.handle_action()
			sys.stderr.write(BOLD + BLUE + str(term) + NORMAL + desc + "\n")		
			sys.stderr.flush()

	def print_error(self, msg):
		"""Print an error message."""
		if not self.complete_quiet:
			self.handle_action()
			sys.stderr.write(BOLD + RED + "ERROR: " + str(msg) + NORMAL + "\n")
			sys.stderr.flush()
	
	def print_warning(self, msg):
		"""Print a warning message."""
		if not self.complete_quiet:
			self.handle_action()
			sys.stderr.write(BOLD + YELLOW + "WARNING: " + str(msg) + NORMAL + "\n")
			sys.stderr.flush()

	def print_success(self, msg):
		"""Print a success message."""
		if not self.complete_quiet:
			self.handle_action()
			sys.stderr.write(BOLD + GREEN + "[100%] " + msg + str(NORMAL) + "\n")
			sys.stderr.flush()

	def print_action(self, msg):
		"""Print a beginning action."""
		if not self.quiet:
			sys.stderr.write("%s ... " % msg)
			sys.stderr.flush()
			self.action = msg
			self.flushed = False
	
	def print_action_final(self, msg):
		if not self.quiet:
			if self.flushed:
				sys.stderr.write("%s ... " % self.action)				
			sys.stderr.write(msg)
			sys.stderr.write("\n");
			sys.stderr.flush()
			self.action = None
			self.flushed = False
	
	def print_action_success(self, msg = ""):
		"""End an action with success."""
		if msg:
			msg = "(%s) " % msg
		self.print_action_final(msg + GREEN + BOLD + "[OK]" + NORMAL)

	def print_action_failure(self, msg = ""):
		"""End an action with failure."""
		if msg:
			msg = "(%s) " % msg
		self.print_action_final(msg + RED + BOLD + "[FAILED]" + NORMAL)

	def print(self, msg):
		self.out.write(msg + "\n")

DEF = UI()

SLASH_COLOR = "\033[4m"
VAR_COLOR = "\033[3m"
slash_re = re.compile("\\\\(.)")
slash_rep = SLASH_COLOR + "\\1" + NORMAL
var_re = re.compile("\\/([a-zA-Z][a-zA-Z0-9]*)\\/")
var_rep = VAR_COLOR + "\\1" + NORMAL
def decorate_syntax(t):
	"""Colorize, if available, escaped special characters."""
	l = len(t)
	if not IS_ANSI:
		return (l, t)
	else:
		(t, cs) = slash_re.subn(slash_rep, t)
		(t, cv) = var_re.subn(var_rep, t)
		return (l - cs - 2 * cv, t)


arg_re = re.compile("\(\?P<([a-zA-Z0-9]+)(_[a-zA-Z0-9_]*)?>(%s|%s)*\)" %
	("[^)[]", "\[[^\]]*\]"))
REPS = [
	(" ", 		u"␣"	),
	("\t", 		u"⭾"	),	
	("\\s+",	" "		),
	("\\s*", 	" "		),
	("\\s", 	" "		),
	("\(", 		"("		),
	("\)", 		")"		),
	("^", 		""		),
	("$", 		""		)
]
def prepare_syntax(t):
	"""Prepare a regular expression to be displayed to human user."""
	if t == "^$" or t == "^\s+$":
		return "\\n"
	t = arg_re.sub('/\\1/', t)
	for (p, r) in REPS:
		t = t.replace(p, r)
	return t.strip()


def display_syntax(syn, ui):
	"""Display list of syntax items. syn is a sequence of pairs (s, d)
	where s is the syntax and d is the documentation. The documentation
	may be split in several lines."""
	
	# find row size
	(w, _) = os.get_terminal_size()
	
	# prepare the strings
	syn = [(decorate_syntax(s), d) for (s, d) in syn]
	
	# display the strings
	m = min(16, 1 + max([l for ((l, _), _) in syn]))
	for ((l, r), d) in syn:
		ls = d.split("\n")
		if l > m:
			ui.print("%s:" % r)
		else:
			ui.print("%s:%s%s" % (r, " " * (m - l), ls[0][0:min(w, len(ls[0]))]))
			if len(ls[0]) > w:
				ls[0] = ls[0][w:]
			else:
				ls = ls[1:]
		for l in ls:
			while len(l) > w:
				ui.print("%s %s" % (" " * m, l[:w]))
				l = l[w:]
			ui.print("%s %s" % (" " * m, l))


def list_available_modules(env, ui):
	"""List available modules."""
	
	ui.print("Available modules:")
	paths = env["THOT_USE_PATH"]
	names = set([os.path.splitext(file)[0]
		for path in paths.split(":") for file in os.listdir(path)
			if os.path.splitext(file)[1] in { ".py" } and not file.startswith("__")])
	for name in names:
		mod = load_module(name, paths)
		desc = ""
		if "__short__" in mod.__dict__:
			desc = " (%s)" % mod.__short__
		ui.print("- %s%s" % (name, desc))

	ui.print("\nAvailable back-ends:")
	path = os.path.join(env["THOT_LIB"], "backs")
	names = set([os.path.splitext(file)[0]
		for file in os.listdir(path)
			if os.path.splitext(file)[1] in { ".py" }
			and not file.startswith("__")])
	for name in names:
		mod = load_module(name, path)
		desc = ""
		if "__short__" in mod.__dict__:
			desc = " (%s)" % mod.__short__
		ui.print("- %s%s" % (name, desc))


def list_module_content(name, env, ui):
	"""Print the description of a module."""
	paths = env["THOT_USE_PATH"] + ":" + os.path.join(env["THOT_LIB"], "backs")
	mod = load_module(name, paths)
	if not mod:
		ui.print_error("no module named %s" % name)
		return
	short = ""
	if "__short__" in mod.__dict__:
		short = " (%s)" % mod.__short__
	ui.print("Module: %s%s" % (name, short))
	if "__description__" in mod.__dict__:
		ui.print("\n%s" % mod.__description__)
	syn = []
	if "__words__" in mod.__dict__:
		for (_, word, desc) in mod.__words__:
			syn.append((prepare_syntax(word), desc))
	if "__lines__" in mod.__dict__:
		for (_, line, desc) in mod.__lines__:
			syn.append((prepare_syntax(line), desc))
	if "__syntaxes__" in mod.__dict__:
		for m in mod.__syntaxes__:
			syn = syn + m.get_doc()
	if syn != []:
		ui.print("Syntax:")
		display_syntax(syn, ui)
	has_output = False
	for out in ["html", "latex", "docbook"]:
		name = "__%s__" % out
		if name in mod.__dict__:
			if not has_output:
				has_output = True
				ui.print("\nOutput:")
			ui.print("\t%s:" % out)
			for (form, desc) in mod.__dict__[name]:
				ui.print("\t%s\n\t\t%s" % (form, desc))


def list_available_syntax(doc, ui):
	"""List syntax available in the current parser."""
	ui.print("Available syntax:")
	syn = []
	for mod in doc.get_uses() + [tparser]:
		if "__words__" in mod.__dict__:
			syn = syn + [(prepare_syntax(w), d) for (_, w, d) in mod.__words__] 
		if "__lines__" in mod.__dict__:
			syn = syn + [(prepare_syntax(l), d) for (_, l, d) in mod.__words__]
		if "__syntaxes__" in mod.__dict__:
			for s in mod.__syntaxes__:
				syn = syn + s.get_doc()
	if syn != []:
		display_syntax(syn, ui)


def list_outputs(doc, ui):
	"""List the output modules in the given document."""
	ui.print("Available outputs:")
	for mod in doc.get_uses():
		ui.print("- %s" % mod.__name__)
		name = "__%s__" % options.list_output
		if name in mod.__dict__:
			for (form, desc) in mod.__dict__[name]:
				ui.print("\t%s\n\t\t%s" % (form, desc))


def list_modules(doc, ui):
	"""List the modules used in the document."""
	ui.print("Used modules:")
	for mod in doc.get_uses():
		desc = ""
		if "__short__" in mod.__dict__:
			desc = " (%s)" % mod.__short__
		ui.print("- %s%s" % (mod.__name__, desc))
