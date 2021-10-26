# -*- coding: utf-8 -*-
"""
Created on Wed Aug 25 14:49:13 2021

@author: mzamarripa
"""

from pareto.strategic_water_management.strategic_produced_water_optimization import (
    create_variables,
    create_model,
    Objectives,
    generate_report,
    PrintValues,
)
from pareto.utilities.get_data import get_data
from pyomo.environ import Var, Param, Set, ConcreteModel, Constraint, SolverFactory
import idaes
import pandas as pd


def read_data(fname):
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
        "PipelineCapacityIncrements",
        "DisposalCapacityIncrements",
        "InitialStorageCapacity",
        "StorageCapacityIncrements",
        "TreatmentCapacityIncrements",
        "TreatmentEfficiency",
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineExpansionCost",
    ]

    # user needs to provide the path to the case study data file
    [df_sets, df_parameters] = get_data(
        "input_data_generic_strategic_case_study_LAYFLAT_FULL.xlsx",
        set_list,
        parameter_list,
    )

    # model = ConcreteModel()
    # print('Initialization complete.')

    return df_sets, df_parameters
