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
from pyomo.environ import SolverFactory


def _enable_idaes_ext_solvers():
    """
    Apply the steps required to be able to use the IDAES-EXT solvers, i.e. the solvers installed by the `idaes get-extensions` command, within the current Python process.
    
    Currently, importing the top-level `idaes` module is enough, as the necessary environment modifications
    are applied as an import side-effect.
    Additionally, since the standard Python import mechanism is used, calling this function again after the first time
    has no effect (and no impact on performance).
    """
    import idaes


def get_solver(solver_name: str):
    """
    Return a solver object from its name.

    This is a minimal wrapper around pyomo's SolverFactory, and all solver-related functionality is currently delegated to it.
    """

    _enable_idaes_ext_solvers()

    solver = SolverFactory(solver_name)
    # TODO add solver validation/error handling
    return solver
