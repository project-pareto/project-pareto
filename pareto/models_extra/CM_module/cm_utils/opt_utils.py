#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2025 by the software owners:
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
Functions used in run_infrastructure_analysis.py
"""

from pareto.models_extra.CM_module.models.qcp_br import build_qcp_br
import pyomo.environ as pyo
from pareto.models_extra.CM_module.cm_utils.gen_utils import (
    obj_fix,
    alter_nonlinear_cons,
)
from pareto.utilities.solvers import get_solver


def max_theoretical_recovery_flow_opt(
    model, desal_unit: str, cm_name: str, desired_cm_conc, tee=False
):
    """
    This function computes the largest flow possible to
    the treatment unit while still keeping the Li
    concentration above the desired level.

    Arguments:
    model: pyomo qcp base model
    treatment_unit: name of desalination unit
    cm_name: name of critical mineral to be assessed
    desired_cm_conc: minimum CM concentration requirement
    """
    assert cm_name in model.s_Q, f"{cm_name} is not a valid component to the base model"
    assert (
        model.p_alpha[desal_unit, cm_name] > 0.999
    ), "to use this tool you need to have perfect separation of the critical mineral"

    alphaW = model.p_alphaW[desal_unit]
    # desired concentration at the inlet - this will be corrected at the end
    desired_cm_conc = desired_cm_conc * (1 - alphaW)

    mm = pyo.ConcreteModel()
    mm.S = list(model.p_FGen.index_set())
    bounds = {k: (0, model.p_FGen[k] * 7) for k in mm.S}
    mm.F = pyo.Var(mm.S, bounds=bounds)
    mm.cumulative_F = pyo.Var(bounds=(10, None))
    mm.cumulative_F_con = pyo.Constraint(
        expr=mm.cumulative_F == sum(mm.F[t] for t in mm.S)
    )
    mm.obj = pyo.Objective(expr=mm.cumulative_F, sense=pyo.maximize)
    mm.total_li = pyo.Expression(
        expr=sum(mm.F[t] * model.p_CGen[t[0], cm_name, t[1]] for t in mm.S)
    )
    mm.quality_con = pyo.Constraint(
        expr=mm.total_li >= desired_cm_conc * mm.cumulative_F
    )

    status = get_solver("ipopt").solve(mm, tee=tee)
    pyo.assert_optimal_termination(status)
    return pyo.value(mm.cumulative_F) * (1 - alphaW)


def max_recovery_with_infrastructure(data, tee=False):
    # build the model from the loaded data
    model = build_qcp_br(data)

    ###
    # First, we solve a flow-based LP without any concentration variables
    ###
    model.obj.deactivate()
    model.br_obj.deactivate()
    model.treatment_only_obj.activate()

    # create lists of constraints involving concentrations and all flow / inventory variables
    model = alter_nonlinear_cons(model, deactivate=True)

    # Solve the linear flow model
    print("   ... running linear flow model")
    opt = get_solver("ipopt")
    status = opt.solve(model, tee=tee)

    # terminating script early if optimal solution not found
    pyo.assert_optimal_termination(status)

    ###
    # Bilinear NLP
    ###

    # unfixing all the initialized variables
    model = alter_nonlinear_cons(model, deactivate=False)

    # solve for the maximum possible recovery revenue given this infrastructure
    model.TINflow.deactivate()
    for k in model.Dflow:
        if k[0].endswith("TW") or k[0].endswith("CW"):
            model.Dflow[k].deactivate()

    # running bilinear model
    print("   ... running bilinear model")
    opt = get_solver("ipopt")
    opt.options["ma27_pivtol"] = 1e-2
    opt.options["tol"] = 1e-6
    status = opt.solve(model, tee=tee)
    pyo.assert_optimal_termination(status)
    print(
        "Max critical mineral revenue with existing infrastructure:",
        pyo.value(model.treat_rev),
    )
    return model


def cost_optimal(data, tee=False):
    # build the model from the loaded data
    model = build_qcp_br(data)

    ###
    # First, we solve a flow-based LP without any concentration variables
    ###

    # create lists of constraints involving concentrations and all flow / inventory variables

    model = alter_nonlinear_cons(model, deactivate=True)

    # Solve the linear flow model
    print("   ... running linear flow model")
    opt = get_solver("ipopt")
    status = opt.solve(model, tee=tee)

    # terminating script early if optimal solution not found
    pyo.assert_optimal_termination(status)

    ###
    # Bilinear NLP
    ###

    # unfixing all the initialized variables
    model = alter_nonlinear_cons(model, deactivate=False)

    # running bilinear model
    print("   ... running bilinear model")
    opt = get_solver("ipopt")
    opt.options["max_iter"] = 10000
    status = opt.solve(model, tee=tee)
    pyo.assert_optimal_termination(status)
    return model
