"""
This file contains the data_parser function which converts
the parameters and sets from the get_data function to align 
with the qcp4 model
"""

from trf_pw.util.data_util.get_data import get_data
from trf_pw.util.data_util.spec_utils import set_processing, parameter_processing


def data_parser(df_sets, df_parameters):
    d = {}

    # ---------------SETS---------------------
    # nodes
    d['s_NMS'] = df_sets["NetworkNodes"].tolist()  # mixers and splitters
    d['s_NP'] = df_sets["ProductionPads"].tolist()    # production pads
    d['s_NC'] = df_sets["CompletionsPads"].tolist()     # completion pads
    d['s_NS'] = df_sets["StorageSites"].tolist()  # storage
    d['s_ND'] = df_sets["SWDSites"].tolist()     # disposal
    #TODO: Make additional disposal sites component recovery cases
    d['s_NW'] = df_sets["FreshwaterSources"].tolist()     # freshwater 
    d['s_NT'] = df_sets["TreatmentSites"].tolist()     # treatment
    #NTIN, NTTW, NTCW created in set processing

    

    # ARCS
    d['s_A'] = []
    
    arcs = ['PNA', 'CNA', 'CCA', 'NNA', 'NCA', 'NKA', 'NRA', 'NSA', 'SNA', 'FNA',
            'FCA', 'RCA', 'RSA', 'SCA', 'RNA', 'PCT', 'FCT', 'PKT', 'CKT', 'CCT', 'CST']
    
    # Creating the unified arc set and appending 'Piped' or 'Trucked' to the arc tuple
    for arc_name in arcs:
        if arc_name in list(df_parameters.keys()):
            for (aIN, aOUT) in df_parameters[arc_name]:
                assert df_parameters[arc_name][(aIN, aOUT)] == 1
                if arc_name[2] == 'A':
                    d['s_A'].append((aIN, aOUT, 'Piped'))
                elif arc_name[2] == 'T':
                    d['s_A'].append((aIN, aOUT, 'Trucked'))
                else:
                    'ERROR: Arc is neither defined as a trucking or piping arc'

         
    # s_Ain and s_Aout created in set processing

    # QUALITY
    d['s_Q'] = df_sets['WaterQualityComponents']
    
    d['s_Qalpha_int'] = df_parameters['ComponentTreatment']
    # going to be made in post processing

    # TIME PERIODS
    d['s_T'] = df_sets['TimePeriods']

    d = set_processing(d, df_parameters)


    # -----------------PARAMETERS-----------------------
    # FGen
    d['p_FGen'] = {**df_parameters['PadRates'], **df_parameters['FlowbackRates']}   # Production pads and completions

    # CGen
    d['p_CGen'] = {(n, q, t): df_parameters['PadWaterQuality'][(n, q)] for (n, q) in df_parameters['PadWaterQuality'].keys() for t in d['s_T']}


    # FCons
    d['p_FCons'] = df_parameters['CompletionsDemand'] 

    # FCons of production pads will be handles in parameter_processing()

    # Mixers splitters FCons, FGen, CGen will be handled in parameter_processing()

    # Inventory Parameters
    d['p_I0'] = df_parameters['InitialStorageLevel']
    d['p_C0'] = df_parameters['StorageInitialWaterQuality']

    # Treatment Efficiencies
    d['p_alphaW'] = {d['NT_set'][n][0]: df_parameters['TreatmentEfficiency'][n] for n in d['s_NT']}
    d['p_alpha'] = {(d['NT_set'][n][0],q): df_parameters['RemovalEfficiency'][n,q] for n in d['s_NT'] for q in d['s_Q']}

    # Treatment Capacities
    d['p_Cap_fresh'] = df_parameters['FreshwaterSourcingAvailability']
    d['p_Cap_disposal'] = df_parameters['InitialDisposalCapacity']  # adding capacity for component recovery in parameter_processing
    d['p_Cap_treat'] = df_parameters['InitialTreatmentCapacity']
    # Combining the three into one p_Cap will be done in the parameter processing

    # Cmin
    d['p_Cmin'] = {(d['NT_set'][n][2],q): df_parameters['MinResidualQuality'][n,q] for n in d['s_NT'] for q in d['s_Q']}

    # TimeDiscretization
    d['p_dt'] = 7   #TODO: Get get_data() to read this


    # Operating costs
    d['p_betaArc'] = {}
    for (aIN, aOUT, aTP) in d['s_A']:
        if aOUT.endswith('_CW') or aOUT.endswith('_TW'):
            d['p_betaArc'][aIN, aOUT, aTP] = 0  # setting all arcs to K_CW as have no cost
        elif aTP == 'Piped':
            d['p_betaArc'][aIN, aOUT, aTP] = df_parameters['PipelineOperationalCost'][(aIN, aOUT)]
        else:   #trucking case
            d['p_betaArc'][aIN, aOUT, aTP] = 0.01   #TODO: Change trucking case
    #TODO: Trucking costs properly
    d['p_betaD'] = df_parameters['DisposalOperationalCost']
    d['p_betaW'] = df_parameters['FreshSourcingCost']
    d['p_betaT'] = {d['NT_set'][n][0]: df_parameters['TreatmentOperationalCost'][n] for n in d['s_NT']}
    d['p_betaS'] = df_parameters['StorageCost']
    #d['p_gammaT'] = {(d['NT_set'][n][2],q): df_parameters['ComponentPrice'][n,q] for n in d['s_NT'] for q in d['s_Q']}
    d['p_gammaT'] = df_parameters['TreatmentReward']
    d['p_gammaS'] = df_parameters['StorageWithdrawalRevenue']

    # Bounds
    d['p_Ibounds'] = {(n,t):(0,df_parameters['InitialStorageCapacity'][n]) for n in d['s_NS'] for t in d['s_T']}
    
    d['p_Fbounds'] = {}
    for (aIN,aOUT,aTP) in d['s_A']:
        for t in d['s_T']:
            # Trucked flow = Max Piped flow if volume is being trucked
            if aTP == "Trucked":
                d['p_Fbounds'][aIN,aOUT,aTP,t] = (0, max(list(df_parameters['InitialPipelineCapacity'].values())))   #TODO: Change this value

            # Flow from treatment unit to pseudo disposal is max piped flow
            elif aOUT.endswith('_TW') or aOUT.endswith('_CW'):
                d['p_Fbounds'][aIN,aOUT,aTP,t] = (0, max(list(df_parameters['InitialPipelineCapacity'].values())))
            
            # For all the other cases - store the pipeline capacity as is
            else:
                d['p_Fbounds'][aIN,aOUT,aTP,t] = (0,df_parameters['InitialPipelineCapacity'][aIN,aOUT])
                # Treatment flows within the network are handled in parameter processing
    

    
    d = parameter_processing(d, df_parameters)


    
    return d







    





#%%


# %%
