from importlib import metadata

import pytest
from packaging.version import Version


def test_pandas():
    v = Version(metadata.version("pandas"))
    assert v.major > 1, f"pandas {v} is not supported"

