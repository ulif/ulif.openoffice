import pytest
def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true",
        help="run slow tests")

def pytest_runtest_setup(item):
    if 'slow' in item.keywords and not item.config.getvalue("runslow"):
        pytest.skip("need --runslow option to run")

class MyPlugin:
    def pytest_pycollect_makeitem(collector, name, obj):
        unittest = sys.modules.get('unittest')
        if unittest is None:
            return # nobody can have derived unittest.TestCase
        try:
            issuite = isinstance(obj, unittest.TestSuite)
        except KeyboardInterrupt:
            raise
        except Exception:
            pass
        else:
            if issuite:
                return UnitTestSuite(name, parent=collector)
        return None

def pytest_collect_file(path, parent):
    return

class UnitTestSuite(pytest.Class):
    pass
