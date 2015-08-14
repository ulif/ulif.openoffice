import os
import pytest
import sys
import ulif.openoffice.oooctl
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
def run_lo_server(request, home, tmpdir):
    """Start a libre office server.
    """
    server_running = False
    if check_port("localhost", 2002):
        server_running = True
    script_path = os.path.dirname(ulif.openoffice.__file__)
    script_path = os.path.splitext(script_path)[0]
    log_path = tmpdir.join("loctl.log")
    cmd = "%s %s.py --stdout=%s start" % (
        sys.executable, script_path, log_path)
    return cmd
