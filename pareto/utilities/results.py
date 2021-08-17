##############################################################################
# 
##############################################################################
"""


Authors: PARETO Team 
"""
from pareto.operational_water_management.\
    operational_produced_water_optimization_model import (ProdTank)
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

        # PrintValues.Detailed: Slacks values included, Same as "All"
        if is_print[0].value == 0:
            printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_F_PadStorageIn','v_F_ReuseDestination',
                        'v_X_Capacity','v_T_Capacity','v_F_Capacity','v_D_Capacity',   
                        'v_F_DisposalDestination','v_F_PadStorageOut','v_C_Piped',
                        'v_C_Trucked','v_C_Sourced','v_C_Disposal','v_C_Reuse','v_L_Storage',
                        'vb_y_Pipeline','vb_y_Disposal','vb_y_Storage','vb_y_Treatment',
                        'vb_y_FLow','v_F_Overview','v_S_FracDemand','v_S_Production','v_S_Flowback',         
                        'v_S_PipelineCapacity','v_S_StorageCapacity','v_S_DisposalCapacity', 
                        'v_S_TreatmentCapacity','v_S_ReuseCapacity']
        
        # PrintValues.Nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage + etc.
        if is_print[0].value == 1:
            printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_C_Piped','v_C_Trucked',
                        'v_C_Sourced','vb_y_Pipeline','vb_y_Disposal','vb_y_Storage','vb_y_Flow',
                        'vb_y_Treatment','v_F_Overview']

        # PrintValues.Essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
        if is_print[0].value == 2:
            printing_list = ['v_F_Overview'] 

        headers = {'v_F_Overview_dict':[('Variable Name', 'Documentation', 'Total')],'v_F_Piped_dict':[('Origin', 'destination', 'Time', 'Piped water')],
                'v_C_Piped_dict':[('Origin', 'Destination', 'Time', 'Cost piping')],'v_F_Trucked_dict':[('Origin', 'Destination', 'Time', 'Trucked water')],
                'v_C_Trucked_dict':[('Origin', 'Destination', 'Time', 'Cost trucking')],'v_F_Sourced_dict':[('Fresh water source', 'Completion pad', 'Time', 'Sourced water')],
                'v_C_Sourced_dict':[('Fresh water source', 'Completion pad', 'Time', 'Cost sourced water')],
                'v_F_PadStorageIn_dict':[('Completion pad', 'Time', 'StorageIn')],'v_F_PadStorageOut_dict':[('Completion pad', 'Time', 'StorageOut')],
                'v_C_Disposal_dict':[('Disposal site', 'Time', 'Cost of disposal')],'v_C_Treatment_dict':[('Treatment site', 'Time', 'Cost of Treatment')],
                'v_C_Reuse_dict':[('Completion pad', 'Time', 'Cost of reuse')],'v_C_Storage_dict':[('Storage Site', 'Time', 'Cost of Storage')],
                'v_R_Storage_dict':[('Storage Site', 'Time', 'Credit of Retrieving Produced Water')],'v_L_Storage_dict':[('Storage site', 'Time', 'Storage Levels')],
                'v_L_PadStorage_dict':[('Completion pad', 'Time', 'Storage Levels')],'vb_y_Pipeline_dict':[('Origin', 'Destination', 'Pipeline Diameter', 'Pipeline Installation')],
                'vb_y_Disposal_dict':[('Disposal Site', 'Injection Capacity', 'Disposal')],'vb_y_Storage_dict':[('Storage Site', 'Storage Capacity', 'Storage Expansion')],
                'vb_y_Flow_dict':[('Origin', 'Destination', 'Time', 'Flow')],'vb_y_Treatment_dict':[('Treatment Site', 'Treatment Capacity', 'Treatment Expansion')],
                'v_D_Capacity_dict':[('Disposal Site', 'Disposal Site Capacity')],'v_T_Capacity_dict':[('Treatment Site', 'Treatment Capacity')],
                'v_X_Capacity_dict':[('Storage Site', 'Storage Site Capacity')],'v_F_Capacity_dict':[('Origin', 'Destination', 'Flow Capacity')],
                'v_S_FracDemand_dict':[('Completion pad', 'Time', 'Slack FracDemand')],
                'v_S_Production_dict':[('Production pad', 'Time', 'Slack Production')],'v_S_Flowback_dict':[('Completion pad', 'Time', 'Slack Flowback')],
                'v_S_PipelineCapacity_dict':[('Origin', 'Destination', 'Slack Pipeline Capacity')],'v_S_StorageCapacity_dict':[('Storage site', 'Slack Storage Capacity')],
                'v_S_DisposalCapacity_dict':[('Storage site', 'Slack Disposal Capacity')],'v_S_TreatmentCapacity_dict':[('Treatment site', 'Slack Treatment Capacity')],
                'v_S_ReuseCapacity_dict':[('Reuse site', 'Slack Reuse Capacity')],'v_F_ReuseDestination_dict':[('Completion Pad', 'Time', 'Total Deliveries to Completion Pad')],
                'v_F_DisposalDestination_dict':[('Disposal Site', 'Time', 'Total Deliveries to Disposal Site')]}

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
        # PrintValues.Detailed: Slacks values included, Same as "All"
        if is_print[0].value == 0:
            printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_F_PadStorageIn','v_L_ProdTank' 
                        'v_F_PadStorageOut','v_C_Piped','v_C_Trucked','v_C_Sourced','v_C_Disposal',
                        'v_C_Reuse','v_L_Storage','vb_y_Pipeline','vb_y_Disposal','vb_y_Storage', 'v_F_Drain',     
                        'v_B_Production','vb_y_FLow','v_F_Overview','v_L_PadStorage','v_C_Treatment','v_C_Storage',
                        'v_R_Storage','v_S_FracDemand','v_S_Production','v_S_Flowback','v_S_PipelineCapacity', 
                        'v_S_StorageCapacity','v_S_DisposalCapacity','v_S_TreatmentCapacity','v_S_ReuseCapacity',
                        'v_D_Capacity','v_X_Capacity','v_F_Capacity']
        
        # PrintValues.Nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage
        if is_print[0].value == 1:
            printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_C_Piped','v_C_Trucked',
                        'v_C_Sourced','vb_y_Pipeline','vb_y_Disposal','vb_y_Storage','vb_y_Flow','v_F_Overview']

        # PrintValues.Essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
        if is_print[0].value == 2:
            printing_list = ['v_F_Overview'] 

        headers = {'v_F_Overview_dict':[('Variable Name', 'Documentation', 'Total')],'v_F_Piped_dict':[('Origin', 'destination', 'Time', 'Piped water')],
                'v_C_Piped_dict':[('Origin', 'Destination', 'Time', 'Cost piping')],'v_F_Trucked_dict':[('Origin', 'Destination', 'Time', 'Trucked water')],
                'v_C_Trucked_dict':[('Origin', 'Destination', 'Time', 'Cost trucking')],'v_F_Sourced_dict':[('Fresh water source', 'Completion pad', 'Time', 'Sourced water')],
                'v_C_Sourced_dict':[('Fresh water source', 'Completion pad', 'Time', 'Cost sourced water')],
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
                'v_S_ReuseCapacity_dict':[('Reuse site', 'Slack Reuse Capacity')],
                'v_B_Production_dict':[('Pads', 'Time', 'Produced Water For Transport From Pad')]}

        if model.config.production_tanks == ProdTank.equalized:
            headers.update({'v_L_ProdTank_dict':[('Pads', 'Time', 'Production Tank Water Level')]})
            headers.update({'v_F_Drain_dict':[('Pads', 'Time', 'Produced Water Drained From Production Tank')]})
        elif model.config.production_tanks == ProdTank.individual:
            headers.update({'v_L_ProdTank_dict':[('Pads', 'Tank', 'Time', 'Production Tank Water Level')]})
            headers.update({'v_F_Drain_dict':[('Pads', 'Tank', 'Time', 'Produced Water Drained From Production Tank')]})
        else:
            raise Exception('Tank Type {0} is not supported'.format(model.config.production_tanks))

    else:
        raise Exception('Model type {0} is not supported'.format(model.type))


    for variable in model.component_objects(Var):
        if variable._data is not None:
            for i in variable._data:
                var_value = variable._data[i].value
                if i is None:
                    headers['v_F_Overview_dict'].append((variable.name, variable.doc, var_value))
                elif i is not None and isinstance(i,str):
                    i = (i,)
                if i is not None and var_value is not None and var_value > 0:
                    headers[str(variable.name) + '_dict'].append((*i, var_value))
    
    if model.v_C_Slack.value is not None and model.v_C_Slack.value > 0:
        print('!!!ATTENTION!!! One or several slack variables have been triggered!')
    
    for i in list(headers.items())[1:]:
        dict_name = i[0].removesuffix('_dict')
        if dict_name in printing_list:
                print('\n','='*10, dict_name.upper(),'='*10)
                print(i[1][0])
                for j in i[1][1:]:
                    print('{0}{1} = {2}'.format(dict_name, j[:-1], j[-1]))

    # Loop for printing Overview Information
    for i in list(headers.items())[:1]:
        dict_name = i[0].removesuffix('_dict')
        if dict_name in printing_list:
                print('\n','='*10, dict_name.upper(),'='*10)
                # print(i[1][1][0])
                for j in i[1][1:]:
                    if not j[0]:  # Conditional that checks if a blank line should be added
                        print()
                    elif not j[1]:  # Conditional that checks if the header for a section should be added
                        print(j[0].upper())
                    else:
                        print('{0} = {1}'.format(j[1], j[2]))

    return model, headers