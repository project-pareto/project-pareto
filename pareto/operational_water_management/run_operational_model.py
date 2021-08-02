##############################################################################
# 
##############################################################################
from pareto.operational_water_management.\
    operational_produced_water_optimization_model import (create_model,
                                                          ProdTank,
                                                          print_results)
from pareto.utilities.get_data import get_data
from importlib import resources
from pyomo.environ import SolverFactory

# This emulates what the pyomo command-line tools does
# Tabs in the input Excel spreadsheet
set_list = ['ProductionPads', 'CompletionsPads',
            'ProductionTanks', 'FreshwaterSources',
            'StorageSites', 'SWDSites', 'TreatmentSites',
            'ReuseOptions', 'NetworkNodes']
parameter_list = ['FCA', 'PCT', 'FCT', 'CCT', 'PKT', 'PRT', 'CKT', 'CRT',
                  'PAL', 'CompletionsDemand', 'PadRates', 'FlowbackRates',
                  'ProductionTankCapacity', 'InitialDisposalCapacity',
                  'CompletionsPadStorage','TreatmentCapacity',
                  'FreshwaterSourcingAvailability', 'PadOffloadingCapacity',
                  'DriveTimes', 'DisposalPipeCapEx', 'DisposalOperationalCost',
                  'TreatmentOperationalCost', 'ReuseOperationalCost',
                  'PipingOperationalCost', 'TruckingHourlyCost',
                  'FreshSourcingCost', 'ProductionRates'
                  ]

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
fname = '..\\case_studies\\EXAMPLE_INPUT_DATA_FILE_generic_operational_model.xlsx'
[df_sets, df_parameters] = get_data(fname, set_list, parameter_list)

# create mathematical model
operational_model = create_model(df_sets, df_parameters,
                                 default={"has_pipeline_constraints": True,
                                          "production_tanks": ProdTank.single})

# import pyomo solver
opt = SolverFactory("gurobi_direct")
# solve mathematical model
results = opt.solve(operational_model, tee=True)
results.write()
print("\nDisplaying Solution\n" + '-'*60)
# pyomo_postprocess(None, model, results)
# print results
print_results(operational_model)
