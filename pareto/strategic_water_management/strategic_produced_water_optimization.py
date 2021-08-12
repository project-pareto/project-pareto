# Title: STRATEGIC Produced Water Optimization Model

# Notes:
# - Implemented a corrected version of the disposal capacity constraint considering more trucking-to-disposal arcs (PKT, SKT, SKT, RKT) [June 29]
# - Implemented an improved slack variable display loop [June 29]
# - Implemented fresh sourcing via trucking [July 2]
# - Implemented completions pad storage [July 6]
# - Implemented changes to flowback processing [July 14]
# - Implemented correction for pipeline capacity slack penalty [July 19]
# - Implemented terminal storage level parameters and constraints [July 26]
# - Implemented enhanced network node balance (incl. storage flows) [July 28]
# - Implemented bi-directional capacity restriction [July 29]
# - Implemented KPI constraints (total piped/trucked/sourced/disposed/... volumes) [July 30]
# - Implemented layflat modifications [August 5]
# - Implemented treatment capacity expansion [August 10]
# - Implemented alternative objectives (cost vs. reuse) via config argument [August 11]
# - Implemented reuse/disposal deliveries variables/constraints/results [August 12]

# Import
from pyomo.environ import (Var, Param, Set, ConcreteModel, Constraint, Objective, minimize,
                            NonNegativeReals, Reals, Binary)
from pareto.utilities.get_data import get_data
from importlib import resources                            
from pyomo.opt import SolverFactory
import pyomo.environ 
# from gurobipy import *
from pyomo.common.config import ConfigBlock, ConfigValue, In
from enum import Enum

class Objectives(Enum):
    cost = 0
    reuse = 1
 
# create config dictionary
CONFIG = ConfigBlock()
CONFIG.declare("has_pipeline_constraints", ConfigValue(
    default=True,
    domain=In([True, False]),
    description="build pipeline constraints",
    doc="""Indicates whether holdup terms should be constructed or not.
**default** - True.
**Valid values:** {
**True** - construct pipeline constraints,
**False** - do not construct pipeline constraints}"""))
CONFIG.declare("objective", ConfigValue(
    default=Objectives.cost,
    domain=In(Objectives),
    description='alternate objectives selection',
    doc='Alternate objective functions (i.e., minimize cost, maximize reuse)'))

# Creation of a Concrete Model

def create_model(df_sets, df_parameters, default={}):
    model = ConcreteModel()
    # import config dictionary
    model.config = CONFIG(default)
    
    ## Define sets ##

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

    # model.s_P.pprint()
    # model.s_L.pprint()

    ## Define continuous variables ##

    model.v_Z           = Var(within=Reals, doc='Objective function variable [$]')

    model.v_F_Piped     = Var(model.s_L,model.s_L,model.s_T,within=NonNegativeReals, doc='Produced water quantity piped from location l to location l [bbl/week]')
    model.v_F_Trucked   = Var(model.s_L,model.s_L,model.s_T,within=NonNegativeReals, doc='Produced water quantity trucked from location l to location l [bbl/week]')
    model.v_F_Sourced   = Var(model.s_F,model.s_CP,model.s_T,within=NonNegativeReals, doc='Fresh water sourced from source f to completions pad p [bbl/week]')
    
    model.v_F_PadStorageIn  = Var(model.s_CP,model.s_T,within=NonNegativeReals, doc='Water put into completions pad storage [bbl/week]')
    model.v_F_PadStorageOut = Var(model.s_CP,model.s_T,within=NonNegativeReals, doc='Water from completions pad storage used for fracturing [bbl/week]')

    model.v_L_Storage       = Var(model.s_S,model.s_T,within=NonNegativeReals, doc='Water level at storage site [bbl]')
    model.v_L_PadStorage    = Var(model.s_CP,model.s_T,within=NonNegativeReals, doc='Water level in completions pad storage [bbl]')

    model.v_F_TotalTrucked  = Var(within=NonNegativeReals, doc='Total volume water trucked [bbl]')
    model.v_F_TotalSourced  = Var(within=NonNegativeReals, doc='Total volume freshwater sourced [bbl]')
    model.v_F_TotalDisposed = Var(within=NonNegativeReals, doc='Total volume of water disposed [bbl]')
    model.v_F_TotalReused   = Var(within=NonNegativeReals, doc='Total volume of produced water reused [bbl]')    

    model.v_C_Piped     = Var(model.s_L,model.s_L,model.s_T,within=NonNegativeReals, doc='Cost of piping produced water from location l to location l [$/week]')
    model.v_C_Trucked   = Var(model.s_L,model.s_L,model.s_T,within=NonNegativeReals, doc='Cost of trucking produced water from location l to location l [$/week]')
    model.v_C_Sourced   = Var(model.s_F,model.s_CP,model.s_T,within=NonNegativeReals, doc='Cost of sourcing fresh water from source f to completion pad p [$/week]')
    model.v_C_Disposal  = Var(model.s_K,model.s_T,within=NonNegativeReals, doc='Cost of injecting produced water at disposal site [$/week]')
    model.v_C_Treatment = Var(model.s_R,model.s_T,within=NonNegativeReals, doc='Cost of treating produced water at treatment site [$/week]')
    model.v_C_Reuse     = Var(model.s_CP,model.s_T,within=NonNegativeReals, doc='Cost of reusing produced water at completions site [$/week]')
    model.v_C_Storage   = Var(model.s_S,model.s_T,within=NonNegativeReals, doc='Cost of storing produced water at storage site [$/week]')
    model.v_R_Storage   = Var(model.s_S,model.s_T,within=NonNegativeReals, doc='Credit for retrieving stored produced water from storage site [$/bbl]')

    model.v_C_TotalSourced   = Var(within=NonNegativeReals, doc='Total cost of sourcing freshwater [$]')
    model.v_C_TotalDisposal  = Var(within=NonNegativeReals, doc='Total cost of injecting produced water [$]')
    model.v_C_TotalTreatment = Var(within=NonNegativeReals, doc= 'Total cost of treating produced water [$]') 
    model.v_C_TotalReuse     = Var(within=NonNegativeReals, doc='Total cost of reusing produced water [$]')
    model.v_C_TotalPiping    = Var(within=NonNegativeReals, doc='Total cost of piping produced water [$]')
    model.v_C_TotalStorage   = Var(within=NonNegativeReals, doc='Total cost of storing produced water [$]')
    model.v_C_TotalTrucking  = Var(within=NonNegativeReals, doc='Total cost of trucking produced water [$]')
    model.v_C_Slack          = Var(within=NonNegativeReals, doc='Total cost of slack variables [$]')
    model.v_R_TotalStorage   = Var(within=NonNegativeReals, doc='Total credit for withdrawing produced water [$]')

    model.v_F_ReuseDestination    = Var(model.s_CP,model.s_T,within=NonNegativeReals, doc='Total deliveries to completions pad [bbl/week]')
    model.v_F_DisposalDestination = Var(model.s_K,model.s_T,within=NonNegativeReals, doc='Total deliveries to disposal site [bbl/week]')

    model.v_D_Capacity       = Var(model.s_K,within=NonNegativeReals, doc='Disposal capacity at a disposal site [bbl/week]')
    model.v_X_Capacity       = Var(model.s_S,within=NonNegativeReals, doc='Storage capacity at a storage site [bbl/week]')
    model.v_T_Capacity       = Var(model.s_R,within=NonNegativeReals, doc='Treatment capacity at a treatment site [bbl/week]')
    model.v_F_Capacity       = Var(model.s_L,model.s_L,within=NonNegativeReals, doc='Flow capacity along pipeline arc [bbl/week]')

    model.v_C_DisposalCapEx  = Var(within=NonNegativeReals, doc='Capital cost of constructing or expanding disposal capacity [$]')
    model.v_C_PipelineCapEx  = Var(within=NonNegativeReals, doc='Capital cost of constructing or expanding piping capacity [$]')
    model.v_C_StorageCapEx   = Var(within=NonNegativeReals, doc='Capital cost of constructing or expanding storage capacity [$]')
    model.v_C_TreatmentCapEx = Var(within=NonNegativeReals, doc='Capital cost of constructing or expanding treatment capacity [$]')

    model.v_S_FracDemand        = Var(model.s_CP,model.s_T,within=NonNegativeReals, doc='Slack variable to meet the completions demand [bbl/week]')
    model.v_S_Production        = Var(model.s_PP,model.s_T,within=NonNegativeReals, doc='Slack variable to process the produced water production [bbl/week]')
    model.v_S_Flowback          = Var(model.s_CP,model.s_T,within=NonNegativeReals, doc='Slack variable to proces flowback water production [bbl/week]')
    model.v_S_PipelineCapacity  = Var(model.s_L,model.s_L,within=NonNegativeReals, doc='Slack variable to provide necessary pipeline capacity [bbl]')  
    model.v_S_StorageCapacity   = Var(model.s_S,within=NonNegativeReals, doc='Slack variable to provide necessary storage capacity [bbl]')
    model.v_S_DisposalCapacity  = Var(model.s_K,within=NonNegativeReals, doc='Slack variable to provide necessary disposal capacity [bbl/week]')
    model.v_S_TreatmentCapacity = Var(model.s_R,within=NonNegativeReals, doc='Slack variable to provide necessary treatment capacity [bbl/weel]')
    model.v_S_ReuseCapacity     = Var(model.s_O,within=NonNegativeReals, doc='Slack variable to provide necessary reuse capacity [bbl/week]')

    ## Define binary variables ##

    model.vb_y_Pipeline      = Var(model.s_L,model.s_L,model.s_D,within=Binary, doc='New pipeline installed between one location and another location with specific diameter')
    model.vb_y_Storage       = Var(model.s_S,model.s_C,within=Binary, doc='New or additional storage capacity installed at storage site with specific storage capacity')
    model.vb_y_Treatment     = Var(model.s_R,model.s_J,within=Binary, doc='New or additional treatment capacity installed at treatment site with specific treatment capacity')
    model.vb_y_Disposal      = Var(model.s_K,model.s_I,within=Binary, doc='New or additional disposal capacity installed at disposal site with specific injection capacity')
    model.vb_y_Flow          = Var(model.s_L,model.s_L,model.s_T,within=Binary, doc='Directional flow between two locations')

    # model.vb_z_Pipeline      = Var(model.s_L,model.s_L,model.s_D,model.s_T,within=Binary, doc='Timing of pipeline installation between two locations')
    # model.vb_z_Storage       = Var(model.s_S,model.s_C,model.s_T,within=Binary, doc='Timing of storage facility installation at storage site')
    # model.vb_z_Disposal      = Var(model.s_K,model.s_I,model.s_T,within=Binary, doc='Timing of disposal facility installation at disposal site')

    ## Define set parameters ##

    PCA_Table = {
    }

    PNA_Table = {
    }

    PPA_Table = {
    }

    CNA_Table = {
    }

    NNA_Table = {
    }

    NCA_Table = {        
    }

    NKA_Table = {        
    }

    NSA_Table = {
    }

    NRA_Table = {
    }

    NOA_Table = {
    }

    FCA_Table = {
    }

    RNA_Table = {
    }

    RKA_Table = {
    }

    SNA_Table = {
    }

    SCA_Table = {
    }

    SKA_Table = {
    }

    SRA_Table = {
    }

    SOA_Table = {
    }

    PCT_Table = {
    }

    PKT_Table = {
    }

    PST_Table = {
    }

    PRT_Table = {
    }

    POT_Table = {
    }

    CKT_Table = {
    }

    CST_Table = {
    }

    CRT_Table = {
    }

    SCT_Table = {
    }

    CRT_Table = {
    }

    SCT_Table = {
    }

    SKT_Table = {
    }

    RKT_Table = {
    }

    model.p_PCA              = Param(model.s_PP,model.s_CP,default=0,initialize=PCA_Table, doc='Valid production-to-completions pipeline arcs [-]')
    model.p_PNA              = Param(model.s_PP,model.s_N,default=0,initialize=df_parameters['PNA'], doc='Valid production-to-node pipeline arcs [-]')
    model.p_PPA              = Param(model.s_PP,model.s_PP,default=0,initialize=PPA_Table, doc='Valid production-to-production pipeline arcs [-]')
    model.p_CNA              = Param(model.s_CP,model.s_N,default=0,initialize=df_parameters['CNA'], doc='Valid completion-to-node pipeline arcs [-]')
    model.p_CCA              = Param(model.s_CP,model.s_CP,default=0,initialize=df_parameters['CCA'], doc='Valid completions-to-completions pipelin arcs [-]')
    model.p_NNA              = Param(model.s_N,model.s_N,default=0,initialize=df_parameters['NNA'], doc='Valid node-to-node pipeline arcs [-]')
    model.p_NCA              = Param(model.s_N,model.s_CP,default=0,initialize=df_parameters['NCA'], doc='Valid node-to-completions pipeline arcs [-]')
    model.p_NKA              = Param(model.s_N,model.s_K,default=0,initialize=df_parameters['NKA'], doc='Valid node-to-disposal pipeline arcs [-]')
    model.p_NSA              = Param(model.s_N,model.s_S,default=0,initialize=df_parameters['NSA'], doc='Valid node-to-storage pipeline arcs [-]')
    model.p_NRA              = Param(model.s_N,model.s_R,default=0,initialize=df_parameters['NRA'], doc='Valid node-to-treatment pipeline arcs [-]')
    model.p_NOA              = Param(model.s_N,model.s_O,default=0,initialize=NOA_Table, doc='Valid node-to-reuse pipeline arcs [-]')
    model.p_FCA              = Param(model.s_F,model.s_CP,default=0,initialize=df_parameters['FCA'], doc='Valid freshwater-to-completions pipeline arcs [-]')
    model.p_RCA              = Param(model.s_R,model.s_CP,default=0,initialize=df_parameters['RCA'], doc='Valid treatment-to-completions layflat arcs [-]')
    model.p_RNA              = Param(model.s_R,model.s_N,default=0,initialize=df_parameters['RNA'], doc='Valid treatment-to-node pipeline arcs [-]')
    model.p_RKA              = Param(model.s_R,model.s_K,default=0,initialize=RKA_Table, doc='Valid treatment-to-disposal pipeline arcs [-]')
    model.p_SNA              = Param(model.s_S,model.s_N,default=0,initialize=df_parameters['SNA'], doc='Valid storage-to-node pipeline arcs [-]')
    model.p_SCA              = Param(model.s_S,model.s_CP,default=0,initialize=SCA_Table, doc='Valid storage-to-completions pipeline arcs [-]')
    model.p_SKA              = Param(model.s_S,model.s_K,default=0,initialize=SKA_Table, doc='Valid storage-to-disposal pipeline arcs [-]')
    model.p_SRA              = Param(model.s_S,model.s_R,default=0,initialize=SRA_Table, doc='Valid storage-to-treatment pipeline arcs [-]')
    model.p_SOA              = Param(model.s_S,model.s_O,default=0,initialize=SOA_Table, doc='Valid storage-to-reuse pipeline arcs [-]')
   
    model.p_PCT              = Param(model.s_PP,model.s_CP,default=0,initialize=df_parameters['PCT'], doc='Valid production-to-completions trucking arcs [-]')
    model.p_FCT              = Param(model.s_F,model.s_CP,default=0,initialize=df_parameters['FCT'], doc='Valid freshwater-to-completions trucking arcs [-]')
    model.p_PKT              = Param(model.s_PP,model.s_K,default=0,initialize=df_parameters['PKT'], doc='Valid production-to-disposal trucking arcs [-]')
    model.p_PST              = Param(model.s_PP,model.s_S,default=0,initialize=PST_Table, doc='Valid production-to-storage trucking arcs [-]')
    model.p_PRT              = Param(model.s_PP,model.s_R,default=0,initialize=PRT_Table, doc='Valid production-to-treatment trucking arcs [-]')
    model.p_POT              = Param(model.s_PP,model.s_O,default=0,initialize=POT_Table, doc='Valid production-to-reuse trucking arcs [-]')
    model.p_CKT              = Param(model.s_CP,model.s_K,default=0,initialize=df_parameters['CKT'], doc='Valid completions-to-disposal trucking arcs [-]')
    model.p_CST              = Param(model.s_CP,model.s_S,default=0,initialize=df_parameters['CST'], doc='Valid completions-to-storage trucking arcs [-]')
    model.p_CRT              = Param(model.s_CP,model.s_R,default=0,initialize=CRT_Table, doc='Valid completions-to-treatment trucking arcs [-]')
    model.p_CCT              = Param(model.s_CP,model.s_CP,default=0,initialize=df_parameters['CCT'], doc='Valid completion-to-completion trucking arcs [-]')
    model.p_SCT              = Param(model.s_S,model.s_CP,default=0,initialize=SCT_Table, doc='Valid storage-to-completions trucking arcs [-]')
    model.p_SKT              = Param(model.s_S,model.s_K,default=0,initialize=SKT_Table, doc='Valid storage-to-disposal trucking arcs [-]')
    model.p_RKT              = Param(model.s_R,model.s_K,default=0,initialize=RKT_Table, doc='Valid treatment-to-disposal trucking arcs [-]')

    # model.p_PCA.pprint()
    # model.p_PNA.pprint()
    # model.p_CNA.pprint()
    # model.p_NNA.pprint()
    # model.p_CCA.pprint()

    ## Define set parameters ##

    CompletionsDemandTable = {
    }

    ProductionTable = {
    }

    FlowbackTable = {}

    InitialPipelineCapacityTable = {   
    }

    # COMMENT: For EXISTING/INITAL pipeline capacity (l,l_tilde)=(l_tilde=l); needs implemented!

    InitialDisposalCapacityTable = {
    }

    InitialStorageCapacityTable = {

    }

    InitialTreatmentCapacityTable = {
    }

    InitialReuseCapacityTable = {

    }

    FreshwaterSourcingAvailabilityTable = {   
    }

    PadOffloadingCapacityTable = {
    }

    StorageOffloadingCapacityTable = {

    }

    ProcessingCapacityPadTable = {

    }

    ProcessingCapacityStorageTable = {

    }

    PipelineCapacityIncrementsTable = {
        ('D0') : 0
    }

    DisposalCapacityIncrementsTable = {
        ('I0') : 0
    }

    StorageDisposalCapacityIncrementsTable = {
        ('C0') : 0
    }

    TruckingTimeTable = {   
    }

    DisposalCapExTable = {
        ('K02','I0') : 0
    }

    StorageCapExTable = {
    }

    TreatmentCapExTable = {
    }

    PipelineCapExTable = {
    }

    DisposalOperationalCostTable = {
    }

    TreatmentOperationalCostTable = {
    }

    ReuseOperationalCostTable = {
    }

    StorageOperationalCostTable = {

    }

    StorageOperationalCreditTable = {

    }

    PipelineOperationalCostTable = {   
    }

    TruckingHourlyCostTable = {
    }

    FreshSourcingCostTable = {
    }

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
    model.p_sigma_Reuse        = Param(model.s_O,default=0,
                                initialize=InitialReuseCapacityTable,
                                doc='Initial weekly reuse capacity at reuse site [bbl/week]')
    model.p_sigma_Freshwater   = Param(model.s_F,model.s_T,default=0,
                                initialize=df_parameters['FreshwaterSourcingAvailability'],
                                doc='Weekly freshwater sourcing capacity at freshwater source [bbl/week]',mutable=True)                                                                                   

    model.p_sigma_OffloadingPad     = Param(model.s_P,default=9999999,
                                    initialize=df_parameters['PadOffloadingCapacity'],
                                    doc='Weekly truck offloading sourcing capacity per pad [bbl/week]',
                                    mutable=True)                            
    model.p_sigma_OffloadingStorage = Param(model.s_S,default=9999999,
                                    initialize=StorageOffloadingCapacityTable,
                                    doc='Weekly truck offloading capacity per pad [bbl/week]',
                                    mutable=True)                             
    model.p_sigma_ProcessingPad     = Param(model.s_P,default=9999999,
                                    initialize=ProcessingCapacityPadTable,
                                    doc='Weekly processing (e.g. clarification) capacity per pad [bbl/week]',
                                    mutable=True)
    model.p_sigma_ProcessingStorage = Param(model.s_S,default=9999999,
                                    initialize=ProcessingCapacityStorageTable,
                                    doc='Weekly processing (e.g. clarification) capacity per storage site [bbl/week]',
                                    mutable=True)  
    
    model.p_epsilon_Treatment   = Param(model.s_R,default=1.0,
                                initialize=df_parameters['TreatmentEfficiency'],
                                doc='Treatment efficiency [%]')

    model.p_delta_Pipeline      = Param(model.s_D,default=10,
                                initialize=df_parameters['PipelineCapacityIncrements'],
                                doc='Pipeline capacity installation/expansion increments [bbl/week]')

    model.p_delta_Disposal      = Param(model.s_I,default=10,
                                initialize=df_parameters['DisposalCapacityIncrements'],
                                doc='Disposal capacity installation/expansion increments [bbl/week]')

    model.p_delta_Storage       = Param(model.s_C,default=10,
                                initialize=df_parameters['StorageCapacityIncrements'],
                                doc='Storage capacity installation/expansion increments [bbl]') 
    model.p_delta_Treatment     = Param(model.s_J,default=10,
                                initialize=df_parameters['TreatmentCapacityIncrements'],
                                doc='Treatment capacity installation/expansion increments [bbl/week]')                           

    model.p_delta_Truck         = Param(default=110,doc='Truck capacity [bbl]')

    model.p_tau_Disposal        = Param(model.s_K,default=12,
                                doc='Disposal construction/expansion lead time [weeks]')

    model.p_tau_Storage         = Param(model.s_S,default=12,
                                doc='Storage constructin/expansion lead time [weeks]')                            

    model.p_tau_Pipeline        = Param(model.s_L,model.s_L,default=12,
                                doc='Pipeline construction/expansion lead time [weeks')

    model.p_tau_Trucking        = Param(model.s_L,model.s_L,default=9999999,
                                initialize=df_parameters['TruckingTime'],
                                doc='Drive time between locations [hr]')                              
                            
    # COMMENT: Many more parameters missing. See documentation for details. 

    model.p_lambda_Storage      = Param(model.s_S,default=0,
                                doc='Initial storage level at storage site [bbl]')

    model.p_lambda_PadStorage   = Param(model.s_CP,default=0,
                                doc='Initial storage level at completions site [bbl]')                                

    model.p_theta_Storage       = Param(model.s_S,default=0,
                                doc='Terminal storage level at storage site [bbl]')
    
    model.p_theta_PadStorage    = Param(model.s_CP,default=0,
                                doc='Terminal storage level at completions site [bbl]')                        

    model.p_lambda_Pipeline     = Param(model.s_L,model.s_L,default=9999999,
                                doc='Pipeline segment length [miles]')

    model.p_kappa_Disposal      = Param(model.s_K,model.s_I,default=20,
                                initialize=df_parameters['DisposalExpansionCost'],
                                doc='Disposal construction/expansion capital cost for selected increment [$/bbl]')    

    model.p_kappa_Storage       = Param(model.s_S,model.s_C,default=0.1,
                                initialize=df_parameters['StorageExpansionCost'],
                                doc='Storage construction/expansion capital cost for selected increment [$/bbl]')
    
    model.p_kappa_Treatment     = Param(model.s_R,model.s_J,default=10,
                                initialize=df_parameters['TreatmentExpansionCost'],
                                doc='Treatment construction/expansion capital cost for selected increment [$/bbl]')

    model.p_kappa_Pipeline      = Param(model.s_L,model.s_L,model.s_D,default=5,
                                initialize=df_parameters['PipelineExpansionCost'],
                                doc='Pipeline construction/expansion capital cost for selected increment [$/bbl]')                            

    # model.p_kappa_Disposal.pprint()
    # model.p_kappa_Storage.pprint()
    # model.p_kappa_Treatment.pprint()
    # model.p_kappa_Pipeline.pprint()

    model.p_pi_Disposal         = Param(model.s_K,default=9999999,
                                initialize=df_parameters['DisposalOperationalCost'],
                                doc='Disposal operational cost [$/bbl]')
    model.p_pi_Treatment        = Param(model.s_R,default=0,
                                initialize=df_parameters['TreatmentOperationalCost'],
                                doc='Treatment operational cost [$/bbl')
    model.p_pi_Reuse            = Param(model.s_CP,default=9999999,
                                initialize=df_parameters['ReuseOperationalCost'],
                                doc='Reuse operational cost [$/bbl]')                                                        
    model.p_pi_Storage          = Param(model.s_S,default=1,
                                initialize=StorageOperationalCostTable,
                                doc='Storage deposit operational cost [$/bbl]')
    model.p_rho_Storage         = Param(model.s_S,default=0.99,
                                initialize=StorageOperationalCreditTable,
                                doc='Storage withdrawal operational credit [$/bbl]')
    model.p_pi_Pipeline         = Param(model.s_L,model.s_L,default=0.01,
                                initialize=df_parameters['PipelineOperationalCost'],
                                doc='Pipeline operational cost [$/bbl]')
    model.p_pi_Trucking        = Param(model.s_L,default=9999999,
                                initialize=df_parameters['TruckingHourlyCost'],
                                doc='Trucking hourly cost (by source) [$/bbl]')  
    model.p_pi_Sourcing         = Param(model.s_F,default=9999999,
                                initialize=df_parameters['FreshSourcingCost'],
                                doc='Fresh sourcing cost [$/bbl]')  

    model.p_M_Flow              = Param(default=9999999, doc='Big-M flow parameter [bbl/week]')

    model.p_psi_FracDemand          = Param(default=999999999, doc='Slack cost parameter [$]')
    model.p_psi_Production          = Param(default=999999999, doc='Slack cost parameter [$]')
    model.p_psi_Flowback            = Param(default=999999999, doc='Slack cost parameter [$]')
    model.p_psi_PipelineCapacity    = Param(default=999999999, doc='Slack cost parameter [$]')
    model.p_psi_StorageCapacity     = Param(default=999999999, doc='Slack cost parameter [$]')
    model.p_psi_DisposalCapacity    = Param(default=999999999, doc='Slack cost parameter [$]')
    model.p_psi_TreatmentCapacity   = Param(default=999999999, doc='Slack cost parameter [$]')
    model.p_psi_ReuseCapacity       = Param(default=999999999, doc='Slack cost parameter [$]')

    # model.p_sigma_Freshwater.pprint()

    ## Define cost objective function ##

    if model.config.objective == Objectives.cost:
        def CostObjectiveFunctionRule(model):
            return model.v_Z == (model.v_C_TotalSourced + model.v_C_TotalDisposal + model.v_C_TotalTreatment + model.v_C_TotalReuse
                                + model.v_C_TotalPiping + model.v_C_TotalStorage + model.v_C_TotalTrucking + model.v_C_DisposalCapEx
                                + model.v_C_StorageCapEx + + model.v_C_TreatmentCapEx + model.v_C_PipelineCapEx + model.v_C_Slack - model.v_R_TotalStorage)
        model.CostObjectiveFunction = Constraint(rule=CostObjectiveFunctionRule, doc='Cost objective function')

        # model.CostObjectiveFunction.pprint()

    ## Define reuse objective function ##

    elif model.config.objective == Objectives.reuse:  
        def ReuseObjectiveFunctionRule(model):
            return model.v_Z == -(model.v_F_TotalReused/model.p_beta_TotalProd) + 1/38446652 * (
                               model.v_C_TotalSourced + model.v_C_TotalDisposal + model.v_C_TotalTreatment + model.v_C_TotalReuse
                               + model.v_C_TotalPiping + model.v_C_TotalStorage + model.v_C_TotalTrucking + model.v_C_DisposalCapEx
                               + model.v_C_StorageCapEx + + model.v_C_TreatmentCapEx + model.v_C_PipelineCapEx + model.v_C_Slack - model.v_R_TotalStorage)
        model.ReuseObjectiveFunction = Constraint(rule=ReuseObjectiveFunctionRule, doc='Reuse objective function')

        # model.ReuseObjectiveFunction.pprint()

    else:
        raise Exception('objective not supported')

    ## Define constraints ##

    def CompletionsPadDemandBalanceRule(model,p,t):
        return model.p_gamma_Completions[p,t] == (sum(model.v_F_Piped[n,p,t] for n in model.s_N if model.p_NCA[n,p])
                                                + sum(model.v_F_Piped[p_tilde,p,t] for p_tilde in model.s_PP if model.p_PCA[p_tilde,p])
                                                + sum(model.v_F_Piped[s,p,t] for s in model.s_S if model.p_SCA[s,p])
                                                + sum(model.v_F_Piped[p_tilde,p,t] for p_tilde in model.s_CP if model.p_CCA[p_tilde,p])
                                                + sum(model.v_F_Piped[r,p,t] for r in model.s_R if model.p_RCA[r,p])
                                                + sum(model.v_F_Sourced[f,p,t] for f in model.s_F if model.p_FCA[f,p])
                                                + sum(model.v_F_Trucked[p_tilde,p,t] for p_tilde in model.s_PP if model.p_PCT[p_tilde,p])
                                                + sum(model.v_F_Trucked[p_tilde,p,t] for p_tilde in model.s_CP if model.p_CCT[p_tilde,p])
                                                + sum(model.v_F_Trucked[s,p,t] for s in model.s_S if model.p_SCT[s,p])
                                                + sum(model.v_F_Trucked[f,p,t] for f in model.s_F if model.p_FCT[f,p])
                                                + model.v_F_PadStorageOut[p,t] - model.v_F_PadStorageIn[p,t]
                                                + model.v_S_FracDemand[p,t]) 
    model.CompletionsPadDemandBalance = Constraint(model.s_CP,model.s_T,rule=CompletionsPadDemandBalanceRule, doc='Completions pad demand balance')

    # model.CompletionsPadDemandBalance['CP02','T24'].pprint()

    def CompletionsPadStorageBalanceRule(model,p,t):
        if t == 'T01':
            return (model.v_L_PadStorage[p,t] == 
                    model.p_lambda_PadStorage[p] + model.v_F_PadStorageIn[p,t] - model.v_F_PadStorageOut[p,t])
        else:
            return (model.v_L_PadStorage[p,t] == 
                    model.v_L_PadStorage[p,model.s_T.prev(t)] + model.v_F_PadStorageIn[p,t] - model.v_F_PadStorageOut[p,t])
    model.CompletionsPadStorageBalance = Constraint(model.s_CP,model.s_T,rule=CompletionsPadStorageBalanceRule, doc='Completions pad storage balance')

    # model.CompletionsPadStorageBalance.pprint()

    def CompletionsPadStorageCapacityRule(model,p,t):
        return (model.v_L_PadStorage[p,t] <= model.p_sigma_PadStorage[p])
    model.CompletionsPadStorageCapacity = Constraint(model.s_CP,model.s_T,rule=CompletionsPadStorageCapacityRule, doc='Completions pad storage capacity')

    # model.CompletionsPadStorageCapacity.pprint()

    def TerminalCompletionsPadStorageLevelRule(model,p,t):
        if t == model.s_T.last():
            return (model.v_L_PadStorage[p,t] <= model.p_theta_PadStorage[p])
        else:
            return Constraint.Skip
    model.TerminalCompletionsPadStorageLevel = Constraint(model.s_CP,model.s_T,rule=TerminalCompletionsPadStorageLevelRule, doc='Terminal completions pad storage level')

    # model.TerminalCompletionsPadStorageLevel.pprint()

    def FreshwaterSourcingCapacityRule(model,f,t):
        return (sum(model.v_F_Sourced[f,p,t] for p in model.s_CP if model.p_FCA[f,p]) +
                sum(model.v_F_Trucked[f,p,t] for p in model.s_CP if model.p_FCT[f,p])) <= model.p_sigma_Freshwater[f,t]
    model.FreshwaterSourcingCapacity = Constraint(model.s_F,model.s_T,rule=FreshwaterSourcingCapacityRule, doc='Freshwater sourcing capacity')

    # model.FreshwaterSourcingCapacity.pprint()

    def CompletionsPadTruckOffloadingCapacityRule(model,p,t):
        return (sum(model.v_F_Trucked[p_tilde,p,t] for p_tilde in model.s_PP if model.p_PCT[p_tilde,p]) + 
                sum(model.v_F_Trucked[s,p,t] for s in model.s_S if model.p_SCT[s,p]) +
                sum(model.v_F_Trucked[p_tilde,p,t] for p_tilde in model.s_CP if model.p_CCT[p_tilde,p]) + 
                sum(model.v_F_Trucked[f,p,t] for f in model.s_F if model.p_FCT[f,p])) <= model.p_sigma_OffloadingPad[p]
    model.CompletionsPadTruckOffloadingCapacity = Constraint(model.s_CP,model.s_T,rule=CompletionsPadTruckOffloadingCapacityRule, doc='Completions pad truck offloading capacity')

    # model.CompletionsPadTruckOffloadingCapacity.pprint()

    def StorageSiteTruckOffloadingCapacityRule(model,s,t):
        return (sum(model.v_F_Trucked[p,s,t] for p in model.s_PP if model.p_PST[p,s]) 
                + sum(model.v_F_Trucked[p,s,t] for p in model.s_CP if model.p_CST[p,s]) <= model.p_sigma_OffloadingStorage[s])
    model.StorageSiteTruckOffloadingCapacity = Constraint(model.s_S,model.s_T,rule=StorageSiteTruckOffloadingCapacityRule, doc='Storage site truck offloading capacity')

    # model.StorageSiteTruckOffloadingCapacity.pprint()

    def StorageSiteProcessingCapacityRule(model,s,t):
        return (sum(model.v_F_Piped[n,s,t] for n in model.s_N if model.p_NSA[n,s]) 
                + sum(model.v_F_Trucked[p,s,t] for p in model.s_PP if model.p_PST[p,s]) 
                + sum(model.v_F_Trucked[p,s,t] for p in model.s_CP if model.p_CST[p,s]) <= model.p_sigma_ProcessingStorage[s])
    model.StorageSiteProcessingCapacity = Constraint(model.s_S,model.s_T,rule=StorageSiteProcessingCapacityRule, doc='Storage site processing capacity')

    # model.StorageSiteProcessingCapacity.pprint()

    def ProductionPadSupplyBalanceRule(model,p,t):
        return (model.p_beta_Production[p,t] == sum(model.v_F_Piped[p,n,t] for n in model.s_N if model.p_PNA[p,n]) 
                + sum(model.v_F_Piped[p,p_tilde,t] for p_tilde in model.s_CP if model.p_PCA[p,p_tilde])
                + sum(model.v_F_Piped[p,p_tilde,t] for p_tilde in model.s_PP if model.p_PPA[p,p_tilde])
                + sum(model.v_F_Trucked[p,p_tilde,t] for p_tilde in model.s_CP if model.p_PCT[p,p_tilde])
                + sum(model.v_F_Trucked[p,k,t] for k in model.s_K if model.p_PKT[p,k])
                + sum(model.v_F_Trucked[p,s,t] for s in model.s_S if model.p_PST[p,s])
                + sum(model.v_F_Trucked[p,r,t] for r in model.s_R if model.p_PRT[p,r])
                + sum(model.v_F_Trucked[p,o,t] for o in model.s_O if model.p_POT[p,o])
                + model.v_S_Production[p,t])
    model.ProductionPadSupplyBalance = Constraint(model.s_PP,model.s_T,rule=ProductionPadSupplyBalanceRule, doc='Production pad supply balance')

    # model.ProductionPadSupplyBalance.pprint()

    def CompletionsPadSupplyBalanceRule(model,p,t):
        return (model.p_beta_Flowback[p,t] == sum(model.v_F_Piped[p,n,t] for n in model.s_N if model.p_CNA[p,n])
                + sum(model.v_F_Piped[p,p_tilde,t] for p_tilde in model.s_CP if model.p_CCA[p,p_tilde])
                + sum(model.v_F_Trucked[p,k,t] for k in model.s_K if model.p_CKT[p,k])
                + sum(model.v_F_Trucked[p,p_tilde,t] for p_tilde in model.s_CP if model.p_CCT[p,p_tilde])
                + sum(model.v_F_Trucked[p,s,t] for s in model.s_S if model.p_CST[p,s])
                + sum(model.v_F_Trucked[p,r,t] for r in model.s_R if model.p_CRT[p,r])
                + model.v_S_Flowback[p,t])
    model.CompletionsPadSupplyBalance = Constraint(model.s_CP,model.s_T,rule=CompletionsPadSupplyBalanceRule, doc='Completions pad supply balance (i.e. flowback balance')

    # model.CompletionsPadSupplyBalance.pprint()

    def NetworkNodeBalanceRule(model,n,t):
        return (sum(model.v_F_Piped[p,n,t] for p in model.s_PP if model.p_PNA[p,n])
                + sum(model.v_F_Piped[p,n,t] for p in model.s_CP if model.p_CNA[p,n])
                + sum(model.v_F_Piped[n_tilde,n,t] for n_tilde in model.s_N if model.p_NNA[n_tilde,n]) 
                + sum(model.v_F_Piped[s,n,t] for s in model.s_S if model.p_SNA[s,n]) ==
                sum(model.v_F_Piped[n,n_tilde,t] for n_tilde in model.s_N if model.p_NNA[n,n_tilde])
                + sum(model.v_F_Piped[n,p,t] for p in model.s_CP if model.p_NCA[n,p])
                + sum(model.v_F_Piped[n,k,t] for k in model.s_K if model.p_NKA[n,k])
                + sum(model.v_F_Piped[n,r,t] for r in model.s_R if model.p_NRA[n,r])
                + sum(model.v_F_Piped[n,s,t] for s in model.s_S if model.p_NSA[n,s])
                + sum(model.v_F_Piped[n,o,t] for o in model.s_O if model.p_NOA[n,o]))
    model.NetworkBalance = Constraint(model.s_N,model.s_T,rule=NetworkNodeBalanceRule, doc='Network node balance')

    # model.NetworkBalance['N12','T05'].pprint()

    def BidirectionalFlowRule1(model,l,l_tilde,t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip 
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip                 
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l,l_tilde]:
                return (model.vb_y_Flow[l,l_tilde,t] + model.vb_y_Flow[l_tilde,l,t] == 1)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    model.BidirectionalFlow1 = Constraint(model.s_L,model.s_L,model.s_T,rule=BidirectionalFlowRule1, doc='Bi-directional flow')

    # model.BidirectionalFlow1.pprint()

    def BidirectionalFlowRule2(model,l,l_tilde,t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l,l_tilde]:
                return (model.v_F_Piped[l,l_tilde,t] <= model.vb_y_Flow[l,l_tilde,t] * model.p_M_Flow)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    model.BidirectionalFlow2 = Constraint(model.s_L,model.s_L,model.s_T,rule=BidirectionalFlowRule2, doc='Bi-directional flow')

    # model.BidirectionalFlow2.pprint()

    def StorageSiteBalanceRule(model,s,t):
        if t == 'T01':
            return (model.v_L_Storage[s,t] == model.p_lambda_Storage[s] +
                    sum(model.v_F_Piped[n,s,t] for n in model.s_N if model.p_NSA[n,s]) + 
                    sum(model.v_F_Trucked[p,s,t] for p in model.s_PP if model.p_PST[p,s]) + 
                    sum(model.v_F_Trucked[p,s,t] for p in model.s_CP if model.p_CST[p,s]) -
                    sum(model.v_F_Piped[s,n,t] for n in model.s_N if model.p_SNA[s,n]) -
                    sum(model.v_F_Piped[s,p,t] for p in model.s_CP if model.p_SCA[s,p]) -
                    sum(model.v_F_Piped[s,k,t] for k in model.s_K if model.p_SKA[s,k]) - 
                    sum(model.v_F_Piped[s,r,t] for r in model.s_R if model.p_SRA[s,r]) - 
                    sum(model.v_F_Piped[s,o,t] for o in model.s_O if model.p_SOA[s,o]) - 
                    sum(model.v_F_Trucked[s,p,t] for p in model.s_CP if model.p_SCT[s,p]) - 
                    sum(model.v_F_Trucked[s,k,t] for k in model.s_K if model.p_SKT[s,k]))
        else:
            return (model.v_L_Storage[s,t] == model.v_L_Storage[s,model.s_T.prev(t)] +
                    sum(model.v_F_Piped[n,s,t] for n in model.s_N if model.p_NSA[n,s]) + 
                    sum(model.v_F_Trucked[p,s,t] for p in model.s_PP if model.p_PST[p,s]) + 
                    sum(model.v_F_Trucked[p,s,t] for p in model.s_CP if model.p_CST[p,s]) -
                    sum(model.v_F_Piped[s,n,t] for n in model.s_N if model.p_SNA[s,n]) -
                    sum(model.v_F_Piped[s,p,t] for p in model.s_CP if model.p_SCA[s,p]) -
                    sum(model.v_F_Piped[s,k,t] for k in model.s_K if model.p_SKA[s,k]) - 
                    sum(model.v_F_Piped[s,r,t] for r in model.s_R if model.p_SRA[s,r]) - 
                    sum(model.v_F_Piped[s,o,t] for o in model.s_O if model.p_SOA[s,o]) - 
                    sum(model.v_F_Trucked[s,p,t] for p in model.s_CP if model.p_SCT[s,p]) - 
                    sum(model.v_F_Trucked[s,k,t] for k in model.s_K if model.p_SKT[s,k]))
    model.StorageSiteBalance = Constraint(model.s_S,model.s_T,rule=StorageSiteBalanceRule, doc='Storage site balance rule')

    # model.StorageSiteBalance.pprint()

    def TerminalStorageLevelRule(model,s,t):
        if t == model.s_T.last():
            return (model.v_L_Storage[s,t] <= model.p_theta_Storage[s])
        else:
            return Constraint.Skip
    model.TerminalStorageLevel = Constraint(model.s_S,model.s_T,rule=TerminalStorageLevelRule, doc='Terminal storage site level')

    # model.TerminalStorageLevel.pprint()    

    def PipelineCapacityExpansionRule(model,l,l_tilde):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip                
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l,l_tilde]:
                return (model.v_F_Capacity[l,l_tilde] == model.p_sigma_Pipeline[l,l_tilde] + 
                        sum(model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l,l_tilde,d]) for d in model.s_D) 
                        + model.v_S_PipelineCapacity[l,l_tilde])
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip  
    model.PipelineCapacityExpansion = Constraint(model.s_L,model.s_L,rule=PipelineCapacityExpansionRule, doc='Pipeline capacity construction/expansion')

    # model.PipelineCapacityExpansion['N03','N04'].pprint()

    # def BiDirectionalPipelineCapacityRestrictionRule(model,l,l_tilde,d):
    #     return (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d] <= 1)
    # model.BiDirectionalPipelineCapacityRestriction = Constraint(model.s_L,model.s_L,model.s_D,rule=BiDirectionalPipelineCapacityRestrictionRule, doc='Bi-directional pipeline capacity restriction')

    # model.BiDirectionalPipelineCapacityRestriction.pprint()

    def PipelineCapacityRule(model,l,l_tilde,t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l,l_tilde]:
                return model.v_F_Piped[l,l_tilde,t] <= model.v_F_Capacity[l,l_tilde]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    model.PipelineCapacity = Constraint(model.s_L,model.s_L,model.s_T,rule=PipelineCapacityRule, doc='Pipeline capacity')

    # model.PipelineCapacity['R01','CP01','T01'].pprint()
    
    def StorageCapacityExpansionRule(model,s):
        return (model.v_X_Capacity[s] == 
                model.p_sigma_Storage[s] + sum(model.p_delta_Storage[c] * model.vb_y_Storage[s,c] for c in model.s_C) + model.v_S_StorageCapacity[s])
    model.StorageCapacityExpansion = Constraint(model.s_S,rule=StorageCapacityExpansionRule, doc='Storage capacity construction/expansion')

    # model.StorageCapacityExpansion.pprint()

    def StorageCapacityRule(model,s,t):
        return model.v_L_Storage[s,t] <= model.v_X_Capacity[s] 
    model.StorageCapacity = Constraint(model.s_S,model.s_T,rule=StorageCapacityRule, doc='Storage capacity')

    # model.StorageCapacity.pprint()

    def DisposalCapacityExpansionRule(model,k):
        return (model.v_D_Capacity[k] ==
                model.p_sigma_Disposal[k] + sum(model.p_delta_Disposal[i] * model.vb_y_Disposal[k,i] for i in model.s_I) + model.v_S_DisposalCapacity[k])
    model.DisposalCapacityExpansion = Constraint(model.s_K,rule=DisposalCapacityExpansionRule, doc='Disposal capacity construction/expansion')

    # model.DisposalCapacityExpansion1.pprint()

    def DisposalCapacityRule(model,k,t):
        return (sum(model.v_F_Piped[n,k,t] for n in model.s_N if model.p_NKA[n,k]) +
                sum(model.v_F_Piped[s,k,t] for s in model.s_S if model.p_SKA[s,k]) +
                sum(model.v_F_Trucked[s,k,t] for s in model.s_S if model.p_SKT[s,k]) +
                sum(model.v_F_Trucked[p,k,t] for p in model.s_PP if model.p_PKT[p,k]) +
                sum(model.v_F_Trucked[p,k,t] for p in model.s_CP if model.p_CKT[p,k]) +
                sum(model.v_F_Trucked[r,k,t] for r in model.s_R if model.p_RKT[r,k])
                <= model.v_D_Capacity[k])
    model.DisposalCapacity = Constraint(model.s_K,model.s_T,rule=DisposalCapacityRule, doc='Disposal capacity')

    # model.DisposalCapacity.pprint()

    def TreatmentCapacityExpansionRule(model,r):
        return (model.v_T_Capacity[r] == 
                model.p_sigma_Treatment[r] + sum(model.p_delta_Treatment[j] * model.vb_y_Treatment[r,j] for j in model.s_J) + model.v_S_TreatmentCapacity[r])
    model.TreatmentCapacityExpansion = Constraint(model.s_R,rule=TreatmentCapacityExpansionRule, doc='Treatment capacity construction/expansion')

    # model.TreatmentCapacityExpansion.pprint()

    def TreatmentCapacityRule(model,r,t):
        return (sum(model.v_F_Piped[n,r,t] for n in model.s_N if model.p_NRA[n,r]) + 
                sum(model.v_F_Piped[s,r,t] for s in model.s_S if model.p_SRA[s,r]) +
                sum(model.v_F_Trucked[p,r,t] for p in model.s_PP if model.p_PRT[p,r]) + 
                sum(model.v_F_Trucked[p,r,t] for p in model.s_CP if model.p_CRT[p,r])
                <= model.v_T_Capacity[r])
    model.TreatmentCapacity = Constraint(model.s_R,model.s_T,rule=TreatmentCapacityRule, doc='Treatment capacity')

    # model.TreatmentCapacity.pprint()

    def TreatmentBalanceRule(model,r,t):
        return (model.p_epsilon_Treatment[r] * (sum(model.v_F_Piped[n,r,t] for n in model.s_N if model.p_NRA[n,r]) + 
                sum(model.v_F_Piped[s,r,t] for s in model.s_S if model.p_SRA[s,r]) +
                sum(model.v_F_Trucked[p,r,t] for p in model.s_PP if model.p_PRT[p,r]) + 
                sum(model.v_F_Trucked[p,r,t] for p in model.s_CP if model.p_CRT[p,r]))
                == sum(model.v_F_Piped[r,p,t] for p in model.s_CP if model.p_RCA[r,p]))
    model.TreatmentBalance = Constraint(model.s_R,model.s_T,rule=TreatmentBalanceRule, doc='Treatment balance')

    # model.TreatmentBalance.pprint()

    def BeneficialReuseCapacityRule(model,o,t):
        return (sum(model.v_F_Piped[n,o,t] for n in model.s_N if model.p_NOA[n,o]) + 
                sum(model.v_F_Piped[s,o,t] for s in model.s_S if model.p_SOA[s,o]) + 
                sum(model.v_F_Trucked[p,o,t] for p in model.s_PP if model.p_POT[p,o]) 
                <= model.p_sigma_Reuse[o] + model.v_S_ReuseCapacity[o])
    model.BeneficialReuseCapacity = Constraint(model.s_O,model.s_T,rule=BeneficialReuseCapacityRule, doc='Beneficial reuse capacity')

    # model.BeneficialReuseCapacity.pprint()

    # COMMENT: Beneficial reuse capacity constraint has not been tested yet 

    def FreshSourcingCostRule(model,f,p,t):
            if f in model.s_F and p in model.s_CP:
                if model.p_FCA[f,p]:
                    return (model.v_C_Sourced[f,p,t] == (model.v_F_Sourced[f,p,t] + model.v_F_Trucked[f,p,t])* model.p_pi_Sourcing[f])
                elif model.p_FCT[f,p]:
                    return (model.v_C_Sourced[f,p,t] == (model.v_F_Sourced[f,p,t] + model.v_F_Trucked[f,p,t])* model.p_pi_Sourcing[f])
                else:
                    return Constraint.Skip
            else:
                return Constraint.Skip
#                    return (model.v_C_Sourced[f,p,t] == (model.v_F_Sourced[f,p,t] + model.v_F_Trucked[f,p,t])* model.p_pi_Sourcing[f])
    model.FreshSourcingCost = Constraint(model.s_F,model.s_CP,model.s_T,rule=FreshSourcingCostRule, doc='Fresh sourcing cost')

    # model.FreshSourcingCost.pprint()

    def TotalFreshSourcingCostRule(model):
            return model.v_C_TotalSourced == sum(sum(sum(model.v_C_Sourced[f,p,t] for f in model.s_F if model.p_FCA[f,p]) for p in model.s_CP)for t in model.s_T)
    model.TotalFreshSourcingCost = Constraint(rule=TotalFreshSourcingCostRule, doc='Total fresh sourcing cost')

    # model.TotalFreshSourcingCost.pprint()

    def TotalFreshSourcingVolumeRule(model):
            return (model.v_F_TotalSourced == 
            sum(sum(sum(model.v_F_Sourced[f,p,t] for f in model.s_F if model.p_FCA[f,p]) for p in model.s_CP) for t in model.s_T) +
            sum(sum(sum(model.v_F_Trucked[f,p,t] for f in model.s_F if model.p_FCT[f,p]) for p in model.s_CP) for t in model.s_T))
    model.TotalFreshSourcingVolume = Constraint(rule=TotalFreshSourcingVolumeRule, doc='Total fresh sourcing volume')

    # model.TotalFreshSourcingVolume.pprint()

    def DisposalCostRule(model,k,t):
        return (model.v_C_Disposal[k,t] == 
                (sum(model.v_F_Piped[n,k,t] for n in model.s_N if model.p_NKA[n,k]) 
                + sum(model.v_F_Piped[r,k,t] for r in model.s_R if model.p_RKA[r,k])
                + sum(model.v_F_Piped[s,k,t] for s in model.s_S if model.p_SKA[s,k])
                + sum(model.v_F_Trucked[p,k,t] for p in model.s_PP if model.p_PKT[p,k])
                + sum(model.v_F_Trucked[p,k,t] for p in model.s_CP if model.p_CKT[p,k]) 
                + sum(model.v_F_Trucked[s,k,t] for s in model.s_S if model.p_SKT[s,k])
                + sum(model.v_F_Trucked[r,k,t] for r in model.s_R if model.p_RKT[r,k])
                )* model.p_pi_Disposal[k])
    model.DisposalCost = Constraint(model.s_K,model.s_T,rule=DisposalCostRule, doc='Disposal cost')

    # model.DisposalCost.pprint()

    def TotalDisposalCostRule(model):
        return model.v_C_TotalDisposal == sum(sum(model.v_C_Disposal[k,t] for k in model.s_K) for t in model.s_T)
    model.TotalDisposalCost = Constraint(rule=TotalDisposalCostRule, doc='Total disposal cost')

    # model.TotalDisposalCost.pprint()

    def TotalDisposalVolumeRule(model):
        return model.v_F_TotalDisposed == (sum(sum(sum(model.v_F_Piped[l,k,t] for l in model.s_L) for k in model.s_K) for t in model.s_T) +
                                           sum(sum(sum(model.v_F_Trucked[l,k,t] for l in model.s_L) for k in model.s_K) for t in model.s_T))
    model.TotalDisposalVolume = Constraint(rule=TotalDisposalVolumeRule, doc='Total disposal volume')

    # model.TotalDisposalVolume.pprint()

    def TreatmentCostRule(model,r,t):
        return (model.v_C_Treatment[r,t] ==
            ( sum(model.v_F_Piped[n,r,t] for n in model.s_N if model.p_NRA[n,r])
            + sum(model.v_F_Piped[s,r,t] for s in model.s_S if model.p_SRA[s,r])
            + sum(model.v_F_Trucked[p,r,t] for p in model.s_PP if model.p_PRT[p,r])
            + sum(model.v_F_Trucked[p,r,t] for p in model.s_CP if model.p_CRT[p,r])
            ) * model.p_pi_Treatment[r])
    model.TreatmentCost = Constraint(model.s_R,model.s_T,rule=TreatmentCostRule, doc='Treatment cost')        

    # model.TreatmentCost.pprint()

    def TotalTreatmentCostRule(model):
        return model.v_C_TotalTreatment == sum(sum(model.v_C_Treatment[r,t] for r in model.s_R) for t in model.s_T)
    model.TotalTreatmentCost = Constraint(rule=TotalTreatmentCostRule, doc='Total treatment cost')

    # model.TotalTreatmentCost.pprint()

    def CompletionsReuseCostRule(model,p,t,):
        return model.v_C_Reuse[p,t] == ((sum(model.v_F_Piped[n,p,t] for n in model.s_N if model.p_NCA[n,p])
            + sum(model.v_F_Piped[p_tilde,p,t] for p_tilde in model.s_PP if model.p_PCA[p_tilde,p])    
            + sum(model.v_F_Piped[p_tilde,p,t] for p_tilde in model.s_CP if model.p_CCA[p_tilde,p])
            + sum(model.v_F_Piped[s,p,t] for s in model.s_S if model.p_SCA[s,p])
            + sum(model.v_F_Piped[r,p,t] for r in model.s_R if model.p_RCA[r,p])
            + sum(model.v_F_Trucked[p_tilde,p,t] for p_tilde in model.s_PP if model.p_PCT[p_tilde,p])
            + sum(model.v_F_Trucked[p_tilde,p,t] for p_tilde in model.s_CP if model.p_CCT[p_tilde,p])
            + sum(model.v_F_Trucked[s,p,t] for s in model.s_S if model.p_SCT[s,p])
            )* model.p_pi_Reuse[p])
    model.CompletionsReuseCost = Constraint(model.s_CP,model.s_T,rule=CompletionsReuseCostRule, doc='Reuse completions cost')

    # model.CompletionsReuseCost.pprint()

    def TotalCompletionsReuseCostRule(model):
        return model.v_C_TotalReuse == sum(sum(model.v_C_Reuse[p,t] for p in model.s_CP) for t in model.s_T)
    model.TotalCompletionsReuseCost = Constraint(rule=TotalCompletionsReuseCostRule, doc='Total completions reuse cost')

    def TotalReuseVolumeRule(model):
        return (model.v_F_TotalReused == sum(sum(
                sum(model.v_F_Piped[n,p,t] for n in model.s_N if model.p_NCA[n,p])
                + sum(model.v_F_Piped[p_tilde,p,t] for p_tilde in model.s_PP if model.p_PCA[p_tilde,p])    
                + sum(model.v_F_Piped[p_tilde,p,t] for p_tilde in model.s_CP if model.p_CCA[p_tilde,p])
                + sum(model.v_F_Piped[s,p,t] for s in model.s_S if model.p_SCA[s,p])
                + sum(model.v_F_Piped[r,p,t] for r in model.s_R if model.p_RCA[r,p])
                + sum(model.v_F_Trucked[p_tilde,p,t] for p_tilde in model.s_PP if model.p_PCT[p_tilde,p])
                + sum(model.v_F_Trucked[p_tilde,p,t] for p_tilde in model.s_CP if model.p_CCT[p_tilde,p])
                + sum(model.v_F_Trucked[s,p,t] for s in model.s_S if model.p_SCT[s,p]) for p in model.s_CP) for t in model.s_T))
    model.TotalReuseVolume = Constraint(rule=TotalReuseVolumeRule, doc='Total reuse volume')

    # model.TotalCompletionsReuseCost.pprint()

    def PipingCostRule(model,l,l_tilde,t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_CP:
            if model.p_CCA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Sourced[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l,l_tilde]:
                return model.v_C_Piped[l,l_tilde,t] == model.v_F_Piped[l,l_tilde,t] * model.p_pi_Pipeline[l,l_tilde]
            else: 
                return Constraint.Skip    
        else:
            return Constraint.Skip 
    model.PipingCost = Constraint(model.s_L,model.s_L,model.s_T,rule=PipingCostRule, doc='Piping cost')

    # model.PipingCost.pprint()

    def TotalPipingCostRule(model):
        return model.v_C_TotalPiping == (sum(
            sum(sum(model.v_C_Piped[p,p_tilde,t] for p in model.s_PP if model.p_PCA[p,p_tilde]) for p_tilde in model.s_CP)
            + sum(sum(model.v_C_Piped[p,n,t] for p in model.s_PP if model.p_PNA[p,n]) for n in model.s_N) 
            + sum(sum(model.v_C_Piped[p,p_tilde,t] for p in model.s_PP if model.p_PPA[p,p_tilde]) for p_tilde in model.s_PP)
            + sum(sum(model.v_C_Piped[p,p_tilde,t] for p in model.s_CP if model.p_CCA[p,p_tilde]) for p_tilde in model.s_CP)
            + sum(sum(model.v_C_Piped[p,n,t] for p in model.s_CP if model.p_CNA[p,n]) for n in model.s_N)
            + sum(sum(model.v_C_Piped[n,n_tilde,t] for n in model.s_N if model.p_NNA[n,n_tilde]) for n_tilde in model.s_N)
            + sum(sum(model.v_C_Piped[n,p,t] for n in model.s_N if model.p_NCA[n,p]) for p in model.s_CP)
            + sum(sum(model.v_C_Piped[n,k,t] for n in model.s_N if model.p_NKA[n,k]) for k in model.s_K)
            + sum(sum(model.v_C_Piped[n,s,t] for n in model.s_N if model.p_NSA[n,s]) for s in model.s_S)
            + sum(sum(model.v_C_Piped[n,r,t] for n in model.s_N if model.p_NRA[n,r]) for r in model.s_R)
            + sum(sum(model.v_C_Piped[n,o,t] for n in model.s_N if model.p_NOA[n,o]) for o in model.s_O)
            + sum(sum(model.v_C_Piped[f,p,t] for f in model.s_F if model.p_FCA[f,p]) for p in model.s_CP)
            + sum(sum(model.v_C_Piped[r,n,t] for r in model.s_R if model.p_RNA[r,n]) for n in model.s_N)
            + sum(sum(model.v_C_Piped[r,p,t] for r in model.s_R if model.p_RCA[r,p]) for p in model.s_CP)
            + sum(sum(model.v_C_Piped[r,k,t] for r in model.s_R if model.p_RKA[r,k]) for k in model.s_K)
            + sum(sum(model.v_C_Piped[s,n,t] for s in model.s_S if model.p_SNA[s,n]) for n in model.s_N)
            + sum(sum(model.v_C_Piped[s,r,t] for s in model.s_S if model.p_SRA[s,r]) for r in model.s_R)
            + sum(sum(model.v_C_Piped[s,o,t] for s in model.s_S if model.p_SOA[s,o]) for o in model.s_O)
            + sum(sum(model.v_C_Piped[f,p,t] for f in model.s_F if model.p_FCA[f,p]) for p in model.s_CP)
            for t in model.s_T))
    model.TotalPipingCost = Constraint(rule=TotalPipingCostRule, doc='Total piping cost')

    # model.TotalPipingCost.pprint()

    def StorageDepositCostRule(model,s,t):
        return model.v_C_Storage[s,t] == ((sum(model.v_F_Piped[n,s,t] for n in model.s_N if model.p_NSA[n,s])
            + sum(model.v_F_Trucked[p,s,t] for p in model.s_CP if model.p_CST[p,s])) 
            * model.p_pi_Storage[s])
    model.StorageDepositCost = Constraint(model.s_S,model.s_T,rule=StorageDepositCostRule, doc='Storage deposit cost')

    # model.StorageDepositCost.pprint()

    def TotalStorageCostRule(model):
        return model.v_C_TotalStorage == sum(sum(model.v_C_Storage[s,t] for s in model.s_S) for t in model.s_T)
    model.TotalStorageCost = Constraint(rule=TotalStorageCostRule, doc='Total storage deposit cost')

    # model.TotalStorageCost.pprint()

    def StorageWithdrawalCreditRule(model,s,t):
        return model.v_R_Storage[s,t] == ((sum(model.v_F_Piped[s,n,t] for n in model.s_N if model.p_SNA[s,n])
            + sum(model.v_F_Piped[s,p,t] for p in model.s_CP if model.p_SCA[s,p])
            + sum(model.v_F_Piped[s,k,t] for k in model.s_K if model.p_SKA[s,k])
            + sum(model.v_F_Piped[s,r,t] for r in model.s_R if model.p_SRA[s,r])
            + sum(model.v_F_Piped[s,o,t] for o in model.s_O if model.p_SOA[s,o])
            + sum(model.v_F_Trucked[s,p,t] for p in model.s_CP if model.p_SCT[s,p])
            + sum(model.v_F_Trucked[s,k,t] for k in model.s_K if model.p_SKT[s,k])
            ) * model.p_rho_Storage[s])
    model.StorageWithdrawalCredit = Constraint(model.s_S,model.s_T,rule=StorageWithdrawalCreditRule, doc='Storage withdrawal credit')

    # model.StorageWithdrawalCredit.pprint()

    def TotalStorageWithdrawalCreditRule(model):
        return model.v_R_TotalStorage == sum(sum(model.v_R_Storage[s,t] for s in model.s_S) for t in model.s_T)
    model.TotalStorageWithdrawalCredit = Constraint(rule=TotalStorageWithdrawalCreditRule, doc='Total storage withdrawal credit')

    # model.TotalStorageWithdrawalCredit.pprint()

    def TruckingCostRule(model,l,l_tilde,t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_K:
            if model.p_PKT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip   
        elif l in model.s_PP and l_tilde in model.s_S:
            if model.p_PST[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip            
        elif l in model.s_PP and l_tilde in model.s_R:
            if model.p_PRT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_O:
            if model.p_POT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_K:
            if model.p_CKT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_S:
            if model.p_CST[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_R:
            if model.p_CRT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_CP:
            if model.p_CCT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKT[l,l_tilde]:
                return model.v_C_Trucked[l,l_tilde,t] == model.v_F_Trucked[l,l_tilde,t] * 1/model.p_delta_Truck * model.p_tau_Trucking[l,l_tilde] * model.p_pi_Trucking[l]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    model.TruckingCost = Constraint(model.s_L,model.s_L,model.s_T,rule=TruckingCostRule, doc='Trucking cost')

    # model.TruckingCost.pprint()

    def TotalTruckingCostRule(model):
        return model.v_C_TotalTrucking == (sum(
            sum(sum(model.v_C_Trucked[p,p_tilde,t] for p in model.s_PP if model.p_PCT[p,p_tilde]) for p_tilde in model.s_CP) 
            + sum(sum(model.v_C_Trucked[p,k,t] for p in model.s_PP if model.p_PKT[p,k]) for k in model.s_K)
            + sum(sum(model.v_C_Trucked[p,s,t] for p in model.s_PP if model.p_PST[p,s]) for s in model.s_S)
            + sum(sum(model.v_C_Trucked[p,r,t] for p in model.s_PP if model.p_PRT[p,r]) for r in model.s_R)
            + sum(sum(model.v_C_Trucked[p,o,t] for p in model.s_PP if model.p_POT[p,o]) for o in model.s_O)
            + sum(sum(model.v_C_Trucked[p,k,t] for p in model.s_CP if model.p_CKT[p,k]) for k in model.s_K)
            + sum(sum(model.v_C_Trucked[p,s,t] for p in model.s_CP if model.p_CST[p,s]) for s in model.s_S)
            + sum(sum(model.v_C_Trucked[p,r,t] for p in model.s_CP if model.p_CRT[p,r]) for r in model.s_R)
            + sum(sum(model.v_C_Trucked[p,p_tilde,t] for p in model.s_CP if model.p_CCT[p,p_tilde]) for p_tilde in model.s_CP)
            + sum(sum(model.v_C_Trucked[s,p,t] for s in model.s_S if model.p_SCT[s,p]) for p in model.s_CP)
            + sum(sum(model.v_C_Trucked[s,k,t] for s in model.s_S if model.p_SKT[s,k]) for k in model.s_K)
            + sum(sum(model.v_C_Trucked[r,k,t] for r in model.s_R if model.p_RKT[r,k]) for k in model.s_K)
            + sum(sum(model.v_C_Trucked[f,p,t] for f in model.s_F if model.p_FCT[f,p]) for p in model.s_CP)
            for t in model.s_T))
    model.TotalTruckingCost = Constraint(rule=TotalTruckingCostRule, doc='Total trucking cost')

    # model.TotalTruckingCost.pprint()

    def TotalTruckingVolumeRule(model):
        return (model.v_F_TotalTrucked == sum(
            sum(sum(model.v_F_Trucked[p,p_tilde,t] for p in model.s_PP if model.p_PCT[p,p_tilde]) for p_tilde in model.s_CP) 
            + sum(sum(model.v_F_Trucked[p,k,t] for p in model.s_PP if model.p_PKT[p,k]) for k in model.s_K)
            + sum(sum(model.v_F_Trucked[p,s,t] for p in model.s_PP if model.p_PST[p,s]) for s in model.s_S)
            + sum(sum(model.v_F_Trucked[p,r,t] for p in model.s_PP if model.p_PRT[p,r]) for r in model.s_R)
            + sum(sum(model.v_F_Trucked[p,o,t] for p in model.s_PP if model.p_POT[p,o]) for o in model.s_O)
            + sum(sum(model.v_F_Trucked[p,k,t] for p in model.s_CP if model.p_CKT[p,k]) for k in model.s_K)
            + sum(sum(model.v_F_Trucked[p,s,t] for p in model.s_CP if model.p_CST[p,s]) for s in model.s_S)
            + sum(sum(model.v_F_Trucked[p,r,t] for p in model.s_CP if model.p_CRT[p,r]) for r in model.s_R)
            + sum(sum(model.v_F_Trucked[p,p_tilde,t] for p in model.s_CP if model.p_CCT[p,p_tilde]) for p_tilde in model.s_CP)
            + sum(sum(model.v_F_Trucked[s,p,t] for s in model.s_S if model.p_SCT[s,p]) for p in model.s_CP)
            + sum(sum(model.v_F_Trucked[s,k,t] for s in model.s_S if model.p_SKT[s,k]) for k in model.s_K)
            + sum(sum(model.v_F_Trucked[r,k,t] for r in model.s_R if model.p_RKT[r,k]) for k in model.s_K)
            + sum(sum(model.v_F_Trucked[f,p,t] for f in model.s_F if model.p_FCT[f,p]) for p in model.s_CP)
            for t in model.s_T))
    model.TotalTruckingVolume = Constraint(rule=TotalTruckingVolumeRule, doc='Total trucking volume')

    def DisposalExpansionCapExRule(model):
        return model.v_C_DisposalCapEx == sum(sum(model.vb_y_Disposal[k,i] * model.p_kappa_Disposal[k,i] * model.p_delta_Disposal[i] for i in model.s_I) for k in model.s_K)
    model.DisposalExpansionCapEx = Constraint(rule=DisposalExpansionCapExRule, doc='Disposal construction or capacity expansion cost')

    # model.DisposalExpansionCapEx.pprint()

    def StorageExpansionCapExRule(model):
        return model.v_C_StorageCapEx == sum(sum(model.vb_y_Storage[s,c] * model.p_kappa_Storage[s,c] * model.p_delta_Storage[c] for s in model.s_S) for c in model.s_C)
    model.StorageExpansionCapEx = Constraint(rule=StorageExpansionCapExRule, doc='Storage construction or capacity expansion cost')

    # model.StorageExpansionCapEx.pprint()

    def TreatmentExpansionCapExRule(model):
        return model.v_C_TreatmentCapEx == sum(sum(model.vb_y_Treatment[r,j] * model.p_kappa_Treatment[r,j] * model.p_delta_Treatment[j] for r in model.s_R) for j in model.s_J)
    model.TreatmentExpansionCapEx = Constraint(rule=TreatmentExpansionCapExRule, doc='Treatment construction or capacity expansion cost')

    # model.TreatmentExpansionCapEx.pprint()

    def PipelineExpansionCapExRule(model):
        return model.v_C_PipelineCapEx == (
            sum(sum(sum(model.vb_y_Pipeline[p,p_tilde,d] * model.p_kappa_Pipeline[p,p_tilde,d] * model.p_delta_Pipeline[d] for p in model.s_PP if model.p_PCA[p,p_tilde]) for p_tilde in model.s_CP) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[p,n,d] * model.p_kappa_Pipeline[p,n,d] * model.p_delta_Pipeline[d] for p in model.s_PP if model.p_PNA[p,n]) for n in model.s_N) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[p,p_tilde,d] * model.p_kappa_Pipeline[p,p_tilde,d] * model.p_delta_Pipeline[d] for p in model.s_PP if model.p_PPA[p,p_tilde]) for p_tilde in model.s_PP) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[p,n,d] * model.p_kappa_Pipeline[p,n,d] * model.p_delta_Pipeline[d] for p in model.s_CP if model.p_CNA[p,n]) for n in model.s_N) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[n,n_tilde,d] * model.p_kappa_Pipeline[n,n_tilde,d] * model.p_delta_Pipeline[d] for n in model.s_N if model.p_NNA[n,n_tilde]) for n_tilde in model.s_N) for d in model.s_D) +
            sum(sum(sum(model.vb_y_Pipeline[n,p,d] * model.p_kappa_Pipeline[n,p,d] * model.p_delta_Pipeline[d] for n in model.s_N if model.p_NCA[n,p]) for p in model.s_CP) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[n,k,d] * model.p_kappa_Pipeline[n,k,d] * model.p_delta_Pipeline[d] for n in model.s_N if model.p_NKA[n,k]) for k in model.s_K) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[n,s,d] * model.p_kappa_Pipeline[n,s,d] * model.p_delta_Pipeline[d] for n in model.s_N if model.p_NSA[n,s]) for s in model.s_S) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[n,r,d] * model.p_kappa_Pipeline[n,r,d] * model.p_delta_Pipeline[d] for n in model.s_N if model.p_NRA[n,r]) for r in model.s_R) for d in model.s_D) +
            sum(sum(sum(model.vb_y_Pipeline[n,o,d] * model.p_kappa_Pipeline[n,o,d] * model.p_delta_Pipeline[d] for n in model.s_N if model.p_NOA[n,o]) for o in model.s_O) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[f,p,d] * model.p_kappa_Pipeline[f,p,d] * model.p_delta_Pipeline[d] for f in model.s_F if model.p_FCA[f,p]) for p in model.s_CP) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[r,n,d] * model.p_kappa_Pipeline[r,n,d] * model.p_delta_Pipeline[d] for r in model.s_R if model.p_RNA[r,n]) for n in model.s_N) for d in model.s_D) +
            sum(sum(sum(model.vb_y_Pipeline[r,p,d] * model.p_kappa_Pipeline[r,p,d] * model.p_delta_Pipeline[d] for r in model.s_R if model.p_RCA[r,p]) for p in model.s_CP) for d in model.s_D) +
            sum(sum(sum(model.vb_y_Pipeline[r,k,d] * model.p_kappa_Pipeline[r,k,d] * model.p_delta_Pipeline[d] for r in model.s_R if model.p_RKA[r,k]) for k in model.s_K) for d in model.s_D) +
            sum(sum(sum(model.vb_y_Pipeline[s,n,d] * model.p_kappa_Pipeline[s,n,d] * model.p_delta_Pipeline[d] for s in model.s_S if model.p_SNA[s,n]) for n in model.s_N) for d in model.s_D) +
            sum(sum(sum(model.vb_y_Pipeline[s,p,d] * model.p_kappa_Pipeline[s,p,d] * model.p_delta_Pipeline[d] for s in model.s_S if model.p_SCA[s,p]) for p in model.s_CP) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[s,k,d] * model.p_kappa_Pipeline[s,k,d] * model.p_delta_Pipeline[d] for s in model.s_S if model.p_SKA[s,k]) for k in model.s_K) for d in model.s_D) + 
            sum(sum(sum(model.vb_y_Pipeline[s,r,d] * model.p_kappa_Pipeline[s,r,d] * model.p_delta_Pipeline[d] for s in model.s_S if model.p_SRA[s,r]) for r in model.s_R) for d in model.s_D) +
            sum(sum(sum(model.vb_y_Pipeline[s,o,d] * model.p_kappa_Pipeline[s,o,d] * model.p_delta_Pipeline[d] for s in model.s_S if model.p_SOA[s,o]) for o in model.s_O) for d in model.s_D)
            )
    model.PipelineExpansionCapEx = Constraint(rule=PipelineExpansionCapExRule, doc='Pipeline construction or capacity expansion cost')

    # model.PipelineExpansionCapEx.pprint()

    def SlackCostsRule(model):
        return model.v_C_Slack == (
            sum(sum(model.v_S_FracDemand[p,t] * model.p_psi_FracDemand for p in model.s_CP) for t in model.s_T) +
            sum(sum(model.v_S_Production[p,t] * model.p_psi_Production for p in model.s_PP) for t in model.s_T) +
            sum(sum(model.v_S_Flowback[p,t] * model.p_psi_Flowback for p in model.s_CP) for t in model.s_T) +
            sum(sum(model.v_S_PipelineCapacity[p,p_tilde] * model.p_psi_PipelineCapacity for p in model.s_PP if model.p_PCA[p,p_tilde]) for p_tilde in model.s_CP) +
            sum(sum(model.v_S_PipelineCapacity[p,p_tilde] * model.p_psi_PipelineCapacity for p in model.s_CP if model.p_CCA[p,p_tilde]) for p_tilde in model.s_CP) +
            sum(sum(model.v_S_PipelineCapacity[p,n] * model.p_psi_PipelineCapacity for p in model.s_PP if model.p_PNA[p,n]) for n in model.s_N) + 
            sum(sum(model.v_S_PipelineCapacity[p,p_tilde] * model.p_psi_PipelineCapacity for p in model.s_PP if model.p_PPA[p,p_tilde]) for p_tilde in model.s_PP) + 
            sum(sum(model.v_S_PipelineCapacity[p,n] * model.p_psi_PipelineCapacity for p in model.s_CP if model.p_CNA[p,n]) for n in model.s_N) + 
            sum(sum(model.v_S_PipelineCapacity[n,n_tilde] * model.p_psi_PipelineCapacity for n in model.s_N if model.p_NNA[n,n_tilde]) for n_tilde in model.s_N) + 
            sum(sum(model.v_S_PipelineCapacity[n,p] * model.p_psi_PipelineCapacity for n in model.s_N if model.p_NCA[n,p]) for p in model.s_CP) + 
            sum(sum(model.v_S_PipelineCapacity[n,k] * model.p_psi_PipelineCapacity for n in model.s_N if model.p_NKA[n,k]) for k in model.s_K) + 
            sum(sum(model.v_S_PipelineCapacity[n,s] * model.p_psi_PipelineCapacity for n in model.s_N if model.p_NSA[n,s]) for s in model.s_S) + 
            sum(sum(model.v_S_PipelineCapacity[n,r] * model.p_psi_PipelineCapacity for n in model.s_N if model.p_NRA[n,r]) for r in model.s_R) + 
            sum(sum(model.v_S_PipelineCapacity[n,o] * model.p_psi_PipelineCapacity for n in model.s_N if model.p_NOA[n,o]) for o in model.s_O) + 
            sum(sum(model.v_S_PipelineCapacity[f,p] * model.p_psi_PipelineCapacity for f in model.s_F if model.p_FCA[f,p]) for p in model.s_CP) + 
            sum(sum(model.v_S_PipelineCapacity[r,n] * model.p_psi_PipelineCapacity for r in model.s_R if model.p_RNA[r,n]) for n in model.s_N) + 
            sum(sum(model.v_S_PipelineCapacity[r,p] * model.p_psi_PipelineCapacity for r in model.s_R if model.p_RCA[r,p]) for p in model.s_CP) + 
            sum(sum(model.v_S_PipelineCapacity[r,k] * model.p_psi_PipelineCapacity for r in model.s_R if model.p_RKA[r,k]) for k in model.s_K) + 
            sum(sum(model.v_S_PipelineCapacity[s,n] * model.p_psi_PipelineCapacity for s in model.s_S if model.p_SNA[s,n]) for n in model.s_N) + 
            sum(sum(model.v_S_PipelineCapacity[s,p] * model.p_psi_PipelineCapacity for s in model.s_S if model.p_SCA[s,p]) for p in model.s_CP) + 
            sum(sum(model.v_S_PipelineCapacity[s,k] * model.p_psi_PipelineCapacity for s in model.s_S if model.p_SKA[s,k]) for k in model.s_K) + 
            sum(sum(model.v_S_PipelineCapacity[s,r] * model.p_psi_PipelineCapacity for s in model.s_S if model.p_SRA[s,r]) for r in model.s_R) + 
            sum(sum(model.v_S_PipelineCapacity[s,o] * model.p_psi_PipelineCapacity for s in model.s_S if model.p_SOA[s,o]) for o in model.s_O) +
            sum(model.v_S_StorageCapacity[s] * model.p_psi_StorageCapacity for s in model.s_S) +
            sum(model.v_S_DisposalCapacity[k] * model.p_psi_DisposalCapacity for k in model.s_K) +
            sum(model.v_S_TreatmentCapacity[r] * model.p_psi_TreatmentCapacity for r in model.s_R) +
            sum(model.v_S_ReuseCapacity[o] * model.p_psi_ReuseCapacity for o in model.s_O)
        )
    model.SlackCosts = Constraint(rule=SlackCostsRule, doc='Slack costs')

    # model.SlackCosts.pprint()

    def LogicConstraintDisposalRule(model,k):
        return sum(model.vb_y_Disposal[k,i] for i in model.s_I) == 1
    model.LogicConstraintDisposal = Constraint(model.s_K,rule=LogicConstraintDisposalRule,doc='Logic constraint disposal')

    # model.LogicConstraintDisposal.pprint()

    def LogicConstraintStorageRule(model,s):
        return sum(model.vb_y_Storage[s,c] for c in model.s_C) ==1
    model.LogicConstraintStorage = Constraint(model.s_S,rule=LogicConstraintStorageRule,doc='Logic constraint storage')

    # model.LogicConstraintStorage.pprint()

    def LogicConstraintTreatmentRule(model,r):
        return sum(model.vb_y_Treatment[r,j] for j in model.s_J) == 1
    model.LogicConstraintTreatment = Constraint(model.s_R,rule=LogicConstraintTreatmentRule,doc='Logic constraint treatment')

    # model.LogicConstraintTreatment.pprint()

    def LogicConstraintPipelineRule(model,l,l_tilde):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip                
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l,l_tilde]:
                return sum(model.vb_y_Pipeline[l,l_tilde,d] for d in model.s_D) == 1
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    model.LogicConstraintPipeline = Constraint(model.s_L,model.s_L,rule=LogicConstraintPipelineRule, doc='Logic constraint pipelines')

    def ReuseDestinationDeliveriesRule(model,p,t):
        return (model.v_F_ReuseDestination[p,t] == sum(model.v_F_Piped[l,p,t] + model.v_F_Trucked[l,p,t] for l in model.s_L))
    model.ReuseDestinationDeliveries = Constraint(model.s_CP,model.s_T,rule=ReuseDestinationDeliveriesRule, doc='Reuse destinations volume')

    # model.ReuseDestinationDeliveries.pprint()

    def DisposalDestinationDeliveriesRule(model,k,t):
        return (model.v_F_DisposalDestination[k,t] == sum(model.v_F_Piped[l,k,t] + model.v_F_Trucked[l,k,t] for l in model.s_L))
    model.DisposalDestinationDeliveries = Constraint(model.s_K,model.s_T,rule=DisposalDestinationDeliveriesRule, doc='Disposal destinations volume')

    # model.DisposalDestinationDeliveries.pprint()

    # model.LogicConstraintPipeline['N17','CP03'].pprint()

    ## Fixing Decision Variables ##

    # model.vb_y_Disposal['K02','I1'].fix(1)

    # model.v_S_ReuseCapacity['O1'].fix(0)

    # model.v_S_TreatmentCapacity['R01'].fix(0)

    # model.v_F_Piped['R01','CP01','T07'].fix(500)

    # model.vb_y_Pipeline['N24','N25','D0'].fix(1)
    # model.vb_y_Pipeline['N25','N24','D0'].fix(1)

    # model.v_S_FracDemand.fix(0)
    # model.v_S_Production.fix(0)
    # model.v_S_Flowback.fix(0)          
    # model.v_S_PipelineCapacity.fix(0)
    # model.v_S_StorageCapacity.fix(0) 
    # model.v_S_DisposalCapacity.fix(0)  
    # model.v_S_TreatmentCapacity.fix(0) 
    # model.v_S_ReuseCapacity.fix(0)     

    ## Define Objective and Solve Statement ##

    model.objective = Objective(expr=model.v_Z, 
                                sense=minimize,
                                doc='Objective function')

    return model

class PrintValues(Enum):
    Detailed = 0  
    Nominal = 1  
    Essential = 2   

def generate_report(model, is_print=[]):

    
    printing_list = []

    # Detailed: Slacks values included, Same as "All"
    if PrintValues.Detailed in is_print:
        printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_F_PadStorageIn', 
                    'v_F_PadStorageOut','v_F_ReuseDestination','v_F_DisposalDestination','v_C_Piped','v_C_Trucked','v_C_Sourced','v_C_Disposal',
                    'v_C_Reuse','v_L_Storage','vb_y_Pipeline','vb_y_Disposal','vb_y_Storage',
                    'vb_y_Treatment',
                    'v_C_TotalSourced','v_C_TotalDisposal','v_C_TotalTreatment','v_C_TotalReuse',
                    'v_C_TotalPiping','v_C_TotalStorage','v_C_TotalTrucking','v_C_Slack','vb_y_FLow'
                    'v_R_TotalStorage','v_C_DisposalCapEx','v_C_StorageCapEx','v_C_PipelineCapEx','v_C_TreatmentCapEx',
                    'v_F_TotalSourced','v_F_TotalDisposed','p_beta_TotalProd','v_F_TotalReused',
                    'Overview']

    # Nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage
    if PrintValues.Nominal in is_print:
        printing_list = ['v_F_Piped','v_F_Trucked','v_F_Sourced','v_C_Piped','v_C_Trucked',
                    'v_C_Sourced','vb_y_Pipeline','vb_y_Disposal','vb_y_Storage','vb_y_Treatment','vb_y_Flow','Overview']

     # Essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
    if PrintValues.Essential in is_print:
        printing_list = ['Overview'] 

    solution_dict = {}
    slacks_dict = {}
    output_dict = {}

    # Piped water volumes 
    v_F_Pipe_dict = [('Origin', 'Destination', 'Time', 'Piped water volumes')]
    for i in model.v_F_Piped:
        var_value = model.v_F_Piped[i].value
        if var_value != None and var_value > 0:
            v_F_Pipe_dict.append((*i, var_value))

    # Piping costs 
    v_C_Piped_dict = [('Origin', 'Destination', 'Time', 'Piping cost')]
    for i in model.v_C_Piped:
        var_value = model.v_C_Piped[i].value
        if var_value != None and var_value > 0:
            v_C_Piped_dict.append((*i, var_value))

    # Trucked water volumes
    v_F_Trucked_dict = [('Origin', 'Destination', 'Time', 'Trucked water volumes')]
    for i in model.v_F_Trucked :
        var_value = model.v_F_Trucked[i].value
        if var_value != None and var_value > 0:
            v_F_Trucked_dict.append((*i, var_value))

    # Trucking costs 
    v_C_Trucked_dict = [('Origin', 'Destination', 'Time', 'Trucking costs')]
    for i in model.v_C_Trucked:
        var_value = model.v_C_Trucked[i].value
        if var_value != None and var_value > 0:
            v_C_Trucked_dict.append((*i, var_value))

    # Sourced freshwater volumes
    v_F_Sourced_dict = [('Origin', 'Destination', 'Time', 'Sourced freshwater volumes')]
    for i in model.v_F_Sourced:
        var_value = model.v_F_Sourced[i].value
        if var_value != None and var_value > 0:
            v_F_Sourced_dict.append((*i, var_value))

    # Sourcing costs 
    v_C_Sourced_dict = [('Origin', 'Destination', 'Time', 'Sourcing costs')]
    for i in model.v_C_Sourced:
        var_value = model.v_C_Sourced[i].value
        if var_value != None and var_value > 0:
            v_C_Sourced_dict.append((*i, var_value))

    # Storage in completions pad
    v_F_PadStorageIn_dict = [('Completions Pad', 'Time', 'Storage In')]
    for i in model.v_F_PadStorageIn:
        var_value = model.v_F_PadStorageIn[i].value
        if var_value != None and var_value > 0:
            v_F_PadStorageIn_dict.append((*i, var_value))

    # Storage out completions pad
    v_F_PadStorageOut_dict = [('Completions Pad', 'Time', 'Storage Out')]
    for i in model.v_F_PadStorageOut:
        var_value = model.v_F_PadStorageOut[i].value
        if var_value != None and var_value > 0:
            v_F_PadStorageOut_dict.append((*i, var_value))

    # Reuse destination volumes
    v_F_ReuseDestination_dict = [('Completions Pad', 'Time', 'Volume')]
    for i in model.v_F_ReuseDestination:
        var_value = model.v_F_ReuseDestination[i].value
#        if var_value != None and var_value > 0:
        v_F_ReuseDestination_dict.append((*i, var_value))

    # Disposal destination volumes
    v_F_DisposalDestination_dict = [('Disposal Site', 'Time', 'Volume')]
    for i in model.v_F_DisposalDestination:
        var_value = model.v_F_DisposalDestination[i].value
#        if var_value != None and var_value > 0:
        v_F_DisposalDestination_dict.append((*i, var_value))

    # Disposal costs 
    v_C_Disposal_dict = [('Disposal site', 'Time', 'Disposal Costs')]
    for i in model.v_C_Disposal:
        var_value = model.v_C_Disposal[i].value
        if var_value != None and var_value > 0:
            v_C_Disposal_dict.append((*i, var_value)) 

    # Treatment costs 
    v_C_Treatment_dict = [('Treatment site', 'Time', 'Treatment Costs')]
    for i in model.v_C_Treatment:
        var_value = model.v_C_Treatment[i].value
        if var_value != None and var_value > 0:
            v_C_Treatment_dict.append((*i, var_value)) 

    # Reuse costs
    v_C_Reuse_dict = [('Completions Pad', 'Time', 'Reuse Costs')]
    for i in model.v_C_Reuse:
        var_value = model.v_C_Reuse[i].value
        if var_value != None and var_value > 0:
            v_C_Reuse_dict.append((*i, var_value))  

    # Storage costs
    v_C_Storage_dict = [('Storage Site', 'Time', 'Storage Costs')]
    for i in model.v_C_Storage:
        var_value = model.v_C_Storage[i].value
        if var_value != None and var_value > 0:
            v_C_Storage_dict.append((*i, var_value)) 

    # Storage credit
    v_R_Storage_dict = [('Storage Site', 'Time', 'Credit for Retrieving Water')]
    for i in model.v_R_Storage:
        var_value = model.v_R_Storage[i].value
        if var_value != None and var_value > 0:
            v_R_Storage_dict.append((*i, var_value))

    # Storage levels
    v_L_StorageLevels_dict = [('Storage site', 'Time', 'Storage Levels')]
    for i in model.v_L_Storage:
        var_value = model.v_L_Storage[i].value
        if var_value != None and var_value > 0:
            v_L_StorageLevels_dict.append((*i, var_value))

    # Pad Storage levels
    v_L_PadStorage_dict = [('Completion pad', 'Time', 'Storage Levels')]
    for i in model.v_L_PadStorage:
        var_value = model.v_L_PadStorage[i].value
        if var_value != None and var_value > 0:
            v_L_PadStorage_dict.append((*i, var_value))

    # Pipeline expansion
    vb_y_PipelineExpansion_dict = [('Origin', 'Destination', 'Pipeline Diameter', 'True/False')]
    for i in model.vb_y_Pipeline:
        var_value = model.vb_y_Pipeline[i].value
        if var_value != None and var_value > 0:
            vb_y_PipelineExpansion_dict.append((*i, var_value))

    # Disposal expansion
    vb_y_DisposalExpansion_dict = [('Disposal Site', 'Injection Capacity', 'True/False')]
    for i in model.vb_y_Disposal:
        var_value = model.vb_y_Disposal[i].value
        if var_value != None and var_value > 0:
            vb_y_DisposalExpansion_dict.append((*i, var_value))
    
    # Storage expansion
    vb_y_StorageExpansion_dict = [('Storage Site', 'Storage Capacity', 'True/False')]
    for i in model.vb_y_Storage:
        var_value = model.vb_y_Storage[i].value
        if var_value != None and var_value > 0:
            vb_y_StorageExpansion_dict.append((*i, var_value))

    # Treatment expansion
    vb_y_TreatmentExpansion_dict = [('Treatment Site', 'Treatment Capacity', 'True/False')]
    for i in model.vb_y_Treatment:
        var_value = model.vb_y_Treatment[i].value
        if var_value != None and var_value > 0:
            vb_y_TreatmentExpansion_dict.append((*i, var_value))

    # Binary flow directions
    vb_y_Flow_dict = [('Origin', 'Destination', 'Time', 'True/False')]
    for i in model.vb_y_Flow:
        var_value = model.vb_y_Flow[i].value
        if var_value != None and var_value > 0:
            vb_y_Flow_dict.append((*i, var_value)) 

    # Disposal Site Capacity
    v_D_Capacity_dict = [('Disposal Site', 'Disposal Capacity')]
    for i in model.v_D_Capacity:
        var_value = model.v_D_Capacity[i].value
        if var_value != None and var_value > 0:
            v_D_Capacity_dict.append((i, var_value))

    # Storage Site Capacity
    v_X_Capacity_dict = [('Storage Site', 'Storage Capacity')]
    for i in model.v_X_Capacity:
        var_value = model.v_X_Capacity[i].value
        if var_value != None and var_value > 0:
            v_X_Capacity_dict.append((i, var_value))

    # Storage Site Capacity
    v_F_Capacity_dict = [('Origin', 'Destination', 'Flow Capacity')]
    for i in model.v_F_Capacity:
        var_value = model.v_F_Capacity[i].value
        if var_value != None and var_value > 0:
            v_F_Capacity_dict.append((*i, var_value))

    # Economics, Volumes, KPIs Overview Variables
    v_F_Overview_dict = [('Variable Name', 'Documentation', 'Total')]
    v_F_Overview_dict.append(('Economics','',''))
    v_F_Overview_dict.append((model.v_Z.name, model.v_Z.doc, model.v_Z.value))
    v_F_Overview_dict.append((model.v_C_TotalDisposal.name, model.v_C_TotalDisposal.doc, model.v_C_TotalDisposal.value))
    v_F_Overview_dict.append((model.v_C_TotalTreatment.name, model.v_C_TotalTreatment.doc, model.v_C_TotalTreatment.value))
    v_F_Overview_dict.append((model.v_C_TotalReuse.name, model.v_C_TotalReuse.doc, model.v_C_TotalReuse.value))
    v_F_Overview_dict.append((model.v_C_TotalPiping.name, model.v_C_TotalPiping.doc, model.v_C_TotalPiping.value))
    v_F_Overview_dict.append((model.v_C_TotalStorage.name, model.v_C_TotalStorage.doc, model.v_C_TotalStorage.value))
    v_F_Overview_dict.append((model.v_C_TotalTrucking.name, model.v_C_TotalTrucking.doc, model.v_C_TotalTrucking.value))
    v_F_Overview_dict.append((model.v_C_TotalSourced.name, model.v_C_TotalSourced.doc, model.v_C_TotalSourced.value))
    v_F_Overview_dict.append((model.v_R_TotalStorage.name, model.v_R_TotalStorage.doc, model.v_R_TotalStorage.value)) 
    v_F_Overview_dict.append((model.v_C_Slack.name, model.v_C_Slack.doc, model.v_C_Slack.value))

    # Adding Blank line in between data on excel sheet
    v_F_Overview_dict.append(('','',''))
    v_F_Overview_dict.append((model.v_C_DisposalCapEx.name,  model.v_C_DisposalCapEx.doc,  model.v_C_DisposalCapEx.value))
    v_F_Overview_dict.append((model.v_C_TreatmentCapEx.name, model.v_C_TreatmentCapEx.doc, model.v_C_TreatmentCapEx.value))
    v_F_Overview_dict.append((model.v_C_StorageCapEx.name,  model.v_C_StorageCapEx.doc,  model.v_C_StorageCapEx.value))
    v_F_Overview_dict.append((model.v_C_PipelineCapEx.name,  model.v_C_PipelineCapEx.doc,  model.v_C_PipelineCapEx.value))

    # Adding Blank line in between data on excel sheet with heading
    v_F_Overview_dict.append(('','',''))
    v_F_Overview_dict.append(('Volumes','',''))
    v_F_Overview_dict.append((model.v_F_TotalSourced.name,  model.v_F_TotalSourced.doc,  model.v_F_TotalSourced.value))
    v_F_Overview_dict.append((model.v_F_TotalDisposed.name,  model.v_F_TotalDisposed.doc,  model.v_F_TotalDisposed.value))
    v_F_Overview_dict.append((model.p_beta_TotalProd.name,  model.p_beta_TotalProd.doc,  model.p_beta_TotalProd.value))
    v_F_Overview_dict.append((model.v_F_TotalReused.name,  model.v_F_TotalReused.doc,  model.v_F_TotalReused.value))
    v_F_Overview_dict.append((model.v_F_TotalTrucked.name,  model.v_F_TotalTrucked.doc,  model.v_F_TotalTrucked.value))

    # Adding Blank line in between data on excel sheet with heading
    v_F_Overview_dict.append(('','',''))
    v_F_Overview_dict.append(('KPIs','',''))

    reuse_WaterKPI = (model.v_F_TotalReused.value)/(model.p_beta_TotalProd.value)*100
    v_F_Overview_dict.append(('Reuse Produced Water KPI',  'Reuse Fraction Produced Water = [%]',  reuse_WaterKPI))

    disposal_WaterKPI = (model.v_F_TotalDisposed.value)/(model.p_beta_TotalProd.value)*100
    v_F_Overview_dict.append(('Disposal Produced Water KPI',  'Disposal Fraction Produced Water = [%]',  disposal_WaterKPI))

    fresh_CompletionsDemandKPI = (model.v_F_TotalSourced.value)/(model.p_gamma_TotalDemand.value)*100
    v_F_Overview_dict.append(('Fresh Completions Demand KPI',  'Fresh Fraction Completions Demand = [%]',  fresh_CompletionsDemandKPI))

    reuse_CompletionsDemandKPI = (model.v_F_TotalReused.value)/(model.p_gamma_TotalDemand.value)*100
    v_F_Overview_dict.append(('Reuse Completions Demand KPI',  'Reuse Fraction Completions Demand = [%]',  reuse_CompletionsDemandKPI))

    if model.v_C_Slack.value != None and model.v_C_Slack.value != 0:
        print('!!!ATTENTION!!! One or several slack variables have been triggered!')

        # Frac demand slack variables
        v_S_FracDemand_dict = [('Completion pad', 'Time', 'Slack FracDemand')]
        for i in model.v_S_FracDemand:
            var_value = model.v_S_FracDemand[i].value
            if var_value != None and var_value != 0:
                v_S_FracDemand_dict.append((*i, var_value))

        # Production slack variables
        v_S_Production_dict = [('Production pad', 'Time', 'Slack Production')]
        for i in model.v_S_Production:
            var_value = model.v_S_Production[i].value
            if var_value != None and var_value != 0:
                v_S_Production_dict.append((*i, var_value))
        
        # Flowback slack variables
        v_S_Flowback_dict = [('Completion pad', 'Time', 'Slack Flowback')]
        for i in model.v_S_Flowback:
            var_value = model.v_S_Flowback[i].value
            if var_value != None and var_value != 0:
                v_S_Flowback_dict.append((*i, var_value))

        # Pipeline capacity slack variables
        v_S_PipelineCapacity_dict = [('Origin', 'Destination', 'Slack Pipeline Capacity')]
        for i in model.v_S_PipelineCapacity:
            var_value = model.v_S_PipelineCapacity[i].value
            if var_value != None and var_value != 0:
                v_S_PipelineCapacity_dict.append((*i, var_value))
        
        # Storage capacity slack variables
        v_S_StorageCapacity_dict = [('Storage site', 'Slack Storage Capacity')]
        for i in model.v_S_StorageCapacity:
            var_value = model.v_S_StorageCapacity[i].value
            if var_value != None and var_value != 0:
                v_S_StorageCapacity_dict.append((i, var_value))

        # Storage capacity slack variables
        v_S_DisposalCapacity_dict = [('Storage site', 'Slack Disposal Capacity')]
        for i in model.v_S_DisposalCapacity:
            var_value = model.v_S_DisposalCapacity[i].value
            if var_value != None and var_value != 0:
                v_S_DisposalCapacity_dict.append((i, var_value))
        
        # Treatment capacity slack variables
        v_S_TreatmentCapacity_dict = [('Treatment site', 'Slack Treatment Capacity')]
        for i in model.v_S_TreatmentCapacity:
            var_value = model.v_S_TreatmentCapacity[i].value
            if var_value != None and var_value != 0:
                v_S_TreatmentCapacity_dict.append((i, var_value))

        # Reuse capacity slack variables
        v_S_ReuseCapacity_dict = [('Reuse site', 'Slack Reuse Capacity')]
        for i in model.v_S_ReuseCapacity:
            var_value = model.v_S_ReuseCapacity[i].value
            if var_value != None and var_value != 0:
                v_S_ReuseCapacity_dict.append((i, var_value))

        slacks_dict = {'v_S_FracDemand': v_S_FracDemand_dict, 
                    'v_S_Production': v_S_Production_dict,
                    'v_S_Flowback': v_S_Flowback_dict, 
                    'v_S_PipelineCapacity': v_S_PipelineCapacity_dict,
                    'v_S_StorageCapacity': v_S_StorageCapacity_dict, 
                    'v_S_TreatmentCapacity': v_S_TreatmentCapacity_dict,
                    'v_S_DisposalCapacity': v_S_DisposalCapacity_dict,
                    'v_S_ReuseCapacity': v_S_ReuseCapacity_dict}

    solution_dict = {'Overview': v_F_Overview_dict, 'v_F_Piped': v_F_Pipe_dict, 
                    'v_F_Trucked': v_F_Trucked_dict,
                    'v_F_Sourced': v_F_Sourced_dict, 'v_F_PadStorageIn': v_F_PadStorageIn_dict,
                    'v_F_PadStorageOut': v_F_PadStorageOut_dict, 'v_C_Piped': v_C_Piped_dict,
                    'v_F_ReuseDestination': v_F_ReuseDestination_dict,'v_F_DisposalDestination': v_F_DisposalDestination_dict,
                    'v_C_Trucked': v_C_Trucked_dict, 'v_C_Sourced': v_C_Sourced_dict,
                    'v_C_Disposal': v_C_Disposal_dict, 'v_C_Reuse': v_C_Reuse_dict,
                    'v_C_Storage': v_C_Storage_dict, 'v_R_Storage': v_R_Storage_dict,
                    'v_C_Treatment': v_C_Treatment_dict, 'v_L_Storage': v_L_StorageLevels_dict,
                    'v_L_PadStorage': v_L_PadStorage_dict,
                    'vb_y_Pipeline': vb_y_PipelineExpansion_dict, 
                    'vb_y_Disposal': vb_y_DisposalExpansion_dict, 
                    'vb_y_Storage': vb_y_StorageExpansion_dict, 'vb_y_Flow': vb_y_Flow_dict,
                    'vb_y_Treatment': vb_y_TreatmentExpansion_dict,
                    'v_D_Capacity': v_D_Capacity_dict, 'v_X_Capacity': v_X_Capacity_dict,
                    'v_F_Capacity': v_F_Capacity_dict}

    output_dict = {**solution_dict, **slacks_dict}


    for i in list(output_dict.items())[1:]:
        if i[0] in printing_list:
                print('\n','='*10, i[0].upper(),'='*10)
                print(i[1][0])
                for j in i[1][1:]:
                        print('{0}{1} = {2}'.format(i[0], j[:-1], j[-1]))
    

    # Loop for printing Overview Information
    for i in list(output_dict.items())[:1]:
            if i[0] in printing_list:
                    print('\n','='*10, i[0].upper(),'='*10)
                    # print(i[1][1][0])
                    for j in i[1][1:]:
                        if not j[0]:  # Conditional that checks if a blank line should be added
                            print()
                        elif not j[1]:  # Conditional that checks if the header for a section should be added
                            print(j[0].upper())
                        else:
                            print('{0} = {1}'.format(j[1], j[2]))

    # if 'Overview' in printing_list:
    #     print('\n','='*10, 'OVERVIEW','='*10)
    #     print('\n Economics, Volumes and KPIs \n')

    #     print('The objective function value is $', model.v_Z.value, '\n')

    #     # Economics
    #     print('Total Disposal Cost = $', model.v_C_TotalDisposal.value)
    #     print('Total Treatment Cost = $', model.v_C_TotalTreatment.value)
    #     print('Total Reuse Cost = $', model.v_C_TotalReuse.value)
    #     print('Total Piping Cost = $', model.v_C_TotalPiping.value)
    #     print('Total Storage Cost = $', model.v_C_TotalStorage.value)
    #     print('Total Trucking Cost = $', model.v_C_TotalTrucking.value)
    #     print('Total Fresh Sourced Cost = $', model.v_C_TotalSourced.value)
    #     print('Total Storage Credit = $', model.v_R_TotalStorage.value, '\n')

    #     print('Total Disposal Capex = $', model.v_C_DisposalCapEx.value)
    #     print('Total Treatment Capex = $', model.v_C_TreatmentCapEx.value)
    #     print('Total Storage Capex = $', model.v_C_StorageCapEx.value)
    #     print('Total Pipeline Capex = $', model.v_C_PipelineCapEx.value, '\n')

    #     # Volumes
    #     print('Total Fresh Sourced Volume = ', model.v_F_TotalSourced.value, 'bbl')
    #     print('Total Disposal Volume = ', model.v_F_TotalDisposed.value, 'bbl')
    #     print('Total Produced Volume = ', model.p_beta_TotalProd.value, 'bbl')    
    #     print('Total Reused Volume = ', model.v_F_TotalReused.value, 'bbl')
    #     print('Total Trucked Volume = ', model.v_F_TotalTrucked.value, 'bbl \n')

    #     # KPIs
    #     print('Reuse Fraction Produced Water = ', (model.v_F_TotalReused.value)/(model.p_beta_TotalProd.value)*100, '%')
    #     print('Disposal Fraction Produced Water = ', (model.v_F_TotalDisposed.value)/(model.p_beta_TotalProd.value)*100, '%')
    #     print('Fresh Fraction Completions Demand = ', (model.v_F_TotalSourced.value)/(model.p_gamma_TotalDemand.value)*100, '%')
    #     print('Reuse Fraction Completions Demand = ', (model.v_F_TotalReused.value)/(model.p_gamma_TotalDemand.value)*100, '%')

    # ## Printing model sets, parameters, constraints, variable values ##
    return model, output_dict

if __name__ == '__main__':
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = ['ProductionPads', 'ProductionTanks','CompletionsPads',
			 'SWDSites','FreshwaterSources','StorageSites','TreatmentSites',
			 'ReuseOptions','NetworkNodes','PipelineDiameters','StorageCapacities',
             'InjectionCapacities','TreatmentCapacities']
    parameter_list = ['PNA','CNA','CCA','NNA','NCA','NKA','NRA','NSA','FCA','RCA','RNA',
			          'SNA','PCT','PKT','FCT','CST','CCT','CKT','TruckingTime','CompletionsDemand',
			          'PadRates','FlowbackRates','InitialPipelineCapacity','InitialDisposalCapacity',
			          'InitialTreatmentCapacity','FreshwaterSourcingAvailability','PadOffloadingCapacity',
			          'CompletionsPadStorage','DisposalOperationalCost','TreatmentOperationalCost',
			          'ReuseOperationalCost','PipelineOperationalCost','FreshSourcingCost','TruckingHourlyCost',
			          'PipelineCapacityIncrements','DisposalCapacityIncrements','InitialStorageCapacity',
                      'StorageCapacityIncrements','TreatmentCapacityIncrements','TreatmentEfficiency',
                      'DisposalExpansionCost','StorageExpansionCost','TreatmentExpansionCost','PipelineExpansionCost']

    with resources.path('pareto.case_studies',
                        "input_data_generic_strategic_case_study_LAYFLAT_FULL.xlsx") as fpath:
            [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

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

