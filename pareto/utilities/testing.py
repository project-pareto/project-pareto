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
from contextlib import nullcontext as does_not_raise
from typing import Any

import _pytest


def get_readable_param(obj: Any):
    """
    Return a more readable representation of an object.

    Use as the `ids` argument of parametrize/pytest.mark.parametrize.
    """
    if isinstance(obj, (tuple, list)):
        return str.join(",", obj)
    if "RaisesContext" in type(obj).__name__:
        return "(should raise)"
    if isinstance(obj, does_not_raise):
        return "(should not raise)"
