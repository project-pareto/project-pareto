##############################################################################
# 
##############################################################################
from pareto.strategic_water_management.\
    strategic_produced_water_optimization import (create_model,Objectives,
                                                          generate_report, PrintValues)
from pareto.utilities.get_data import get_data
from importlib import resources
from pyomo.environ import SolverFactory
from pyomo.environ import (Var, Param, Set, ConcreteModel, Constraint)

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
fname = 'case_studies\\input_data_generic_strategic_case_study_LAYFLAT_FULL.xlsx'
[df_sets, df_parameters] = get_data(fname, set_list, parameter_list)

model = ConcreteModel()

## Definition of sets ##
model.s_T  = Set(initialize=df_sets['TimePeriods'], doc='Time Periods', ordered=True)
model.s_PP = Set(initialize=df_sets['ProductionPads'], doc='Production Pads')
model.s_CP = Set(initialize=df_sets['CompletionsPads'], doc='Completions Pads')
model.s_P  = Set(initialize=(model.s_PP | model.s_CP), doc='Pads')
model.s_F  = Set(initialize=df_sets['FreshwaterSources'], doc='Freshwater Sources')
model.s_K  = Set(initialize=df_sets['SWDSites'], doc='Disposal Sites')
model.s_S  = Set(initialize=df_sets['StorageSites'], doc='Storage Sites')
model.s_R  = Set(initialize=df_sets['TreatmentSites'], doc='Treatment Sites')
model.s_O  = Set(initialize=df_sets['ReuseOptions'], doc='Reuse Options')
model.s_N  = Set(initialize=df_sets['NetworkNodes'], doc=['Network Nodes'])
model.s_L  = Set(initialize=(model.s_P | model.s_F | model.s_K | model.s_S | model.s_R | model.s_O | model.s_N), doc='Locations')
model.s_D  = Set(initialize=df_sets['PipelineDiameters'], doc='Pipeline diameters')
model.s_C  = Set(initialize=df_sets['StorageCapacities'], doc='Storage capacities')
model.s_J  = Set(initialize=df_sets['TreatmentCapacities'], doc='Treatment capacities')
model.s_I  = Set(initialize=df_sets['InjectionCapacities'], doc='Injection (i.e. disposal) capacities')

# Definition of parameters
model.p_gamma_Completions  = Param(model.s_P,model.s_T,default=0,
							initialize=df_parameters['CompletionsDemand'], 
							doc='Completions water demand [bbl/week]')
model.p_gamma_TotalDemand  = Param(default=0,
							initialize=sum(sum(model.p_gamma_Completions[p,t] for p in model.s_P) for t in model.s_T),
							doc='Total water demand over the planning horizon [bbl]', mutable=True)
model.p_beta_Production    = Param(model.s_P,model.s_T,default=0, 
							initialize=df_parameters['PadRates'],
							doc='Produced water supply forecast [bbl/week]')                            
model.p_beta_Flowback      = Param(model.s_P,model.s_T,default=0,
							initialize=df_parameters['FlowbackRates'],
							doc='Flowback supply forecast for a completions bad [bbl/week]')
model.p_beta_TotalProd     = Param(default=0,
							initialize=sum(sum(model.p_beta_Production[p,t] + model.p_beta_Flowback[p,t] for p in model.s_P) for t in model.s_T),
							doc='Combined water supply forecast (flowback & production) over the planning horizon [bbl]', mutable=True)
model.p_sigma_Pipeline     = Param(model.s_L,model.s_L,default=0,
							initialize=df_parameters['InitialPipelineCapacity'],
							doc='Initial weekly pipeline capacity between two locations [bbl/week]')                        
model.p_sigma_Disposal     = Param(model.s_K,default=0,
							initialize=df_parameters['InitialDisposalCapacity'],
							doc='Initial weekly disposal capacity at disposal sites [bbl/week]')
model.p_sigma_Storage      = Param(model.s_S,default=0,
							initialize=df_parameters['InitialStorageCapacity'],
							doc='Initial storage capacity at storage site [bbl]')
model.p_sigma_PadStorage   = Param(model.s_CP,default=0,
							initialize=df_parameters['CompletionsPadStorage'],
							doc='Storage capacity at completions site [bbl]')                    
model.p_sigma_Treatment    = Param(model.s_R,default=0,
							initialize=df_parameters['InitialTreatmentCapacity'],
							doc='Initial weekly treatment capacity at treatment site [bbl/week]') 

# create mathematical model
strategic_model = create_model(model, df_sets, df_parameters, default={"objective": Objectives.cost})

# import pyomo solver
opt = SolverFactory("cbc")
opt.options['seconds'] = 60
# opt.options['timeLimit'] = 60
opt.options['mipgap'] = 0
# solve mathematical model
results = opt.solve(strategic_model, tee=True)
results.write()
print("\nDisplaying Solution\n" + '-'*60)
[model, results_dict] = generate_report(strategic_model, is_print=[PrintValues.Detailed])
fname = 'strategic_optimization_results.xlsx'
with pd.ExcelWriter(fname) as writer:
        for i in results_dict:
                df = pd.DataFrame(results_dict[i][1:], columns = results_dict[i][0])
                df.to_excel(writer, sheet_name=i)