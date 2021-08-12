##############################################################################
# 
##############################################################################
from pareto.strategic_water_management.\
    strategic_produced_water_optimization import (create_model,Objectives,
                                                          generate_report, PrintValues)
from pareto.utilities.get_data import get_data
from importlib import resources
from pyomo.environ import SolverFactory

import pandas as pd

# This emulates what the pyomo command-line tools does
# Tabs in the input Excel spreadsheet
set_list = ['ProductionPads', 'ProductionTanks','CompletionsPads',
			 'SWDSites','FreshwaterSources','StorageSites','TreatmentSites',
			 'ReuseOptions','NetworkNodes','PipelineDiameters','StorageCapacities'
			 ,'InjectionCapacities','TreatmentCapacities']
parameter_list = ['PNA','CNA','CCA','NNA','NCA','NKA','NRA','NSA','FCA','RCA','RNA',
			'SNA','PCT','PKT','FCT','CST','CCT','CKT','TruckingTime','CompletionsDemand',
			'PadRates','FlowbackRates','InitialPipelineCapacity','InitialDisposalCapacity',
			'InitialTreatmentCapacity','FreshwaterSourcingAvailability','PadOffloadingCapacity',
			'CompletionsPadStorage','DisposalOperationalCost','TreatmentOperationalCost',
			'ReuseOperationalCost','PipelineOperationalCost','FreshSourcingCost','TruckingHourlyCost',
			'PipelineCapacityIncrements','DisposalCapacityIncrements','InitialStorageCapacity',
			'StorageCapacityIncrements','TreatmentCapacityIncrements','TreatmentEfficiency',
			'DisposalExpansionCost','StorageExpansionCost','TreatmentExpansionCost','PipelineExpansionCost']

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
fname = 'C:\\Users\\drouvenm\\Desktop\\Temp\\PARETO-LOCAL\\Strategic-Case-Study\\input_data_generic_strategic_case_study_LAYFLAT_FULL.xlsx'
[df_sets, df_parameters] = get_data(fname, set_list, parameter_list)

# create mathematical model
strategic_model = create_model(df_sets, df_parameters, default={"objective": Objectives.cost})

# import pyomo solver
opt = SolverFactory("gurobi")
# opt.options['seconds'] = 60
opt.options['timeLimit'] = 60
opt.options['mipgap'] = 0
# solve mathematical model
results = opt.solve(strategic_model, tee=True)
results.write()
print("\nDisplaying Solution\n" + '-'*60)
[model, results_dict] = generate_report(strategic_model, is_print=[PrintValues.Detailed])
fname = 'C:\\Users\\drouvenm\\Desktop\\Temp\\PARETO-LOCAL\\Strategic-Case-Study\\strategic_optimization_results.xlsx'
with pd.ExcelWriter(fname) as writer:
        for i in results_dict:
                df = pd.DataFrame(results_dict[i][1:], columns = results_dict[i][0])
                df.to_excel(writer, sheet_name=i)