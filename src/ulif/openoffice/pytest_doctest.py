import os
import pkg_resources
import pytest, py
import re
import sys
import unittest
import zc.buildout.testing
from py._code.code import TerminalRepr, ReprFileLocation
from zope.testing import renormalizing

def pytest_pycollect_makeitem(collector, name, obj):
    doctest = sys.modules.get('doctest')
    if doctest is None:
        return # Nobody can have derived doctest.DocFileSuite

    try:
        isdocfilesuite = isinstance(obj, unittest.TestSuite)
    except KeyboardInterrupt:
        raise
    except Exception:
        pass
    else:
        if isdocfilesuite:
            return UnitTestSuite(name, parent=collector)
    return None

class UnitTestSuite(pytest.Class): #pytest.Collector):
    def reportinfo(self):
        return (self.name, None, '[XXXXXXXXX]')
    def collect(self):
        doctest = sys.modules.get('doctest')
        for doctestcase in self.obj:
            if not isinstance(doctestcase, doctest.DocFileCase):
                continue
            name = doctestcase.__repr__()
            yield DoctestItem(name, parent=self, obj=doctestcase)

    def setup(self):
        meth = getattr(self.obj, 'setUpClass', None)
        if meth is not None:
            meth()
        super(UnitTestSuite, self).setup()

    def teardown(self):
        meth = getattr(self.obj, 'tearDownClass', None)
        if meth is not None:
            meth()
        super(UnitTestSuite, self).teardown()


def pytest_addoption(parser):
    group = parser.getgroup("collect")
    group.addoption("--doctest",
        action="store_false", default=True,
        help="run doctests in all .py modules",
        dest="doctestclasses")

VERSION = pkg_resources.get_distribution('ulif.openoffice').version
class ReprFailDoctest(TerminalRepr):
    def __init__(self, reprlocation, lines):
        self.reprlocation = reprlocation
        self.lines = lines
    def toterminal(self, tw):
        for line in self.lines:
            tw.line(line)
        self.reprlocation.toterminal(tw)

class DoctestItem(pytest.Item):

    def __init__(self, name, parent=None, obj=None):
        super(DoctestItem, self).__init__(name, parent)
        self.obj = obj

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
        return self.fspath, None, "[doctest (%s)]" % (
            self.name,)

    def runtest(self):
        doctest = py.std.doctest
        testrunner = doctest.DocTestRunner()

        self.obj.debug()  # <-----------WORKS PARTIALLY
        return

class DoctestModule(DoctestItem, pytest.File):
    def runtest(self):
        doctest = py.std.doctest
        if self.fspath.basename == "conftest.py":
            module = self.config._conftest.importconftest(self.fspath)
        else:
            module = self.fspath.pyimport()
        failed, tot = doctest.testmod(
            module, raise_on_error=True, verbose=0,
            optionflags=doctest.ELLIPSIS)
