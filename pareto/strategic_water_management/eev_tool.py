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

import pyomo.environ as pyo
from pyomo.environ import Constraint, Var, Expression, units as pyunits, value
import re
import numbers
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


# Fix first-stage decision variables based on nominal results
def prob_weighted_average(obj_per_scenario, probabilities):
    """
    obj_per_scenario: dict {scenario -> object}
    probabilities: dict {scenario -> prob}
    """

    # Case 1: numeric leaf
    if all(isinstance(v, numbers.Number) for v in obj_per_scenario.values()):
        return sum(probabilities[s] * obj_per_scenario[s] for s in obj_per_scenario)

    # Case 2: dictionary → recurse keywise
    if all(isinstance(v, dict) for v in obj_per_scenario.values()):
        result = {}
        keys = obj_per_scenario[next(iter(obj_per_scenario))].keys()

        for k in keys:
            result[k] = prob_weighted_average(
                {s: obj_per_scenario[s][k] for s in obj_per_scenario}, probabilities
            )
        return result

    # Case 3: pandas DataFrame

    if all(isinstance(v, pd.DataFrame) for v in obj_per_scenario.values()):
        avg_df = None
        for s, df in obj_per_scenario.items():
            if avg_df is None:
                avg_df = probabilities[s] * df
            else:
                avg_df += probabilities[s] * df
        return avg_df

    # Case 4: anything else (strings, metadata, Units, etc.)
    # → copy from sc1
    return obj_per_scenario[next(iter(obj_per_scenario))]


def compute_average_data(scenario_data, probability_data):
    scenarios = scenario_data.keys()

    df_parameters_ev = {}

    for pname in scenario_data[next(iter(scenarios))]["df_parameters"]:
        obj_per_scenario = {
            s: scenario_data[s]["df_parameters"][pname]
            for s in scenarios
            if pname in scenario_data[s]["df_parameters"]
        }

        df_parameters_ev[pname] = prob_weighted_average(
            obj_per_scenario, probability_data
        )

    df_sets_ev = scenario_data[next(iter(scenarios))]["df_sets"]

    return df_sets_ev, df_parameters_ev


def get_first_stage_solution(model, var_names):
    first_stage_solution = {}

    for v in var_names:
        var = getattr(model, v)

        sol = {}
        for idx in var:
            sol[idx] = value(var[idx])
        first_stage_solution[v] = sol
    return first_stage_solution


# def fix_first_stage_vars(
#     model,
#     pipeline_df,
#     storage_df,
#     treatment_df,
#     disposal_df,
#     beneficialreuse_df,
#     tcapacity_df,
# ):
#     # 1. Pipelines
#     # First, fix all pipelines in the model to 0
#     for idx in model.vb_y_Pipeline:
#         model.vb_y_Pipeline[idx].fix(0)
#     # Then, for the ones listed in Excel, fix them to 1
#     for _, row in pipeline_df.iterrows():
#         origin = row["Origin"]
#         dest = row["Destination"]
#         diam = row["Pipeline Diameter"]
#         if (origin, dest, diam) in model.vb_y_Pipeline:
#             model.vb_y_Pipeline[origin, dest, diam].fix(row["Pipeline Installation"])

#     # 2. Storage Sites
#     # First, fix all storage sites in the model to 0
#     for idx in model.vb_y_Storage:
#         model.vb_y_Storage[idx].fix(0)
#     # Then, for the ones listed in Excel, fix them to 1
#     for _, row in storage_df.iterrows():
#         node = row["Storage Site"]
#         stype = row["Storage Capacity"]
#         if (node, stype) in model.vb_y_Storage:
#             model.vb_y_Storage[node, stype].fix(row["Storage Expansion"])

#     # 3. Treatment Sites
#     # First, fix all Treatment in the model to 0
#     for idx in model.vb_y_Treatment:
#         model.vb_y_Treatment[idx].fix(0)
#     # Then, for the ones listed in Excel, fix them to 1
#     for _, row in treatment_df.iterrows():
#         site = row["Treatment Site"]
#         technology = row["Treatment Technology"]
#         capacity = row["Treatment Capacity"]
#         if (site, technology, capacity) in model.vb_y_Treatment:
#             model.vb_y_Treatment[site, technology, capacity].fix(
#                 row["Treatment Expansion"]
#             )

#     # 4. Disposal Sites
#     # First, fix all Disposal in the model to 0
#     for idx in model.vb_y_Disposal:
#         model.vb_y_Disposal[idx].fix(0)
#     # Then, for the ones listed in Excel, fix them to 1
#     for _, row in disposal_df.iterrows():
#         site = row["Disposal Site"]
#         capacity = row["Injection Capacity"]
#         if (site, capacity) in model.vb_y_Disposal:
#             model.vb_y_Disposal[site, capacity].fix(row["Disposal"])


# # for _, row in disposal_df.iterrows():
# #     site = row["Disposal Site"]
# #     if any(i[0] == site for i in model.vb_y_Disposal):
# #         for idx in model.vb_y_Disposal:
# #             if idx[0] == site:
# #                 model.vb_y_Disposal[idx].fix(row["Disposal"])

# # # 5. Beneficial Reuse Sites
# # # First fix all treatment capacity in the model to 0
# # for idx in model.vb_y_BeneficialReuse:
# #     model.vb_y_BeneficialReuse[idx].fix(0)

# # # 6. Treatment Capacity
# # # First fix all treatment capacity in the model to 0
# # for idx in model.v_T_Capacity:
# #     model.v_T_Capacity[idx].fix(0)
# # #Then, for the ones listed in Excel, fix them to the value
# # for _, row in tcapacity_df.iterrows():
# #     site = row["Treatment Site"]
# #     if site in model.v_T_Capacity:
# #         model.v_T_Capacity[site].fix(row["Treatment Capacity [bbl/d]"])

# # # -- Load data for fixing first-stage variables --
# # fnominal = r"C:\Users\Soumya\OneDrive - KeyLogic\Desktop\strategic_DSc_2.xlsx"

# # pipeline_df = pd.read_excel(fnominal, sheet_name="vb_y_Pipeline", header=1)
# # storage_df = pd.read_excel(fnominal, sheet_name="vb_y_Storage", header=1)
# # treatment_df = pd.read_excel(fnominal, sheet_name="vb_y_Treatment", header=1)
# # disposal_df = pd.read_excel(fnominal, sheet_name="vb_y_Disposal", header=1)
# # beneficialreuse_df = pd.read_excel(
# #     fnominal, sheet_name="vb_y_BeneficialReuse", header=1
# # )
# # tcapacity_df = pd.read_excel(fnominal, sheet_name="v_T_Capacity", header=1)
