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


@pytest.fixture(scope='session')
def tmpdir_sess(request):
    """return a temporary py.path.local object which is unique
    for each test run.

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
    """Strip virtualenv path from system environment $PATH.

    For the test remove virtualenv path from $PATH.

    We use this fixture here to ensure that virtualenvs can be used in
    tests but do not interfere with `unoconv` path and needed libs.

    In other words: with this fixture we can run tests in Python
    versions, that normally do not support `uno` and other packages
    needed by `unoconv`.
    """
    _path = os.environ.get('PATH', None)
    if not _path:
        return
    v_env_path = os.environ.get('VIRTUAL_ENV', None)
    if not v_env_path or (v_env_path not in _path):
        return
    new_path = ":".join([
        x for x in _path.split(":")
        if v_env_path not in x]
        )
    monkeypatch_sess.setenv("PATH", new_path)


@pytest.fixture(scope="session")
def home(request, tmpdir_sess, monkeypatch_sess):
    """Provide a new $HOME.
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
def conv_logger(request):
    """`py.io.TextIO` stream capturing log messages.

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
