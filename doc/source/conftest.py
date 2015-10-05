import pytest
from ulif.openoffice.testing import envpath_wo_virtualenvs


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
