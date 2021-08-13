##############################################################################
# 
##############################################################################
"""


Authors: PARETO Team 
"""

from pyomo.environ import Var
import pandas as pd
from enum import Enum

class PrintValues(Enum):
    Detailed = 0  
    Nominal = 1  
    Essential = 2 

def generate_report(model, is_print=[]):
    # ## Printing model sets, parameters, constraints, variable values ##
    
    printing_list = []
    if model.type == 'strategic':
        # Detailed: Slacks values included, Same as "All"
        if PrintValues.Detailed in is_print:
            printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_F_PadStorageIn', 
                        'v_F_PadStorageOut','v_C_Piped','v_C_Trucked','v_C_Sourced','v_C_Disposal',
                        'v_C_Reuse','v_L_Storage','vb_y_Pipeline','vb_y_Disposal','vb_y_Storage',
                        'vb_y_FLow','v_F_Overview']
        
        # Nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage
        if PrintValues.Nominal in is_print:
            printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_C_Piped','v_C_Trucked',
                        'v_C_Sourced','vb_y_Pipeline','vb_y_Disposal','vb_y_Storage','vb_y_Flow','v_F_Overview']

        # Essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
        if PrintValues.Essential in is_print:
            printing_list = ['v_F_Overview'] 

        headers = {'v_F_Piped_dict':[('Origin', 'destination', 'Time', 'Piped water')],'v_C_Piped_dict':[('Origin', 'Destination', 'Time', 'Cost piping')],
                'v_F_Trucked_dict':[('Origin', 'Destination', 'Time', 'Trucked water')],'v_C_Trucked_dict':[('Origin', 'Destination', 'Time', 'Cost trucking')],
                'v_F_Sourced_dict':[('Fresh water source', 'Completion pad', 'Time', 'Sourced water')],'v_C_Sourced_dict':[('Fresh water source', 'Completion pad', 'Time', 'Cost sourced water')],
                'v_F_PadStorageIn_dict':[('Completion pad', 'Time', 'StorageIn')],'v_F_PadStorageOut_dict':[('Completion pad', 'Time', 'StorageOut')],
                'v_C_Disposal_dict':[('Disposal site', 'Time', 'Cost of disposal')],'v_C_Treatment_dict':[('Treatment site', 'Time', 'Cost of Treatment')],
                'v_C_Reuse_dict':[('Completion pad', 'Time', 'Cost of reuse')],'v_C_Storage_dict':[('Storage Site', 'Time', 'Cost of Storage')],
                'v_R_Storage_dict':[('Storage Site', 'Time', 'Credit of Retrieving Produced Water')],'v_L_Storage_dict':[('Storage site', 'Time', 'Storage Levels')],
                'v_L_PadStorage_dict':[('Completion pad', 'Time', 'Storage Levels')],'vb_y_Pipeline_dict':[('Origin', 'Destination', 'Pipeline Diameter', 'Pipeline Installation')],
                'vb_y_Disposal_dict':[('Disposal Site', 'Injection Capacity', 'Disposal')],'vb_y_Storage_dict':[('Storage Site', 'Storage Capacity', 'Storage Expansion')],
                'vb_y_Flow_dict':[('Origin', 'Destination', 'Time', 'Flow')],'v_D_Capacity_dict':[('Disposal Site', 'Disposal Site Capacity')],
                'v_X_Capacity_dict':[('Storage Site', 'Storage Site Capacity')],'v_F_Capacity_dict':[('Origin', 'Destination', 'Flow Capacity')],
                'v_F_Overview_dict':[('Variable Name', 'Documentation', 'Total')],'v_S_FracDemand_dict':[('Completion pad', 'Time', 'Slack FracDemand')],
                'v_S_Production_dict':[('Production pad', 'Time', 'Slack Production')],'v_S_Flowback_dict':[('Completion pad', 'Time', 'Slack Flowback')],
                'v_S_PipelineCapacity_dict':[('Origin', 'Destination', 'Slack Pipeline Capacity')],'v_S_StorageCapacity_dict':[('Storage site', 'Slack Storage Capacity')],
                'v_S_DisposalCapacity_dict':[('Storage site', 'Slack Disposal Capacity')],'v_S_TreatmentCapacity_dict':[('Treatment site', 'Slack Treatment Capacity')],
                'v_S_ReuseCapacity_dict':[('Reuse site', 'Slack Reuse Capacity')]}

        model.reuse_WaterKPI = Var(doc='Reuse Fraction Produced Water = [%]')
        reuseWater_value = (model.v_F_TotalReused.value)/(model.p_beta_TotalProd.value)*100
        model.reuse_WaterKPI.value = reuseWater_value

        model.disposal_WaterKPI = Var(doc='Disposal Fraction Produced Water = [%]')
        disposalWater_value = (model.v_F_TotalDisposed.value)/(model.p_beta_TotalProd.value)*100
        model.disposal_WaterKPI.value = disposalWater_value

        model.fresh_CompletionsDemandKPI = Var(doc='Fresh Fraction Completions Demand = [%]')
        freshDemand_value = (model.v_F_TotalSourced.value)/(model.p_gamma_TotalDemand.value)*100
        model.fresh_CompletionsDemandKPI.value = freshDemand_value

        model.reuse_CompletionsDemandKPI = Var(doc='Reuse Fraction Completions Demand = [%]')
        reuseDemand_value = (model.v_F_TotalReused.value)/(model.p_gamma_TotalDemand.value)*100
        model.reuse_CompletionsDemandKPI.value = reuseDemand_value
        
    elif model.type == 'operational':
        # Detailed: Slacks values included, Same as "All"
        if PrintValues.Detailed in is_print:
            printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_F_PadStorageIn','v_L_ProdTank' 
                        'v_F_PadStorageOut','v_C_Piped','v_C_Trucked','v_C_Sourced','v_C_Disposal',
                        'v_C_Reuse','v_L_Storage','vb_y_Pipeline','vb_y_Disposal','vb_y_Storage', 'v_F_Drain',     
                        'v_B_Production','vb_y_FLow','v_F_Overview']
        
        # Nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage
        if PrintValues.Nominal in is_print:
            printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_C_Piped','v_C_Trucked',
                        'v_C_Sourced','vb_y_Pipeline','vb_y_Disposal','vb_y_Storage','vb_y_Flow','v_F_Overview']

        # Essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
        if PrintValues.Essential in is_print:
            printing_list = ['v_F_Overview'] 

        headers = {'v_F_Piped_dict':[('Origin', 'destination', 'Time', 'Piped water')],'v_C_Piped_dict':[('Origin', 'Destination', 'Time', 'Cost piping')],
                'v_F_Trucked_dict':[('Origin', 'Destination', 'Time', 'Trucked water')],'v_C_Trucked_dict':[('Origin', 'Destination', 'Time', 'Cost trucking')],
                'v_F_Sourced_dict':[('Fresh water source', 'Completion pad', 'Time', 'Sourced water')],'v_C_Sourced_dict':[('Fresh water source', 'Completion pad', 'Time', 'Cost sourced water')],
                'v_F_PadStorageIn_dict':[('Completion pad', 'Time', 'StorageIn')],'v_F_PadStorageOut_dict':[('Completion pad', 'Time', 'StorageOut')],
                'v_C_Disposal_dict':[('Disposal site', 'Time', 'Cost of disposal')],'v_C_Treatment_dict':[('Treatment site', 'Time', 'Cost of Treatment')],
                'v_C_Reuse_dict':[('Completion pad', 'Time', 'Cost of reuse')],'v_C_Storage_dict':[('Storage Site', 'Time', 'Cost of Storage')],
                'v_R_Storage_dict':[('Storage Site', 'Time', 'Credit of Retrieving Produced Water')],'v_L_Storage_dict':[('Storage site', 'Time', 'Storage Levels')],
                'v_L_PadStorage_dict':[('Completion pad', 'Time', 'Storage Levels')],'vb_y_Pipeline_dict':[('Origin', 'Destination', 'Pipeline Diameter', 'Pipeline Installation')],
                'vb_y_Disposal_dict':[('Disposal Site', 'Injection Capacity', 'Disposal')],'vb_y_Storage_dict':[('Storage Site', 'Storage Capacity', 'Storage Expansion')],
                'vb_y_Flow_dict':[('Origin', 'Destination', 'Time', 'Flow')],'v_D_Capacity_dict':[('Disposal Site', 'Disposal Site Capacity')],
                'v_X_Capacity_dict':[('Storage Site', 'Storage Site Capacity')],'v_F_Capacity_dict':[('Origin', 'Destination', 'Flow Capacity')],
                'v_S_FracDemand_dict':[('Completion pad', 'Time', 'Slack FracDemand')], 'v_S_Production_dict':[('Production pad', 'Time', 'Slack Production')],
                'v_S_Flowback_dict':[('Completion pad', 'Time', 'Slack Flowback')],
                'v_S_PipelineCapacity_dict':[('Origin', 'Destination', 'Slack Pipeline Capacity')],'v_S_StorageCapacity_dict':[('Storage site', 'Slack Storage Capacity')],
                'v_S_DisposalCapacity_dict':[('Storage site', 'Slack Disposal Capacity')],'v_S_TreatmentCapacity_dict':[('Treatment site', 'Slack Treatment Capacity')],
                'v_S_ReuseCapacity_dict':[('Reuse site', 'Slack Reuse Capacity')],'v_L_ProdTank_dict':[('Pads', 'Time', 'Production Tank Water Level')],
                'v_F_Drain_dict':[('Pads', 'Time', 'Produced Water Drained From Production Tank')], 'v_B_Production_dict':[('Pads', 'Time', 'Produced Water For Transport From Pad')],
                'v_F_Overview_dict':[('Variable Name', 'Documentation', 'Total')],}
    else:
        raise Exception('Model type {0} is not supported'.format(model.type))


    for variable in model.component_objects(Var):
        if variable._data != None:
            for i in variable._data:
                var_value = variable._data[i].value
                if i is None:
                    headers['v_F_Overview_dict'].append((variable.name, variable.doc, var_value))
                elif i is not None and isinstance(i,str):
                    i = (i,)
                if i is not None and var_value is not None and var_value > 0:
                    headers[str(variable.name) + '_dict'].append((*i, var_value))
    

    # if model.v_C_Slack.value != None and model.v_C_Slack.value > 0:
    #     print('!!!ATTENTION!!! One or several slack variables have been triggered!')


    for i in list(headers.items()):
        dict_name = i[0].removesuffix('_dict')
        if dict_name in printing_list:
                print('\n','='*10, dict_name.upper(),'='*10)
                print(i[1][0])
                for j in i[1][1:]:
                    print('{0}{1} = {2}'.format(dict_name, j[:-1], j[-1]))

    return model, headers