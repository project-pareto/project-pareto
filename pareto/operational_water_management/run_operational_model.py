##############################################################################
# 
##############################################################################
from pareto.operational_water_management.\
    operational_produced_water_optimization_model import (create_model,
                                                          print_results)
from pareto.utilities.get_data import get_data
from importlib import resources
from pyomo.environ import SolverFactory

# This emulates what the pyomo command-line tools does
# Tabs in the input Excel spreadsheet
set_list = ['ProductionPads', 'ProductionTanks', 'CompletionsPads',
            'SWDSites', 'FreshwaterSources', 'StorageSites',
            'TreatmentSites', 'ReuseOptions', 'NetworkNodes']
parameter_list = ['FCA', 'PCT', 'FCT', 'PKT', 'CKT', 'CCT',
                  'PAL', 'DriveTimes', 'CompletionsDemand',
                  'ProductionRates', 'PadRates', 'FlowbackRates',
                  'InitialDisposalCapacity',
                  'FreshwaterSourcingAvailability',
                  'CompletionsPadStorage',
                  'PadOffloadingCapacity', 'DriveTimes',
                  'DisposalOperationalCost', 'ReuseOperationalCost',
                  'TruckingHourlyCost', 'FreshSourcingCost',
                  'PipingOperationalCost']

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
fname = '..\\case_studies\\EXAMPLE_INPUT_DATA_FILE_generic_operational_model.xlsx'
[df_sets, df_parameters] = get_data(fname, set_list, parameter_list)

# create mathematical model
operational_model = create_model(df_sets, df_parameters)

# import pyomo solver
opt = SolverFactory("gurobi")
# solve mathematical model
results = opt.solve(operational_model, tee=True)
results.write()
print("\nDisplaying Solution\n" + '-'*60)
# pyomo_postprocess(None, model, results)
# print results
print_results(operational_model)
