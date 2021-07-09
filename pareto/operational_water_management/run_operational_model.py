from operational_produced_water_optimization_model import (create_model,
                                                           ProdTank, print_results)
from pareto.utilities.get_data import get_data
from importlib import resources
from pyomo.environ import SolverFactory

# Import data from case study
# read data from Excel Spreadsheet
set_list = ['ProductionPads', 'ProductionTanks', 'CompletionsPads',
            'SWDSites', 'FreshwaterSources', 'StorageSites',
            'TreatmentSites', 'ReuseOptions', 'NetworkNodes']
parameter_list = ['FCA', 'PCT', 'PKT', 'CKT', 'PAL', 'DriveTimes',
                  'CompletionsDemand', 'ProductionRates', 'PadRates',
                  'InitialDisposalCapacity', 'DriveTimes', 'FlowbackRates',
                  'CompletionsPadStorage']
    
with resources.path('pareto.case_studies',
                    "EXAMPLE_INPUT_DATA_FILE_generic_operational_model.xlsx") as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

# create mathematical model
operational_model = create_model(df_sets, df_parameters,
                                 default={"has_pipeline_constraints": True,
                                          "production_tanks": ProdTank.aggregated})
# import pyomo solver
opt = SolverFactory("gurobi_direct")
# solve mathematical model
results = opt.solve(operational_model, tee=True)
results.write()
print("\nDisplaying Solution\n" + '-'*60)
# pyomo_postprocess(None, model, results)
# print results
print_results(operational_model)
