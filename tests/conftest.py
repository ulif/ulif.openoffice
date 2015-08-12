import os
import pytest

@pytest.fixture(scope="function")
def reset_sys_path(request):
    _path = os.environ.get('PATH', None)

    def teardown():
        if _path is not None:
            os.environ.set('PATH', _path)

    request.addfinalizer(teardown)
