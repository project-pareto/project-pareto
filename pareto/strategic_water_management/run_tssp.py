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
This code is developed to run the stochastic version of the strategic water management model in
PARETO. It builds three scenarios from separate case study Excel files, enforces non-anticipativity
on first-stage decisions across scenarios, and updates the objective function. It then solves the
expected-cost problem directly on the wrapper model and generates per-scenario Excel reports with
results.
"""

import pyomo.environ as pyo
from pyomo.environ import Constraint, Var, Expression, units as pyunits, value
import re

import pandas as pd
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    Objectives,
    PipelineCost,
    PipelineCapacity,
    Hydraulics,
    RemovalEfficiencyMethod,
    InfrastructureTiming,
    DesalinationModel,
    SubsurfaceRisk,
    WaterQuality,
    solve_model,
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

# ---- Load Data ---- #
with resources.path(
    "pareto.case_studies",
    "strategic_discap_sc1.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets_sc1, df_parameters_sc1] = get_data(fpath, model_type="strategic")

with resources.path(
    "pareto.case_studies",
    "strategic_discap_sc2.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets_sc2, df_parameters_sc2] = get_data(fpath, model_type="strategic")

with resources.path(
    "pareto.case_studies",
    "strategic_discap_sc3.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets_sc3, df_parameters_sc3] = get_data(fpath, model_type="strategic")


scenario_data = {
    "sc1": {
        "df_sets": df_sets_sc1,
        "df_parameters": df_parameters_sc1,
        "default": {
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
        },
    },
    "sc2": {
        "df_sets": df_sets_sc2,
        "df_parameters": df_parameters_sc2,
        "default": {
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
        },
    },
    "sc3": {
        "df_sets": df_sets_sc3,
        "df_parameters": df_parameters_sc3,
        "default": {
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
        },
    },
}

probability_data = {"sc1": 1 / 3, "sc2": 1 / 3, "sc3": 1 / 3}

stochastic_model = StochasticPareto(
    scenario_data,
    probability_data,
)

# ---- Solve the stochastic model ---- #
options = {
    "deactivate_slacks": False,
    "scale_model": False,
    "scaling_factor": 1000,
    "running_time": 100000,
    "gap": 0.01,
}

if not hasattr(stochastic_model, "do_subsurface_risk_calcs"):
    stochastic_model.do_subsurface_risk_calcs = False

results = solve_model(stochastic_model, options=options)

with nostdout():
    feasibility_status = is_feasible(stochastic_model)

if not feasibility_status:
    print("\nModel results are not feasible and should not be trusted\n" + "-" * 60)
else:
    print("\nModel results validated and found to pass feasibility tests\n" + "-" * 60)

# Generate report with results in Excel
print("\nConverting to Output Units and Displaying Solution\n" + "-" * 60)

print("\nChecking feasibility status:", feasibility_status)
print("Scenario set:", list(stochastic_model.set_scenarios))
print("Proceeding to report generation...\n")


"""Valid values of parameters in the generate_report() call
 is_print: [PrintValues.detailed, PrintValues.nominal, PrintValues.essential]
 output_units: [OutputUnits.user_units, OutputUnits.unscaled_model_units]
 """


for s in stochastic_model.set_scenarios:
    scn = stochastic_model.scenario[s]

    results_dict = generate_stochastic_report(
        model=scn,  # same block but with solved values
        fname=f"strategic_optimization_results_{s}.xlsx",
        is_print=PrintValues.nominal,
    )
Obj = sum(
    probability_data[s] * value(stochastic_model.scenario[s].objective_Cost)
    for s in stochastic_model.set_scenarios
)
Obj /= 1000
print(f"Objective Value from stochastic solution: {Obj:.2f} MM USD")
print("Done")
