from ulif.openoffice.testing import envpath_wo_virtualenvs


class TestEnvPathWithoutVirtualEnvs(object):
    # tests for envpath_wo_virtualenvs.

    def test_no_PATH_set(self, monkeypatch):
        monkeypatch.setenv("PATH", None)
        assert envpath_wo_virtualenvs() is None
