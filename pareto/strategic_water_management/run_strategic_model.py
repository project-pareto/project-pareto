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
    Hydraulics,
    RemovalEfficiencyMethod,
    InfrastructureTiming,
    DesalinationModel,
    SubsurfaceRisk,
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
import pyomo.environ as pyo


# This emulates what the pyomo command-line tools does
# Tabs in the input Excel spreadsheet
set_list = [
    "ProductionPads",
    "CompletionsPads",
    "SWDSites",
    "ExternalWaterSources",
    "WaterQualityComponents",
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
    "ROA",
    "RKA",
    "SOA",
    "NOA",
    "PCT",
    "PKT",
    "FCT",
    "CST",
    "CCT",
    "CKT",
    "RST",
    "ROT",
    "SOT",
    "RKT",
    "Elevation",
    "CompletionsPadOutsideSystem",
    "DesalinationTechnologies",
    "DesalinationSites",
    "BeneficialReuseCost",
    "BeneficialReuseCredit",
    "TruckingTime",
    "CompletionsDemand",
    "PadRates",
    "FlowbackRates",
    "WellPressure",
    "NodeCapacities",
    "InitialPipelineCapacity",
    "InitialPipelineDiameters",
    "InitialDisposalCapacity",
    "InitialTreatmentCapacity",
    "ReuseMinimum",
    "ReuseCapacity",
    "ExtWaterSourcingAvailability",
    "PadOffloadingCapacity",
    "CompletionsPadStorage",
    "DisposalOperationalCost",
    "TreatmentOperationalCost",
    "ReuseOperationalCost",
    "PipelineOperationalCost",
    "ExternalSourcingCost",
    "TruckingHourlyCost",
    "PipelineDiameterValues",
    "DisposalCapacityIncrements",
    "InitialStorageCapacity",
    "StorageCapacityIncrements",
    "TreatmentCapacityIncrements",
    "TreatmentEfficiency",
    "RemovalEfficiency",
    "DisposalExpansionCost",
    "StorageExpansionCost",
    "TreatmentExpansionCost",
    "PipelineCapexDistanceBased",
    "PipelineCapexCapacityBased",
    "PipelineCapacityIncrements",
    "PipelineExpansionDistance",
    "Hydraulics",
    "Economics",
    "DesalinationSurrogate",
    "ExternalWaterQuality",
    "PadWaterQuality",
    "StorageInitialWaterQuality",
    "PadStorageInitialWaterQuality",
    "DisposalOperatingCapacity",
    "TreatmentExpansionLeadTime",
    "DisposalExpansionLeadTime",
    "StorageExpansionLeadTime",
    "PipelineExpansionLeadTime_Dist",
    "PipelineExpansionLeadTime_Capac",
    "SWDDeep",
    "SWDAveragePressure",
    "SWDProxPAWell",
    "SWDProxInactiveWell",
    "SWDProxEQ",
    "SWDProxFault",
    "SWDProxHpOrLpWell",
    "SWDRiskFactors",
]

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
"""By default, PARETO comes with the following 6 strategic case studies:
strategic_treatment_demo.xlsx
strategic_permian_demo.xlsx
strategic_small_case_study.xlsx
strategic_toy_case_study.xlsx
workshop_baseline_all_data.xlsx
strategic_treatment_demo_surrogates.xlsx
"""
with resources.path(
    "pareto.case_studies",
    "strategic_toy_case_study.xlsx"
    # "strategic_treatment_demo_modified.xlsx",
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

# create mathematical model
"""Valid values of config arguments for the default parameter in the create_model() call
 objective: [Objectives.cost, Objectives.reuse, Objectives.subsurface_risk]
 pipeline_cost: [PipelineCost.distance_based, PipelineCost.capacity_based]
 pipeline_capacity: [PipelineCapacity.input, PipelineCapacity.calculated]
 hydraulics: [Hydraulics.false, Hydraulics.post_process, Hydraulics.co_optimize, Hydraulics.co_optimize_linearized]
 desalination_model: [DesalinationModel.false, DesalinationModel.mvc, DesalinationModel.md]
 node_capacity: [True, False]
 water_quality: [WaterQuality.false, WaterQuality.post_process, WaterQuality.discrete]
 removal_efficiency_method: [RemovalEfficiencyMethod.concentration_based, RemovalEfficiencyMethod.load_based]
 infrastructure_timing: [InfrastructureTiming.false, InfrastructureTiming.true]
 subsurface_risk: [SubsurfaceRisk.false, SubsurfaceRisk.exclude_over_and_under_pressured_wells, SubsurfaceRisk.calculate_risk_metrics]
 """

strategic_model = create_model(
    df_sets,
    df_parameters,
    default={
        "objective": Objectives.cost_surrogate,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "hydraulics": Hydraulics.false,
        "desalination_model": DesalinationModel.false,
        "node_capacity": True,
        "water_quality": WaterQuality.false,
        "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
        "infrastructure_timing": InfrastructureTiming.true,
        "subsurface_risk": SubsurfaceRisk.exclude_over_and_under_pressured_wells,
    },
)

options = {
    "deactivate_slacks": True,
    "scale_model": False,
    "scaling_factor": 1000,
    "running_time": 10000,
    "gap": 100,
}

results = solve_model(model=strategic_model, options=options)

with nostdout():
    feasibility_status = is_feasible(strategic_model)

if not feasibility_status:
    print("\nModel results are not feasible and should not be trusted\n" + "-" * 60)
else:
    print("\nModel results validated and found to pass feasibility tests\n" + "-" * 60)

# Generate report with results in Excel
print("\nConverting to Output Units and Displaying Solution\n" + "-" * 60)
"""Valid values of parameters in the generate_report() call
 is_print: [PrintValues.detailed, PrintValues.nominal, PrintValues.essential]
 output_units: [OutputUnits.user_units, OutputUnits.unscaled_model_units]
 """
[model, results_dict] = generate_report(
    strategic_model,
    results_obj=results,
    is_print=PrintValues.essential,
    output_units=OutputUnits.user_units,
    fname="MD_surrogate_UB_100.xlsx",
)

# This shows how to read data from PARETO reports
set_list = []
parameter_list = ["v_F_Trucked", "v_C_Trucked"]
fname = "MD_surrogate_UB_100.xlsx"
[sets_reports, parameters_report] = get_data(fname, set_list, parameter_list)
