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
from pyomo.opt.base.solvers import SolverFactory, OptSolver, check_available_solvers
from numbers import Number
from typing import Iterable


class SolverError(ValueError):
    "Base exception for solver-related errors"


class NoAvailableSolver(SolverError):
    def __init__(self, *choices: Iterable[str]):
        self.choices = choices

    def __str__(self):
        return f"No available solver found among choices: {self.choices}"


def _enable_idaes_ext_solvers() -> None:
    """
    Apply the steps required to be able to use the IDAES-EXT solvers, i.e. the solvers installed by the `idaes get-extensions` command, within the current Python process.

    Currently, importing the top-level `idaes` module is enough, as the necessary environment modifications
    are applied as an import side-effect.
    Additionally, since the standard Python import mechanism is used, calling this function again after the first time
    has no effect (and no impact on performance).
    """
    import idaes


def get_solver(*solver_names: Iterable[str]) -> OptSolver:
    """
    Return a solver object from one or more names.

    This is a thin wrapper around pyomo's SolverFactory; apart from basic validation to check if a solver is available, all functionality is currently delegated to it.

    Args:
        solver_names: one or more solver names to attempt for instantiating the solver object. If multiple names are given, the first available solver will be returned.

    Returns:
        The instantiated solver object.

    Raises:
        NoAvailableSolver if none of the choices succeed.
    """

    _enable_idaes_ext_solvers()

    for name in solver_names:
        solver = SolverFactory(name)
        if solver.available(exception_flag=False):
            break
    else:
        raise NoAvailableSolver(solver_names)
    # TODO add extra solver validation, logging, etc
    return solver


def set_timeout(solver: OptSolver, timeout_s: Number) -> OptSolver:
    """
    Set timeout (time limit) for solver in a solver-indipendent way.

    Args:
        solver: the solver object to which the option will be applied.
        timeout_s: the timeout, in seconds, to be applied as a solver option.
    Returns:
        The same solver object.
    Raises:
        SolverError if no mapping for the option key is found for the given solver.
    """
    name_key_mapping = {
        "gurobi": "timeLimit",
        "gurobi_direct": "timeLimit",
        "cbc": "seconds",
    }
    option_key = name_key_mapping.get(solver.name, None)
    if option_key is None:
        raise SolverError(
            f"No timeout option mapping found for {solver}: {name_key_mapping}"
        )
    solver.options[option_key] = float(timeout_s)
    return solver
