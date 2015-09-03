from ulif.openoffice.testing import envpath_wo_virtualenvs


class TestEnvPathWithoutVirtualEnvs(object):
    # tests for envpath_wo_virtualenvs.

    def test_no_PATH_set(self, monkeypatch):
        monkeypatch.delenv("PATH", raising=False)
        assert envpath_wo_virtualenvs() is None

    def test_no_VIRTUAL_ENV_set(self, monkeypatch):
        monkeypatch.setenv("PATH", "/tmp:/foo")
        monkeypatch.delenv("VIRTUAL_ENV", raising=False)
        assert envpath_wo_virtualenvs() == "/tmp:/foo"

    def test_single_virt_env_set(self, monkeypatch):
        monkeypatch.setenv("PATH", "/myvenv1/bin:/foo")
        monkeypatch.setenv("VIRTUAL_ENV", "/myvenv1")
        assert envpath_wo_virtualenvs() == "/foo"

