"""
Test that headers are on all files
"""
# stdlib
from pathlib import Path
import os

# third-party
from addheader.add import FileFinder, detect_files
import pytest
import yaml


@pytest.fixture
def package_root():
    """Determine package root."""
    import pareto

    return Path(pareto.__file__).parent


@pytest.fixture
def patterns(package_root):
    """Grab glob patterns from config file."""
    conf_file = package_root.parent / ".addheader.yml"
    if not conf_file.exists():
        print(
            f"Cannot load configuration file from '{conf_file}'. Perhaps this is not development mode?"
        )
        return None
    with open(conf_file) as f:
        conf_data = yaml.safe_load(f)
    print(f"Patterns for finding files with headers: {conf_data['patterns']}")
    return conf_data["patterns"]


@pytest.mark.unit
def test_headers(package_root, patterns):
    if patterns is None:
        print(f"ERROR: Did not get glob patterns: skipping test")
    else:
        # modify patterns to match the files that should have headers
        ff = FileFinder(package_root, glob_patterns=patterns)
        has_header, missing_header = detect_files(ff)
        # ignore empty files (probably should add option in 'detect_files' for this)
        nonempty_missing_header = list(
            filter(lambda p: p.stat().st_size > 0, missing_header)
        )
        #
        if len(nonempty_missing_header) > 0:
            pfx = str(package_root.resolve())
            pfx_len = len(pfx)
            file_list = ", ".join(
                [str(p)[pfx_len + 1 :] for p in nonempty_missing_header]
            )
            print(f"Missing headers from files under '{pfx}{os.path.sep}': {file_list}")
        # uncomment to require all files to have headers
        assert len(nonempty_missing_header) == 0
