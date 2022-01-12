#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021 by the software owners: The
# Regents of the University of California, through Lawrence Berkeley National Laboratory, et al. All
# rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the
# U.S. Government consequently retains certain rights. As such, the U.S. Government has been granted
# for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license
# in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit other to do so.
#####################################################################################################
from _pytest.config import Config


_MARKERS = {
    "unit": "quick tests that do not require a solver, must run in < 2 s",
    "component": "quick tests that may require a solver",
    "integration": "long duration tests",
}


def pytest_configure(config: Config):

    for name, descr in _MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {descr}")
