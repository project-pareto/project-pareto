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
This code is created to evaluate the expected value of the stochastic model with the given
scenarios. It first solves the expected-value (EV) problem by averaging the parameters across
scenarios, then extracts the first-stage decisions from the EV solution, and finally solves
the stochastic model with these first-stage decisions fixed to compute the expected EV (EEV).
"""

import pyomo.environ as pyo
from pyomo.environ import Constraint, Var, Expression, units as pyunits, value
import re

import pandas as pd
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    WaterQuality,
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
    Hydraulics,
    RemovalEfficiencyMethod,
    InfrastructureTiming,
    DesalinationModel,
    SubsurfaceRisk,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import (
    PrintValues,
    OutputUnits,
    is_feasible,
    nostdout,
)
from pareto.strategic_water_management.stochastic_model_creation import StochasticPareto
from pareto.strategic_water_management.stochastic_results import (
    generate_stochastic_report,
)

from importlib import resources
from pareto.strategic_water_management.eev_tool import (
    compute_average_data,
    get_first_stage_solution,
)


### Step 1. Load expected-value data
with resources.path(
    "pareto.case_studies",
    "tssp_discap_sc1.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets_sc1, df_parameters_sc1] = get_data(fpath, model_type="strategic")

with resources.path(
    "pareto.case_studies",
    "tssp_discap_sc2.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets_sc2, df_parameters_sc2] = get_data(fpath, model_type="strategic")

with resources.path(
    "pareto.case_studies",
    "tssp_discap_sc3.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets_sc3, df_parameters_sc3] = get_data(fpath, model_type="strategic")

default_options = {
    "objective": Objectives.cost,
    "pipeline_cost": PipelineCost.distance_based,
    "pipeline_capacity": PipelineCapacity.input,
    "hydraulics": Hydraulics.false,
    "desalination_model": DesalinationModel.false,
    "node_capacity": True,
    "water_quality": WaterQuality.false,
    "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
    "infrastructure_timing": InfrastructureTiming.true,
    "subsurface_risk": SubsurfaceRisk.false,
}
scenario_data = {
    "sc1": {
        "df_sets": df_sets_sc1,
        "df_parameters": df_parameters_sc1,
        "default": default_options,
    },
    "sc2": {
        "df_sets": df_sets_sc2,
        "df_parameters": df_parameters_sc2,
        "default": default_options,
    },
    "sc3": {
        "df_sets": df_sets_sc3,
        "df_parameters": df_parameters_sc3,
        "default": default_options,
    },
}


probability_data = {"sc1": 1 / 3, "sc2": 1 / 3, "sc3": 1 / 3}

df_sets_ev, df_parameters_ev = compute_average_data(scenario_data, probability_data)


# ### Step 2. Solve the expected value (deterministic) problem
model_ev = create_model(
    df_sets_ev,
    df_parameters_ev,
    default=default_options,
)
options = {
    "deactivate_slacks": True,
    "scale_model": False,
    "scaling_factor": 1000,
    "running_time": 10000,
    "gap": 0.01,
}
print(
    "...........Solving the Deterministic model with expected parameter values..........."
)
results_ev = solve_model(model_ev, options=options)

# ### Step 3. Extract first-stage decisions
first_stage_vars = (
    "vb_y_Pipeline",
    "vb_y_Storage",
    "vb_y_Treatment",
    "vb_y_Disposal",
    "vb_y_BeneficialReuse",
)

first_stage_solution = get_first_stage_solution(model_ev, first_stage_vars)
print("First-stage solution extracted.")

### Step 4. Build stochastic model with first-stage decisions fixed fron EV solution

stochastic_model_ev = StochasticPareto(
    scenario_data,
    probability_data,
)

for s in stochastic_model_ev.set_scenarios:
    scn = stochastic_model_ev.scenario[s]
    for vname in first_stage_vars:
        var = getattr(scn, vname)

        for idx in var:
            var[idx].fix(first_stage_solution[vname][idx])

options = {
    "deactivate_slacks": False,
    "scale_model": False,
    "scaling_factor": 1000,
    "running_time": 100000,
    "gap": 0.01,
}

if not hasattr(stochastic_model_ev, "do_subsurface_risk_calcs"):
    stochastic_model_ev.do_subsurface_risk_calcs = False

### Step 5. Solve stochastic model with fixed first-stage decisions

print(
    "...........Solving stochastic model with fixed first-stage decisions values..........."
)
results_eev = solve_model(stochastic_model_ev, options=options)

# with nostdout():
#     feasibility_status = is_feasible(stochastic_model_ev)

# if not feasibility_status:
#     print("\nModel results are not feasible and should not be trusted\n" + "-" * 60)
# else:
#     print("\nModel results validated and found to pass feasibility tests\n" + "-" * 60)

# # Generate report with results in Excel
# print("\nConverting to Output Units and Displaying Solution\n" + "-" * 60)

# print("\nChecking feasibility status:", feasibility_status)
# print("Scenario set:", list(stochastic_model_ev.set_scenarios))

### Step 6. Computing EEV
EEV = sum(
    probability_data[s] * value(stochastic_model_ev.scenario[s].objective_Cost)
    for s in stochastic_model_ev.set_scenarios
)
EEV /= 1000
print(f"Expected EV (EEV) Cost: {EEV:.2f} MM USD")
