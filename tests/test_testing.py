from ulif.openoffice.testing import envpath_wo_virtualenvs


class TestEnvPathWithoutVirtualEnvs(object):
    # tests for envpath_wo_virtualenvs.

    def test_no_PATH_set(self, monkeypatch):
        # we require $PATH to be set.
        monkeypatch.delenv("PATH", raising=False)
        assert envpath_wo_virtualenvs() is None

    def test_no_VIRTUAL_ENV_set(self, monkeypatch):
        # we require $VIRTUAL_ENV to be set.
        monkeypatch.setenv("PATH", "/tmp:/foo")
        monkeypatch.delenv("VIRTUAL_ENV", raising=False)
        assert envpath_wo_virtualenvs() == "/tmp:/foo"

    def test_single_virt_env_set(self, monkeypatch):
        # with a single virtual env set we get a path list without it.
        monkeypatch.setenv("PATH", "/myvenv1/bin:/foo")
        monkeypatch.setenv("VIRTUAL_ENV", "/myvenv1")
        assert envpath_wo_virtualenvs() == "/foo"

    def test_venv_and_old_venv_set(self, monkeypatch):
        # with $VIRTUAL_ENV_BEFORE_TOX we get additional dirs removed
        monkeypatch.setenv("PATH", "/env2/.tox/bin:/env1/bin:/foo")
        monkeypatch.setenv("VIRTUAL_ENV", "/env2/.tox")
        monkeypatch.setenv("VIRTUAL_ENV_BEFORE_TOX", "/env1")
        assert envpath_wo_virtualenvs() == "/foo"
