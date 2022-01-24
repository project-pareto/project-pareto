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
from pareto.operational_water_management.operational_produced_water_optimization_model import (
    create_model,
    ProdTank,
    postprocess_water_quality_calculation,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import generate_report, PrintValues
from pareto.utilities.solvers import get_solver, set_timeout
from importlib import resources

import pandas as pd

# This emulates what the pyomo command-line tools does
# Tabs in the input Excel spreadsheet
set_list = [
    "ProductionPads",
    "CompletionsPads",
    "ProductionTanks",
    "FreshwaterSources",
    "StorageSites",
    "SWDSites",
    "TreatmentSites",
    "ReuseOptions",
    "NetworkNodes",
]
parameter_list = [
    "RCA",
    "FCA",
    "PCT",
    "FCT",
    "CCT",
    "PKT",
    "PRT",
    "CKT",
    "CRT",
    "PAL",
    "CompletionsDemand",
    "PadRates",
    "FlowbackRates",
    "ProductionTankCapacity",
    "InitialDisposalCapacity",
    "CompletionsPadStorage",
    "TreatmentCapacity",
    "FreshwaterSourcingAvailability",
    "PadOffloadingCapacity",
    "DriveTimes",
    "DisposalPipeCapEx",
    "DisposalOperationalCost",
    "TreatmentOperationalCost",
    "ReuseOperationalCost",
    "PadStorageCost",
    "PipingOperationalCost",
    "TruckingHourlyCost",
    "FreshSourcingCost",
    "ProductionRates",
    "TreatmentEfficiency",
    "PadWaterQuality",
    "StorageInitialWaterQuality",
]

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference

with resources.path(
    "pareto.case_studies", "EXAMPLE_INPUT_DATA_FILE_generic_operational_model.xlsx"
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

df_parameters["MinTruckFlow"] = 75
df_parameters["MaxTruckFlow"] = 37000
# create mathematical model
operational_model = create_model(
    df_sets,
    df_parameters,
    default={"has_pipeline_constraints": True, "production_tanks": ProdTank.equalized},
)

# initialize pyomo solver
opt = get_solver("gurobi_direct", "gurobi", "cbc")
set_timeout(opt, timeout_s=60)

# solve mathematical model
results = opt.solve(operational_model, tee=True)
results.write()

operational_model = postprocess_water_quality_calculation(
    operational_model, df_sets, df_parameters, opt
)

# pyomo_postprocess(None, model, results)
# set is_print=[PrintValues.Nominal] in generate_report() below to print results
[model, results_dict] = generate_report(
    operational_model,
    is_print=[],
    fname="PARETO_report.xlsx",
)

# This shows how to read data from PARETO reports
set_list = []
parameter_list = ["v_F_Trucked", "v_C_Trucked"]
fname = "PARETO_report.xlsx"
[sets_reports, parameters_report] = get_data(fname, set_list, parameter_list)
