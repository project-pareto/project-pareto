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
from typing import Dict, Union, Any
import contextlib
import os
import io
import logging
import time
import pandas as pd # type: ignore

from pyomo.environ import Var # type: ignore
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    WaterQuality,
    BuildUnits,
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import is_feasible

# pylint: disable=invalid-name
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
# pylint: disable=logging-not-lazy
LOGGER = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def solve_case(input_file: str, model_options: Dict[str, Any],
               solver_options: Dict[str, Union[str, int, bool]],
               output_log: str, output_csv: str):
    '''
    Solve a test case with specific model options and solver options.
    Returns the output log and output csv of the results in the locations specified
    '''

    if os.path.exists(output_log):
        print("File :%s exists. Please specify different log file" % output_log)
        return

    if os.path.exists(output_csv):
        print("File :%s exists. Please specify different output file" % output_csv)
        return

    [sets, parameters] = get_data(input_file, set_list, parameter_list)
    strategic_model = create_model(sets, parameters, default=model_options)
    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            solve_model(model=strategic_model, options=solver_options)
            if is_feasible(strategic_model):
                print("Model solution is feasible!")
            else:
                print("Model solution does not pass feasibility checks :-(")
    with open(output_log, "a") as write_file:
        write_file.write("Passing stdout logs\n")
        write_file.write(stdout.getvalue())
        write_file.write("Passing stderr logs\n")
        write_file.write(stderr.getvalue())


    output = [(var, var.value) for var in strategic_model.component_data_objects(ctype=Var,
                                                                                 descend_into=True)]

    pd.DataFrame(output, columns=["Variable", "Value"]).to_csv(output_csv, index=False)
    return

def run_tests(test_dict: dict, results: Union[str, None] = None):
    '''
    Run multiple tests as specified by test dict
    '''
    # If a results folder is not specified create one
    if results is None:
        # Identify test based on when it was run
        results = time.asctime().replace(":", ".")
        if os.path.exists(results):
            print("Please provide a valid location to write result files")
            return

        os.mkdir(results)
    elif not os.path.exists(results):
        print("Please provide a valid location to write result files")
        return

    print("Writing result files in: %s" % results)
    log_file = os.path.join(results, "test_log.log")
    logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO,
                        format=FORMAT)

    for test, test_config in test_dict.items():
        LOGGER.info("Running test: %s" % test)
        test_file = test_config["TEST_FILE"]
        model_options = test_config["MODEL_OPTIONS"]
        solver_options = test_config["SOLVER_OPTIONS"]
        log_file = os.path.join(results, test + ".log")
        results_file = os.path.join(results, test + ".csv")
        solve_case(test_file, model_options, solver_options, log_file, results_file)
        LOGGER.info("Finished running test: %s" % test)
    return

if __name__ == "__main__":

    # Solve for the 5 test instances outlined by Melody

    # Base case
    MODEL_OPTIONS_BASE = {"objective": Objectives.cost,
                          "pipeline_cost": PipelineCost.distance_based,
                          "pipeline_capacity": PipelineCapacity.input,
                          "node_capacity": True,
                          "water_quality": WaterQuality.false,
                          "build_units": BuildUnits.scaled_units}

    #  Quality considerations for Test 2
    MODEL_OPTIONS_QUALITY = {"objective": Objectives.cost,
                             "pipeline_cost": PipelineCost.distance_based,
                             "pipeline_capacity": PipelineCapacity.input,
                             "node_capacity": True,
                             "water_quality": WaterQuality.post_process,
                             "build_units": BuildUnits.scaled_units}


    # Default solver options for all cases
    SOLVER_OPTIONS_BASE: Dict[str, Union[str, int, bool]] = {"deactivate_slacks": True,
                                                             "scale_model": False,
                                                             "scaling_factor": 1000,
                                                             "running_time": 60,
                                                             "gap": 0}
    # Base folder where all tests are located
    BASE_PATH = "/mnt/c/codes/project-pareto/pareto/case_studies/"
    TESTS = {"Run-1":
             {"TEST_FILE": os.path.join(BASE_PATH, "strategic_treatment_demo.xlsx"),
              "MODEL_OPTIONS": MODEL_OPTIONS_BASE,
              "SOLVER_OPTIONS": SOLVER_OPTIONS_BASE},
             "Run-2":
             {"TEST_FILE": os.path.join(BASE_PATH, "strategic_treatment_demo.xlsx"),
              "MODEL_OPTIONS": MODEL_OPTIONS_QUALITY,
              "SOLVER_OPTIONS": SOLVER_OPTIONS_BASE},
             "Run-3":
             {"TEST_FILE": os.path.join(BASE_PATH,
                                        "strategic_Feb_stakeholder_simplified_midland.xlsx"),
              "MODEL_OPTIONS": MODEL_OPTIONS_BASE,
              "SOLVER_OPTIONS": SOLVER_OPTIONS_BASE},
             "Run-4":
             {"TEST_FILE": os.path.join(BASE_PATH, "strategic_toy_case_study.xlsx"),
              "MODEL_OPTIONS": MODEL_OPTIONS_BASE,
              "SOLVER_OPTIONS": SOLVER_OPTIONS_BASE},
             "Run-5":
             {"TEST_FILE": os.path.join(BASE_PATH, "strategic_small_case_study.xlsx"),
              "MODEL_OPTIONS": MODEL_OPTIONS_BASE,
              "SOLVER_OPTIONS": SOLVER_OPTIONS_BASE}}

    run_tests(TESTS)
