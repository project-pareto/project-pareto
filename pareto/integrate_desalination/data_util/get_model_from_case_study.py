# -*- coding: utf-8 -*-
"""
Created on Wed Aug 30 14:39:33 2023

@author: ssnaik
"""
"""
A file to read excel data and feed into a network model. 
Took this from Arsh's run.py file. 
"""

from trf_pw.util.data_util.data_parser import data_parser
from trf_pw.util.data_util.data_checker import data_checker
from trf_pw.util.data_util.get_data import get_data
from trf_pw.util.data_util.data_modifier import add_solids_gen_parameter, add_min_capacity_parameter, set_processing
import os
from importlib import resources

def get_processed_data(file_name = "integrated_desalination_case_study.xlsx"):
    set_list = [
        "ProductionPads",
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
        "TreatmentTechnologies",
    ]
    parameter_list = [
        "Units",
        "PNA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NRA",
        "NSA",
        "FCA",
        "FNA",
        "RCA",
        "RNA",
        "RSA",
        "SCA",
        "SNA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
    
        "DesalinationTechnologies",
        "DesalinationSites",
        "TruckingTime",
        "CompletionsDemand",
        "InitialStorageLevel",
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
        "PipelineOperationalCost",
        "FreshSourcingCost",
        "TruckingHourlyCost",
        "PipelineDiameterValues",
        "DisposalCapacityIncrements",
        "InitialStorageCapacity",
        "StorageCapacityIncrements",
        "TreatmentCapacityIncrements",
        "TreatmentEfficiency",
        "RemovalEfficiency",
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineCapexDistanceBased",
        "PipelineCapexCapacityBased",
        "PipelineCapacityIncrements",
        "PipelineExpansionDistance",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
        "PadStorageInitialWaterQuality",
        "DisposalOperatingCapacity",
        "MinResidualQuality",
        "ComponentPrice",
        "ComponentTreatment",
        "StorageCost",
        "StorageWithdrawalRevenue",
        "TreatmentReward"
    ]
    # -------------------------Loading data and model------------------------------
    #checking for tabs in the excel sheet
    with resources.path(
        "pareto.case_studies",
        file_name
    ) as fpath:
           
        # Permian case study has issues because FNA tab not present
        (set_list_found, set_list_empty), (param_list_found, param_list_empty) = data_checker(fpath, set_list, parameter_list)
        
        # importing data
        [df_sets, df_parameters] = get_data(fpath, set_list_found, param_list_found)    # Pareto tool
        
    data = data_parser(df_sets, df_parameters)
    data = set_processing(data)
    data = add_solids_gen_parameter(data)
    data = add_min_capacity_parameter(data)

    return data

if __name__ == "__main__":
    data = get_processed_data()
   