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
    WaterQuality,
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import generate_report, PrintValues, OutputUnits
from importlib import resources

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
    "TreatmentTechnologies",
]
parameter_list = [
    "Units",
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
    "RSA",
    "SCA",
    "SNA",
    "PCT",
    "PKT",
    "FCT",
    "CST",
    "CCT",
    "CKT",
    "CompletionsPadOutsideSystem",
    "DesalinationTechnologies",
    "DesalinationSites",
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
    "DisposalOperatingCapacity",
]

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
with resources.path(
    "pareto.case_studies",
    "input_data_generic_strategic_case_study_Treatment_Demo.xlsx",
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

# create mathematical model
"""Valid values of config arguments for the default parameter in the create_model() call
 objective: [Objectives.cost, Objectives.reuse]
 pipeline_cost: [PipelineCost.distance_based, PipelineCost.capacity_based]
 pipeline_capacity: [PipelineCapacity.input, PipelineCapacity.calculated]
 node_capacity: [True, False]
 water_quality: [WaterQuality.false, WaterQuality.post_process, WaterQuality.discrete]
 """

strategic_model = create_model(
    df_sets,
    df_parameters,
    default={
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": True,
        "water_quality": WaterQuality.false,
    },
)

# Note: if using the small_strategic_case_study and cbc, allow at least 5 minutes
options = {
    "deactivate_slacks": True,
    "scale_model": True,
    "scaling_factor": 1000,
    "running_time": 60,
    "gap": 0,
}

solve_model(model=strategic_model, options=options)

# Generate report with results in Excel
print("\nConverting to Output Units and Displaying Solution\n" + "-" * 60)
"""Valid values of parameters in the generate_report() call
 is_print: [PrintValues.detailed, PrintValues.nominal, PrintValues.essential]
 output_units: [OutputUnits.user_units, OutputUnits.unscaled_model_units]
 """
[model, results_dict] = generate_report(
    strategic_model,
    is_print=[PrintValues.essential],
    output_units=OutputUnits.user_units,
    fname="strategic_optimization_results.xlsx",
)

# This shows how to read data from PARETO reports
set_list = []
parameter_list = ["v_F_Trucked", "v_C_Trucked"]
fname = "strategic_optimization_results.xlsx"
[sets_reports, parameters_report] = get_data(fname, set_list, parameter_list)
