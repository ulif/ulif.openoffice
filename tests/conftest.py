import logging
import os
import py.path
import pytest
import subprocess
import sys
import tempfile
import time
from py.io import TextIO
from ulif.openoffice import oooctl
from ulif.openoffice.oooctl import check_port
from ulif.openoffice.testing import envpath_wo_virtualenvs


@pytest.fixture(scope='session')
def tmpdir_sess(request):
    """return a temporary py.path.local object which is unique
    for each test run (scope: session).

    Different to `tmpdir`, the path is removed immediately after test
    session.
    """
    sess_dir = py.path.local(tempfile.mkdtemp())
    request.addfinalizer(lambda: sess_dir.remove(rec=1))
    return sess_dir


@pytest.fixture(scope='session')
def monkeypatch_sess(request):
    """Like `monkeypatch` fixture, but for sessions.
    """
    from _pytest import monkeypatch
    mpatch = monkeypatch.monkeypatch()
    request.addfinalizer(mpatch.undo)
    return mpatch


@pytest.fixture(scope="session", autouse=True)
def envpath_no_venv(request, monkeypatch_sess):
    """Strip virtualenv path from system environment $PATH (scope: session).

    For the test remove virtualenv path from $PATH.

    We use this fixture here to ensure that virtualenvs can be used in
    tests but do not interfere with `unoconv` path and needed libs.

    In other words: with this fixture we can run tests in Python
    versions, that normally do not support `uno` and other packages
    needed by `unoconv`.
    """
    new_path = envpath_wo_virtualenvs()
    if not new_path:
        return
    monkeypatch_sess.setenv("PATH", new_path)


@pytest.fixture(scope="session")
def home(request, tmpdir_sess, monkeypatch_sess):
    """Provide a new $HOME (scope: session).
    """
    new_home = tmpdir_sess.mkdir('home')
    monkeypatch_sess.setenv('HOME', str(new_home))
    return new_home


@pytest.fixture(scope="session")
def lo_server(request, home, tmpdir_sess, envpath_no_venv):
    """Start a libre office server (scope: session).

    session-scoped test fixture. Sets new $HOME.
    """
    if check_port("localhost", 2002):
        return
    script_path = os.path.splitext(oooctl.__file__)[0]
    log_path = tmpdir_sess.join("loctl.log")
    cmd = "%s %s.py --stdout=%s start" % (
        sys.executable, script_path, log_path)
    # It would be nice, to work w/o shell here.
    proc = subprocess.Popen(cmd, shell=True)
    proc.wait()
    ts = time.time()
    nap = 0.1
    while not check_port('localhost', 2002):
        time.sleep(nap)
        nap = nap * 2
        if time.time() - ts > 3:
            break

    def stop_server():
        cmd = "%s %s.py stop" % (sys.executable, script_path)
        # It would be nice, to work w/o shell here.
        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()
        ts = time.time()
        nap = 0.1
        while check_port('localhost', 2002):
            time.sleep(nap)
            nap = nap * 2
            if time.time() - ts > 3:
                break

    request.addfinalizer(stop_server)
    return proc


@pytest.fixture(scope="function")
def workdir(request, tmpdir, monkeypatch):
    """Provide a working dir (scope: function).

    Creates a temporary directory with subdirs 'src/', 'cache/', and
    'tmp/'. In 'src/sample.txt' a simple text file is created.

    The system working directory is changed to the temporary dir during
    test.

    Global root temporary dir is set to the newly created 'tmp/' dir
    during test.
    """
    tmpdir.mkdir('src')
    tmpdir.mkdir('cache')
    tmpdir.mkdir('tmp')
    tmpdir.join('src').join('sample.txt').write('Hi there!')
    monkeypatch.chdir(tmpdir)
    monkeypatch.setattr(tempfile, 'tempdir', str(tmpdir.join('tmp')))
    return tmpdir


@pytest.fixture(scope="function")
def conv_env(workdir):
    """Get the py.path local to a docconverter environment.

    A converter environment contains a `workdir` which is returned.

    The path contains additionally ``sample1.ini`` with content copied
    from local ``inputs/sample1.ini``, a cache dir named ``cache`` and a
    file ``paste.ini``, copied from ``input/sample2.ini`` and with all
    cache dir references pointing to the local cache dir.
    """
    input_path = os.path.join(os.path.dirname(__file__), "input")
    input_dir = workdir.new(dirname=input_path, basename="")
    workdir.join("sample1.ini").write(input_dir.join("sample1.ini").read())
    paste_conf2 = input_dir.join("sample2.ini").read().replace(
        "/tmp/mycache", str(workdir / "cache"))
    workdir.join("paste.ini").write(paste_conf2)
    return workdir


@pytest.fixture(scope="function")
def conv_logger(request):
    """`py.io.TextIO` stream capturing log messages (scope:funcion).

    Captures messages to 'ulif.openoffice.convert' logger. Text can be
    retrieved with `conv_logger.getvalue()`.
    """
    stream = TextIO()
    logger = logging.getLogger('ulif.openoffice.convert')
    entry_level = logger.level
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream)

    def cleanup():
        logger.removeHandler(handler)
        logger.setLevel(entry_level)

    logger.addHandler(handler)
    request.addfinalizer(cleanup)
    return stream


@pytest.fixture(scope="function")
def samples_path(request):
    """Get path of local samples dir (scope: function).

    The path is delivered as `py.path.local` path for your
    convenience.
    """
    samples_dir = py.path.local(__file__).dirpath("input")
    assert samples_dir.check()  # make sure the path exists really
    return samples_dir
