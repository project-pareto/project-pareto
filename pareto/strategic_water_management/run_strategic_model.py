##############################################################################
# 
##############################################################################
from pareto.strategic_water_management.\
    strategic_produced_water_optimization import (create_model,
                                                          print_results)
from pareto.utilities.get_data import get_data
from importlib import resources
from pyomo.environ import SolverFactory

# This emulates what the pyomo command-line tools does
# Tabs in the input Excel spreadsheet
set_list = ['ProductionPads', 'ProductionTanks','CompletionsPads',
        'SWDSites','FreshwaterSources','StorageSites','TreatmentSites',
        'ReuseOptions','NetworkNodes','PipelineDiameters','StorageCapacities',
        'InjectionCapacities']
parameter_list = ['PNA','CNA','CCA','NNA','NCA','NKA','NRA','FCA',
        'RNA','PCT','FCT','CST','CCT','TruckingTime','CompletionsDemand',
        'PadRates','FlowbackRates','InitialPipelineCapacity',
        'InitialDisposalCapacity','InitialTreatmentCapacity',
        'FreshwaterSourcingAvailability','PadOffloadingCapacity',
        'CompletionsPadStorage','DisposalOperationalCost','TreatmentOperationalCost',
        'ReuseOperationalCost','PipelineOperationalCost','FreshSourcingCost',
        'TruckingHourlyCost']

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
fname = '..\\case_studies\\EXAMPLE_INPUT_DATA_FILE_generic_strategic_model.xlsx'
[df_sets, df_parameters] = get_data(fname, set_list, parameter_list)

# create mathematical model
strategic_model = create_model(df_sets, df_parameters)

# import pyomo solver
opt = SolverFactory("gurobi")
# solve mathematical model
results = opt.solve(strategic_model, tee=True)
results.write()
print("\nDisplaying Solution\n" + '-'*60)
# pyomo_postprocess(None, model, results)
# print results
print_results(strategic_model)
