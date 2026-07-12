import re

import pyalgoviz


def test_package_importable():
    assert re.fullmatch(r"\d+\.\d+\.\d+", pyalgoviz.__version__)
