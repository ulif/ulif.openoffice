# tests for oooctl module
import pytest
from ulif.openoffice.oooctl import get_options


class TestOOOCtl(object):

    def test_get_options(self):
        cmd, options = get_options(["fakeoooctl", "start"])
        assert cmd == "start"
        assert options.binarypath is not None
        assert options.pidfile == "/tmp/ooodaemon.pid"

    def test_get_options_no_argv(self):
        with pytest.raises(SystemExit) as why:
            get_options(argv=[])
        code = getattr(why.value, "code", why.value)
        assert code == 2

    def test_get_options_invalid_command(self):
        with pytest.raises(SystemExit) as why:
            get_options(argv=['fakeoooctl', 'maybestart'])
        code = getattr(why.value, "code", why.value)
        assert code == 2

    def test_get_options_too_many_args(self):
        with pytest.raises(SystemExit) as why:
            get_options(argv=['fakeoooctl', 'too', 'much'])
        code = getattr(why.value, "code", why.value)
        assert code == 2

    def test_get_options_invalid_binpath(self):
        # we should not pass an invalid path to executable
        with pytest.raises(SystemExit) as why:
            get_options(argv=['fakeoooctl', '-b', 'invalid-path', 'start'])
        code = getattr(why.value, "code", why.value)
        assert code == 2
