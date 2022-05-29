#!/usr/bin/python3
import subprocess
import sys

THOT = "../thot.py"

class Test:

	def __init__(self, label, file = None, params = ""):
		self.label = label
		if file == None:
			self.file = label + ".thot"
		else:
			self.file = file
		self.params = params

	def process(self, dump = False):
		sys.stderr.write("%s ....\n" % self.label)
		sys.stderr.flush()
		ret = subprocess.run(
			"%s %s %s 2> %s.log" % \
				(THOT, self.file, self.params, self.label),
			shell=True
		)
		if ret.returncode == 0:
			sys.stderr.write("%s ... [OK]\n" % self.label)
			return True
		else:
			if dump:
				sys.stderr.write("\n")
				for l in open("%s.log" % self.label).readlines():
					sys.stderr.write(l)
				sys.stderr.write("%s ... [Failed]\n" % self.label)
			else:
				sys.stderr.write("%s ... [Failed] (log in \"%s.log\")\n" \
					% (self.label, self.label))
			return False

ALL = [
	Test("html-all", "dokuwiki.thot"),
	Test("html-chapter", "dokuwiki.thot", "-DHTML_ONE_FILE_PER=chapter"),
	Test("html-section", "dokuwiki.thot", "-DHTML_ONE_FILE_PER=section"),
#	Test("simple-html", "simple.thot"),
#	Test("simple-latex", "simple.thot", "-t latex"),	
#	Test("simple-docbook", "simple.thot", "-t docbook"),
#	Test("textile-html", "textile.thot"),
#	Test("markdown-html", "markdown.thot"),
#	Test("unicode-html", "unicode.thot"),
#	Test("lexicon-html", "lexicon.thot"),
#	Test("doxygen-html", "doxygen.thot"),
#	Test("wiki", "wiki.thot", "-t wiki")
]


# main
if len(sys.argv) == 1:
	for t in ALL:
		if not t.process(False):
			break
elif sys.argv[1] == "-l":
	sys.stderr.write("Available tests:\n")
	for t in ALL:
		sys.stderr.write("- %s\n" % t.label)
	sys.exit(0)
else:
	for t in ALL:
		if t.label in sys.argv[1:]:
			if not t.process(True):
				break

	
