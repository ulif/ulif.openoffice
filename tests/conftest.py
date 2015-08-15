import os
import pytest
import subprocess
import sys
import time
from ulif.openoffice import oooctl
from ulif.openoffice.oooctl import check_port


@pytest.fixture(scope="function")
def envpath_no_venv(request, monkeypatch):
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
    monkeypatch.setenv("PATH", new_path)


@pytest.fixture(scope="function")
def home(request, tmpdir, monkeypatch):
    """Provide a new $HOME.
    """
    new_home = tmpdir.mkdir('home')
    monkeypatch.setenv('HOME', str(new_home))
    return new_home


@pytest.fixture(scope="function")
def run_lo_server(request, home, tmpdir, envpath_no_venv):
    """Start a libre office server.
    """
    if check_port("localhost", 2002):
        return
    script_path = os.path.splitext(oooctl.__file__)[0]
    log_path = tmpdir.join("loctl.log")
    cmd = "%s %s.py --stdout=%s start" % (
        sys.executable, script_path, log_path)
    # It would be nice, to work w/o shell here.
    with subprocess.Popen(cmd, shell=True) as proc:
        proc.wait()
    ts = time.time()
    while not check_port('localhost', 2002):
        time.sleep(0.5)
        if time.time() - ts > 3:
            break

    def stop_server():
        cmd = "%s %s.py stop" % (sys.executable, script_path)
        # It would be nice, to work w/o shell here.
        with subprocess.Popen(cmd, shell=True) as proc:
            proc.wait()
        ts = time.time()
        while check_port('localhost', 2002):
            time.sleep(0.5)
            if time.time() - ts > 3:
                break

    request.addfinalizer(stop_server)
    return cmd
