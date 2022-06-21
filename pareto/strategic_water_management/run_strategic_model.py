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

from pareto.strategic_water_management.strategic_produced_water_optimization import (
    Objectives,
    PipelineCost,
    PipelineCapacity,
    IncludeNodeCapacity,
)
from pareto.utilities.results import PrintValues
from pareto.utilities.solve_scenarios import solve_scenarios

# This emulates what the pyomo command-line tools does
# Tabs in the input Excel spreadsheet
set_list = [
    "ProductionPads",
    "ProductionTanks",
    "CompletionsPads",
    "SWDSites",
    "FreshwaterSources",
    "StorageSites",
    "TreatmentSites",
    "ReuseOptions",
    "NetworkNodes",
    "PipelineDiameters",
    "StorageCapacities",
    "InjectionCapacities",
    "TreatmentCapacities",
]
parameter_list = [
    "PNA",
    "CNA",
    "CCA",
    "NNA",
    "NCA",
    "NKA",
    "NRA",
    "NSA",
    "FCA",
    "RCA",
    "RNA",
    "SNA",
    "PCT",
    "PKT",
    "FCT",
    "CST",
    "CCT",
    "CKT",
    "TruckingTime",
    "CompletionsDemand",
    "PadRates",
    "FlowbackRates",
    "NodeCapacities",
    "InitialPipelineCapacity",
    "InitialDisposalCapacity",
    "InitialTreatmentCapacity",
    "FreshwaterSourcingAvailability",
    "PadOffloadingCapacity",
    "CompletionsPadStorage",
    "DisposalOperationalCost",
    "TreatmentOperationalCost",
    "ReuseOperationalCost",
    "PipelineOperationalCost",
    "FreshSourcingCost",
    "TruckingHourlyCost",
    "PipelineDiameterValues",
    "DisposalCapacityIncrements",
    "InitialStorageCapacity",
    "StorageCapacityIncrements",
    "TreatmentCapacityIncrements",
    "TreatmentEfficiency",
    "DisposalExpansionCost",
    "StorageExpansionCost",
    "TreatmentExpansionCost",
    "PipelineCapexDistanceBased",
    "PipelineCapexCapacityBased",
    "PipelineCapacityIncrements",
    "PipelineExpansionDistance",
    "Hydraulics",
    "Economics",
    "PadWaterQuality",
    "StorageInitialWaterQuality",
    "PadStorageInitialWaterQuality",
]


### Input Settings
""" Please enter the path to folder in which the different input files reside
    for example: 'C:\\user\\Documents\\myfile.xlsx'
    note the double backslashes '\\' in that path reference
    input_files should contain all files to be read. Each file will be a 
    different scenario and create a separate output file"""
input_folder = "pareto.case_studies"
input_files = [
    "input_data_generic_strategic_case_study_LAYFLAT_FULL.xlsx",
    "small_strategic_case_study.xlsx",
]

### Scenario Settings
""" Please provide a scenario name per input file"""
scenario_names = [
    "scenario_1",
    "scenario_2",
]


### Optimization Settings
"""Valid values of model creation config arguments for the default parameter 
    in the create_model() call.
    objective: [Objectives.cost, Objectives.reuse]
    pipeline_cost: [PipelineCost.distance_based, PipelineCost.capacity_based]
    pipeline_capacity: [PipelineCapacity.input, PipelineCapacity.calculated]
    node_capacity: [IncludeNodeCapacity.True, IncludeNodeCapacity.False]"""
model_options = {
    "s1": {
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": IncludeNodeCapacity.true,
    },
    "s2": {
        "objective": Objectives.reuse,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": IncludeNodeCapacity.true,
    },
}


# General optimization settings
"""Valid values of optimization config arguments for the default parameter 
    in the solve_model() call.
    deactivate_slacks: [True, False]
    scale_model: [True, False]
    scaling_factor: nonnegative integer
    running_time: nonnegative integer. Running time in seconds.
    gap: nonnegative double
    water_quality: [True, False]
    """
opt_options = {
    "deactivate_slacks": True,
    "scale_model": True,
    "scaling_factor": 1000000,
    "running_time": 60,  # in seconds
    "gap": 0,
    "water_quality": True,
}

### Output Settings
"""Please add name of scenario overview file. The main KPIs per scenario will 
    be exported to this file."""
scenario_overview_name = "PARETO_Scenario_Overview.xlsx"


### Create and solve optimization model, print results
solve_scenarios(
    set_list,
    parameter_list,
    input_folder,
    input_files,
    scenario_names,
    model_options,
    opt_options,
    scenario_overview_name,
)
