""" discover and run buildout-based doctests in modules and test files."""

import os
import pkg_resources
import pytest, py
import re
import zc.buildout.testing
from py._code.code import TerminalRepr, ReprFileLocation
from zope.testing import renormalizing

def pytest_addoption(parser):
    group = parser.getgroup("collect")
    group.addoption("--buildout-doctest-modules",
        action="store_true", default=False,
        help="run doctests in all .py modules",
        dest="buildoutdoctestmodules")
    group.addoption("--buildout-doctest-glob",
        action="store", default="test*.txt", metavar="pat",
        help="doctests file matching pattern, default: test*.txt",
        dest="buildoutdoctestglob")

def pytest_collect_file(path, parent):
    config = parent.config
    if path.ext == ".py":
        if config.option.buildoutdoctestmodules:
            return BuildoutDoctestModule(path, parent)
    elif (path.ext in ('.txt', '.rst') and parent.session.isinitpath(path)) or \
        path.check(fnmatch=config.getvalue("buildoutdoctestglob")):
        return BuildoutDoctestTextfile(path, parent)

VERSION = pkg_resources.get_distribution('ulif.openoffice').version

checker = renormalizing.RENormalizing([
    zc.buildout.testing.normalize_path,
    (re.compile(
        "Couldn't find index page for '[a-zA-Z0-9.]+' "
        "\(maybe misspelled\?\)"
        "\n"),
     ''),
    (re.compile("""['"][^\n"']+z3c.recipe.i18n[^\n"']*['"],"""),
     "'/z3c.recipe.i18n',"),
    (re.compile('#![^\n]+\n'), ''),
    (re.compile('Python/2\.\d\.\d'), 'Python/2.x.x'),
    (re.compile('-\S+-py\d[.]\d(-\S+)?.egg'),
     '-pyN.N.egg',),
    (re.compile(VERSION), '<VERSION>',), # This way we can write <VERSION>
                                         # in tests and it will match with
                                         # the current version of
                                         # ulif.openoffice, i.e. '0.2.2dev'
                                         # or similar.
    ])

class ReprFailDoctest(TerminalRepr):
    def __init__(self, reprlocation, lines):
        self.reprlocation = reprlocation
        self.lines = lines
    def toterminal(self, tw):
        for line in self.lines:
            tw.line(line)
        self.reprlocation.toterminal(tw)

class DoctestItem(pytest.Item):
    def repr_failure(self, excinfo):
        doctest = py.std.doctest
        if excinfo.errisinstance((doctest.DocTestFailure,
                                  doctest.UnexpectedException)):
            doctestfailure = excinfo.value
            example = doctestfailure.example
            test = doctestfailure.test
            filename = test.filename
            lineno = test.lineno + example.lineno + 1
            message = excinfo.type.__name__
            reprlocation = ReprFileLocation(filename, lineno, message)
            checker = py.std.doctest.OutputChecker()
            REPORT_UDIFF = py.std.doctest.REPORT_UDIFF
            filelines = py.path.local(filename).readlines(cr=0)
            i = max(test.lineno, max(0, lineno - 10)) # XXX?
            lines = []
            for line in filelines[i:lineno]:
                lines.append("%03d %s" % (i+1, line))
                i += 1
            if excinfo.errisinstance(doctest.DocTestFailure):
                lines += checker.output_difference(example,
                        doctestfailure.got, REPORT_UDIFF).split("\n")
            else:
                inner_excinfo = py.code.ExceptionInfo(excinfo.value.exc_info)
                lines += ["UNEXPECTED EXCEPTION: %s" %
                            repr(inner_excinfo.value)]

            return ReprFailDoctest(reprlocation, lines)
        else:
            return super(DoctestItem, self).repr_failure(excinfo)

    def reportinfo(self):
        name = self.fspath.basename
        return self.fspath, None, "[buildout-doctest (%s)]" % (
            name,)



def doctestsetup(test):
    zc.buildout.testing.buildoutSetUp(test)
    zc.buildout.testing.install_develop('ulif.openoffice', test)
    zc.buildout.testing.install_develop('zc.recipe.egg', test)

    # Set up all packages we rely on...
    req_pkgs = pkg_resources.get_distribution('ulif.openoffice').requires()
    req_pkgs = [x.project_name for x in req_pkgs
                if x.project_name not in ['setuptools', 'zc.buildout']]
    for requirement in req_pkgs:
            zc.buildout.testing.install_develop(requirement, test)

    # Create a home that openoffice.org can fiddle around with...
    os.mkdir('home')
    os.environ['HOME'] = os.path.abspath(os.path.join(os.getcwd(), 'home'))

    teardowns = test.globs['__tear_downs']
    test.__myteardowns = [x for x in test.globs['__tear_downs']]

def doctestteardown(test):
    for x in test.__myteardowns: x()

class BuildoutDoctestTextfile(DoctestItem, pytest.File):
    def runtest(self):
        doctest = py.std.doctest
        suite = doctest.DocFileSuite(
            str(self.fspath), module_relative=False,
            setUp =  doctestsetup,
            tearDown = doctestteardown,
            checker=checker,
            optionflags=doctest.ELLIPSIS,
            )
        suite.debug()

class BuildoutDoctestModule(DoctestItem, pytest.File):
    def runtest(self):
        doctest = py.std.doctest
        if self.fspath.basename == "conftest.py":
            module = self.config._conftest.importconftest(self.fspath)
        else:
            module = self.fspath.pyimport()
        failed, tot = doctest.testmod(
            module, raise_on_error=True, verbose=0,
            optionflags=doctest.ELLIPSIS)
