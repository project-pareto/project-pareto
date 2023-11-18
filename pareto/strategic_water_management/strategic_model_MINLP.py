#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2023 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################

from pareto.strategic_water_management.strategic_produced_water_optimization_minlp import (
    WaterQuality,
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
    Hydraulics,
    RemovalEfficiencyMethod,
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
from pyomo.environ import Constraint, value, units

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from ipywidgets import FloatText, Button, Layout, GridspecLayout, ToggleButtons
from IPython.display import display

from os import remove

# from tabulate import tabulate

# Each entry in set_list corresponds to a tab in the Excel input file that
# defines an index set.
set_list = [
    "ProductionPads", "CompletionsPads", "SWDSites", "FreshwaterSources", "StorageSites",
    "TreatmentSites", "ReuseOptions", "NetworkNodes", "PipelineDiameters", "StorageCapacities",
    "InjectionCapacities", "TreatmentCapacities", "TreatmentTechnologies",
]
# Each entry in parameter_list also corresponds to a tab in the Excel input
# file, but these tabs have parameter data.
parameter_list = [
    "Units", "PNA", "CNA", "CCA", "NNA", "NCA", "NKA", "NRA", "NSA", "FCA", "RCA", "RNA",
    "RSA", "SCA", "SNA", "PCT", "PKT", "FCT", "CST", "CCT", "CKT", "CompletionsPadOutsideSystem",
    "DesalinationTechnologies", "DesalinationSites", "TruckingTime", "CompletionsDemand",
    "PadRates", "FlowbackRates", "NodeCapacities", "InitialPipelineCapacity",
    "InitialDisposalCapacity", "InitialTreatmentCapacity", "FreshwaterSourcingAvailability",
    "PadOffloadingCapacity", "CompletionsPadStorage", "DisposalOperationalCost",
    "TreatmentOperationalCost", "ReuseOperationalCost", "PipelineOperationalCost",
    "FreshSourcingCost", "TruckingHourlyCost", "PipelineDiameterValues",
    "DisposalCapacityIncrements", "InitialStorageCapacity", "StorageCapacityIncrements",
    "TreatmentCapacityIncrements", "TreatmentEfficiency", "RemovalEfficiency",
    "DisposalExpansionCost", "StorageExpansionCost", "TreatmentExpansionCost",
    "PipelineCapexDistanceBased", "PipelineCapexCapacityBased", "PipelineCapacityIncrements",
    "PipelineExpansionDistance", "Hydraulics", "Economics", "PadWaterQuality",
    "StorageInitialWaterQuality", "PadStorageInitialWaterQuality", "DisposalOperatingCapacity",
]

# Load data from Excel input file into Python
with resources.path(
    "pareto.case_studies",
    "strategic_treatment_demo_modified.xlsx",
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

# Create Pyomo optimization model representing the produced water network
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
    "gurobi_numeric_focus": 2,
}
results_obj = solve_model(model=strategic_model, options=options)

# Check feasibility of the solved model
def check_feasibility(model):
    with nostdout():
        feasibility_status = is_feasible(model)
    if not feasibility_status:
        print("Model results are not feasible and should not be trusted")
    else:
        print("Model results validated and found to pass feasibility tests")

check_feasibility(strategic_model)

[model, results_dict] = generate_report(
    strategic_model,
    # is_print=[PrintValues.essential],
    output_units=OutputUnits.user_units,
    fname="strategic_optimization_small_case_results_SRA_post_process.xlsx",
)