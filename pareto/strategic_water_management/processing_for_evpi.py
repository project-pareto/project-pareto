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
from importlib import resources


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

options = {
    "deactivate_slacks": True,
    "scale_model": False,
    "scaling_factor": 1000,
    "running_time": 10000,
    "gap": 0.01,
}

scenario_objectives = {}

for s, sc_data in scenario_data.items():
    model_ws = create_model(
        sc_data["df_sets"],
        sc_data["df_parameters"],
        default=sc_data.get("default", {}),
    )

    results_ws = solve_model(model_ws, options=options)

    scenario_objectives[s] = value(model_ws.objective_Cost)

E_WS = sum(probability_data[s] * scenario_objectives[s] for s in scenario_objectives)
E_WS /= 1000
print(f"Expected WS (k$): {E_WS:.3f} MM USD")
