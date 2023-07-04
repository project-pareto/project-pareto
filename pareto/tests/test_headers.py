#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2023 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################
"""
Test that headers are on all files
"""
# stdlib
from pathlib import Path
import os

# third-party
import pytest

yaml = pytest.importorskip("yaml", reason="pyyaml not available")
_ = pytest.importorskip("addheader", reason="addheader not available")
from addheader.add import FileFinder, detect_files


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
