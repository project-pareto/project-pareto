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


def get_solver(solver_name: str):
    # importing idaes is required to apply the necessary modification to the environment
    # so that IDAES solvers (i.e. those installed with `idaes get-extensions`) can be used
    import idaes

    solver = SolverFactory(solver_name)
    # TODO add solver validation/error handling
    return solver
