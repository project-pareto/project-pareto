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

from telnetlib import theNULL
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
    IncludeNodeCapacity,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import generate_report, PrintValues
from importlib import resources

# set default values for model and opt options
default_model_options = {
    "objective": Objectives.cost,
    "pipeline_cost": PipelineCost.distance_based,
    "pipeline_capacity": PipelineCapacity.input,
    "node_capacity": IncludeNodeCapacity.true,
}

default_opt_options = {
    "deactivate_slacks": True,
    "scale_model": True,
    "scaling_factor": 1000000,
    "running_time": 60,  # in seconds
    "gap": 0,
    "water_quality": True,
}


def solve_scenarios(
    set_list,
    parameter_list,
    input_folder,
    input_files,
    model_options_input,
    opt_options_input,
):

    # Determine if model_options are entered per scenario
    bool_model_options = any(isinstance(i, dict) for i in model_options_input.values())
    bool_opt_options = any(isinstance(i, dict) for i in opt_options_input.values())

    # TODO: check - this is a working option, not sure if only way to check if it
    # is a nested dictionary

    count = 0

    for file in input_files:
        # run optimization for all files in input file

        df_sets = []
        df_parameters = []

        with resources.path(
            str(input_folder),
            str(file),
        ) as fpath:
            [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

        # set model options
        if bool_model_options:
            model_options = list(model_options_input.values())[count]
        else:
            model_options = model_options_input

        # set optimization options
        if bool_opt_options:
            opt_options = list(opt_options_input.values())[count]
        else:
            opt_options = opt_options_input

        # create mathematical model
        """Valid values of config arguments for the default parameter in the create_model() call
        objective: [Objectives.cost, Objectives.reuse]
        pipeline_cost: [PipelineCost.distance_based, PipelineCost.capacity_based]
        pipeline_capacity: [PipelineCapacity.input, PipelineCapacity.calculated]
        node_capacity: [IncludeNodeCapacity.True, IncludeNodeCapacity.False]"""
        # TODO: make name dynamic
        strategic_model = create_model(
            df_sets,
            df_parameters,
            default=model_options,
        )

        solve_model(model=strategic_model, options=opt_options)

        # Define name of resultfile. Note that file already contains suffix ".xlsx"
        result_file = "strategic_opt_results_" + str(file)

        # Generate report with results in Excel
        print("\nDisplaying Solution - " + str(file) + "\n" + "-" * 60)
        [model, results_dict] = generate_report(
            strategic_model,
            is_print=[PrintValues.Essential],
            fname=result_file,
        )

        # This shows how to read data from PARETO reports
        set_list_report = []
        parameter_list_report = ["v_F_Trucked", "v_C_Trucked"]
        [sets_reports, parameters_report] = get_data(
            result_file, set_list_report, parameter_list_report
        )

        # update loop counter
        count += 1
