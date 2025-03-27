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
from pareto.utilities.visualize import plot_network
from importlib import resources


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
    "strategic_toy_case_study.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets, df_parameters] = get_data(fpath, model_type="strategic")

# create mathematical model
"""Valid values of config arguments for the default parameter in the create_model() call
 objective: [Objectives.cost, Objectives.reuse, Objectives.subsurface_risk, Objectives.cost_surrogate, Objectives.environmental]
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
)

options = {
    "deactivate_slacks": True,
    "scale_model": False,
    "scaling_factor": 1000,
    "running_time": 200,
    "gap": 0,
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
    fname="strategic_optimization_results.xlsx",
)

# Positions for the toy case study
pos = {
    "PP01": (20, 20),
    "PP02": (45, 20),
    "PP03": (50, 50),
    "PP04": (80, 40),
    "CP01": (65, 20),
    "F01": (75, 15),
    "F02": (75, 25),
    "K01": (30, 10),
    "K02": (40, 50),
    "S02": (60, 50),
    "S03": (10, 44),
    "S04": (10, 36),
    "R01": (20, 40),
    "R02": (70, 50),
    "O01": (1, 55),
    "O02": (1, 40),
    "O03": (1, 25),
    "N01": (30, 20),
    "N02": (30, 30),
    "N03": (30, 40),
    "N04": (40, 40),
    "N05": (45, 30),
    "N06": (50, 40),
    "N07": (60, 40),
    "N08": (60, 30),
    "N09": (70, 40),
}

# Network visualization feature
plot_network(
    strategic_model,
    show_piping=True,
    show_trucking=True,
    show_results=False,
    save_fig="network.png",
    pos=pos,
)
