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

from pareto.strategic_water_management.strategic_produced_water_optimization import (
    WaterQuality,
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import (
    generate_report,
    PrintValues,
    OutputUnits,
    is_feasible,
    nostdout,
)
from importlib import resources
from pyomo.environ import (
    Constraint,
    Var,
    Binary,
    value,
    units,
    Constraint,
    Objective,
    minimize,
    SolverFactory,
    Param,
    Reals,
    ConcreteModel,
)

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from ipywidgets import FloatText, Button, Layout, GridspecLayout, ToggleButtons
from IPython.display import display

import os

# Check feasibility of the solved model
def _check_feasibility(model):
    with nostdout():
        feasibility_status = is_feasible(model)
    if not feasibility_status:
        print("Model results are not feasible and should not be trusted")
    else:
        print("Model results validated and found to pass feasibility tests")


def solve_MILP(df_sets, df_parameters):
    strategic_model = create_model(
        df_sets,
        df_parameters,
        default={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "node_capacity": True,
            "water_quality": WaterQuality.post_process,
        },
    )

    # Solve Pyomo model with specified options
    options = {
        # "solver": "cbc",  # If you don't have gurobi, uncooment this line to use free solver cbc
        "deactivate_slacks": True,
        "scale_model": False,
        "scaling_factor": 1000000,
        "running_time": 300,
        "gap": 0,
        "gurobi_numeric_focus": 1,
    }
    results_obj = solve_model(model=strategic_model, options=options)

    _check_feasibility(strategic_model)

    # [model, results_dict] = generate_report(
    #     strategic_model,
    #     # is_print=[PrintValues.essential],
    #     output_units=OutputUnits.user_units,
    #     fname="strategic_optimization_results_SRA_post_process.xlsx",
    # )

    model = strategic_model
    return model


def _free_variables(model, exception_list, time_period=None):
    for var in model.component_objects(Var):
        if var.name in exception_list:
            continue
        else:
            for index in var:
                is_in_time_period = True
                if index is not None and time_period is not None:
                    for i in index:
                        if i in model.s_T and i not in time_period:
                            is_in_time_period = False
                            break
                if not is_in_time_period:
                    continue
                index_var = var if index is None else var[index]
                # unfix binary variables and unbound the continuous variables
                if index_var.domain is Binary:
                    # index_var.free()
                    # index_var.unfix()
                    pass
                else:
                    index_var.unfix()
                    index_var.setlb(0)
                    index_var.setub(None)
    # NOTE Freeing up concentration variable
    return model


def _deactivate_slacks(model):
    model.v_C_Slack.fix(0)
    model.v_S_FracDemand.fix(0)
    model.v_S_Production.fix(0)
    model.v_S_Flowback.fix(0)
    model.v_S_PipelineCapacity.fix(0)
    model.v_S_StorageCapacity.fix(0)
    model.v_S_DisposalCapacity.fix(0)
    model.v_S_TreatmentCapacity.fix(0)
    # model.v_S_ReuseCapacity.fix(0)

    return model

def _add_MIQCP_cons_obj(model):
    def CostObjectiveFunctionRule2(model):
        return model.v_Z == (
            model.v_C_TotalSourced
            + model.v_C_TotalDisposal
            + model.v_C_TotalTreatment
            + model.v_C_TotalReuse
            + model.v_C_TotalPiping
            + model.v_C_TotalStorage
            + model.v_C_TotalTrucking
            + model.p_alpha_AnnualizationRate
            * (
                model.v_C_DisposalCapEx
                + model.v_C_StorageCapEx
                + model.v_C_TreatmentCapEx
                + model.v_C_PipelineCapEx
            )
            + model.v_C_Slack
            - model.v_R_TotalStorage
            # + 0.1*sum(model.quality.v_Q['R01', w, t] for w in model.s_QC for t in model.s_T)  # Reduce TDS at R01
        )

    model.ObjectiveFunction = Constraint(
        rule=CostObjectiveFunctionRule2, doc="MINLP objective function"
    )

    return model


def build_MIQCP(strategic_model):
    discrete_variables_names = {"v_X"}  # "v_Q", "v_X", "v_Z", "v_ObjectiveWithQuality"}
    _free_variables(
        strategic_model, discrete_variables_names
    )  # unfixed all variables except for dsicrete var names
    _deactivate_slacks(strategic_model)
    strategic_model.quality.objective.deactivate()
    strategic_model.CostObjectiveFunction.deactivate()

    strategic_model = _add_MIQCP_cons_obj(strategic_model)

    model = strategic_model

    return model
