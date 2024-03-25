#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2024 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################

import pyomo.environ as pyo
import pyomo.gdp as gdp
import re
import math
import contextlib
from pyomo.common.timing import TicTocTimer


def solve_model(
    model,
    solver="gurobi",
    time_limit=360,
    abs_gap=0.0,
    mip_flag=False,
    tee=False,
    status_check=True,
):

    disjunctions = [
        d for d in model.component_data_objects(ctype=gdp.Disjunct, descend_into=True)
    ]

    if len(disjunctions) >= 1:
        pyo.TransformationFactory("gdp.bigm").apply_to(model)

    opt = pyo.SolverFactory(solver)

    if solver == "gurobi":
        opt.options["TimeLimit"] = time_limit
        opt.options["MIPGap"] = abs_gap

        if not mip_flag:
            opt.options["NonConvex"] = 2

        opt.options["Threads"] = 8

    elif solver == "ipopt":
        opt.options["max_iter"] = 10000
        # opt.options['max_cpu_time'] = time_limit

    model.results = opt.solve(model, tee=tee)
    model.termination = model.results.solver.termination_condition

    if status_check:
        assert model.termination in ["infeasible", "optimal", "locallyOptimal"]

    return model


def parse_nonlinear_expressions(model, active=False):
    for c in model.component_data_objects(ctype=pyo.Constraint, descend_into=True):
        degree = c.body.polynomial_degree()
        if degree != 0 and degree != 1:
            c.activate() if active else c.deactivate()

    return model


def fix_binary_variables(model_to_fix, solved_model):
    for v in model_to_fix.component_data_objects(ctype=pyo.Var, descend_into=True):
        if v._domain == pyo.Binary:
            v.unfix()
            name = re.sub(r"\[.*?\]", "", v.name)
            v.fix(round(getattr(solved_model, name)[v._index].value, 0))

    return model_to_fix


def add_feasibility_cut(model, constraint_list):
    zeros, ones = {}, {}
    for v in model.component_data_objects(ctype=pyo.Var, descend_into=True):
        if v._domain == pyo.Binary:
            name = re.sub(r"\[.*?\]", "", v.name)
            (zeros if v.value < 0.5 else ones)[name] = v._index

    constraint_list.add(
        expr=sum(getattr(model, var)[index] for var, index in zeros.items())
        + sum(1 - getattr(model, var)[index] for var, index in ones.items())
        >= 1
    )

    return model


def get_objective_value(model):
    for o in model.component_data_objects(ctype=pyo.Objective, descend_into=True):
        if o._active:
            return o()


def integer_cut_decomposition(
    model: pyo.ConcreteModel,
    master_solver="gurobi",
    subproblem_solver="gurobi",
    time_limit=360,
    abs_gap=0.0,
    tee=False,
    iter_limit=100,
    rtol=1e-3,
    subproblem_warmstart=False,
    enable_status_outputs=False,
):
    # Start algorithm
    if enable_status_outputs:
        print("Starting decomposition")
    LB, UB, k = -math.inf, math.inf, 0
    best = None

    # Build master model
    master = model

    # Make it liear by deactivate nonlinear constraints
    master = parse_nonlinear_expressions(master, active=False)

    # Solve master problem
    if enable_status_outputs:
        print("Solve master problem")
    master = solve_model(
        master,
        solver=master_solver,
        time_limit=time_limit,
        abs_gap=abs_gap,
        mip_flag=True,
        tee=tee,
    )

    # If the relaxation of the original problem is infeasible, the problem is infeasible
    if master.termination == "infeasible":
        if enable_status_outputs:
            print("Original problem is infeasible")
        return master
    else:
        # Append the first lower bound
        LB = get_objective_value(master)
    # Create a list to append the cuts
    master.feasibility_cuts = pyo.ConstraintList()

    # Build subproblem
    subproblem = model

    while k < iter_limit:

        # If not warmsarting, rebuild the subproblem from scratch
        if not subproblem_warmstart and k > 0:
            subproblem = model

        # Build subproblem by fixing with the current solution of the master
        subproblem = fix_binary_variables(subproblem, master)

        # Solve subproblem
        if enable_status_outputs:
            print("Solve subproblem")
        subproblem = solve_model(
            subproblem,
            solver=subproblem_solver,
            time_limit=time_limit,
            abs_gap=abs_gap,
            mip_flag=False,
            tee=tee,
            status_check=True,
        )

        # If subproblem is infeasible, no bound update, so throw the cut right away
        if subproblem.termination != "infeasible":
            if enable_status_outputs:
                print("Feasible subproblem. Valid solution found")

            # If optimal subproblem check if improved the current best bound
            sub_objective = get_objective_value(subproblem)

            if sub_objective < UB:
                UB = sub_objective
                best = subproblem

            # Check if the bounds already crossed and return
            if UB < LB:
                if enable_status_outputs:
                    print("Bounds crossed. Returning best solution found")
                return best

            if (
                abs_gap == 0.0
                and master_solver == "gurobi"
                and subproblem_solver == "gurobi"
            ):
                # Check if bound converged and return
                if abs(UB - LB) / abs(max(LB, UB) + 1e-6) < rtol:
                    if enable_status_outputs:
                        print("Model solved. Relative tolerance reached")
                    return best

        # Add the cut
        if enable_status_outputs:
            print("Add integer cut")
        master = add_feasibility_cut(master, constraint_list=master.feasibility_cuts)

        if enable_status_outputs:
            print("Back to solving master")
        master = solve_model(
            master,
            solver=master_solver,
            time_limit=time_limit,
            abs_gap=abs_gap,
            mip_flag=True,
            tee=tee,
        )

        if master.termination == "infeasible":
            if best is None:
                if enable_status_outputs:
                    print(
                        "Master problem became infeasible. No solution found. Returning infeasible master"
                    )
                return master
            if enable_status_outputs:
                print("Master problem became infeasible. best solution found")
            return best
        else:
            # This should always be the case. We expect the master to be monotonically increasing
            master_obj = get_objective_value(master)
            if master_obj > LB:
                LB = master_obj

        k += 1
    if enable_status_outputs:
        print("Algorithm exceeded number of iterations. Returning best solution found")
    return best
