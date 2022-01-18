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
from os import strerror
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    create_model,
    Objectives,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import generate_report, PrintValues
from importlib import resources
from pareto.utilities.solvers import get_solver, set_timeout

import pandas as pd

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
    "PipelineExpansionCost",
    "PipelineExpansionDistance",
    "Hydraulics",
    "Economics",
]

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
with resources.path(
    "pareto.case_studies",
    "input_data_generic_strategic_case_study_LAYFLAT_FULL.xlsx"
    # "pareto.case_studies", "small_strategic_case_study.xlsx"
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

# create mathematical model
strategic_model = create_model(
    df_sets, df_parameters, default={"objective": Objectives.cost}
)

# initialize pyomo solver
opt = get_solver("gurobi_direct", "gurobi", "cbc")
# Note: if using the small_strategic_case_study and cbc, allow at least 5 minutes
set_timeout(opt, timeout_s=60)
opt.options["mipgap"] = 0

# solve mathematical model
results = opt.solve(strategic_model, tee=True)
results.write()
print("\nDisplaying Solution\n" + "-" * 60)
[model, results_dict] = generate_report(
    strategic_model,
    is_print=[PrintValues.Essential],
    fname="strategic_optimization_results.xlsx",
)

# This shows how to read data from PARETO reports
set_list = []
parameter_list = ["v_F_Trucked", "v_C_Trucked"]
fname = "strategic_optimization_results.xlsx"
[sets_reports, parameters_report] = get_data(fname, set_list, parameter_list)
