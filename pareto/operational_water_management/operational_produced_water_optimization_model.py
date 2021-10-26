#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021 by the software owners: The
# Regents of the University of California, through Lawrence Berkeley National Laboratory, et al. All
# rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the
# U.S. Government consequently retains certain rights. As such, the U.S. Government has been granted
# for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license
# in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit other to do so.
#####################################################################################################
# Title: OPERATIONAL Produced Water Optimization Model

# Notes:
# - Introduced new completions-to-completions trucking arc (CCT) to account for possible flowback reuse
# - Implemented a generic OPERATIONAL case study example (updated model sets, additional input data)
# - Implemented an initial formulation for production tank modeling (see updated documentation)
# - Implemented a corrected version of the disposal capacity constraint considering more trucking-to-disposal arcs (PKT, SKT, SKT, RKT) [June 28]
# - Implemented an improved slack variable display loop [June 29]
# - Implemented fresh sourcing via trucking [July 2]
# - Implemented completions pad storage [July 6]
# - Implemeted an equalized production tank formulation [July 7]
# - Implemented changes to flowback processing [July 13]
# - Implemented production tank config option [August 4]

# Import
from pyomo.environ import (
    Var,
    Param,
    Set,
    ConcreteModel,
    Constraint,
    Objective,
    minimize,
    NonNegativeReals,
    Reals,
    Binary,
)
from pareto.utilities.get_data import get_data
from importlib import resources
import pyomo.environ

# import gurobipy
from pyomo.common.config import ConfigBlock, ConfigValue, In
from enum import Enum

from pareto.utilities.solvers import get_solver


class ProdTank(Enum):
    individual = 0
    equalized = 1


# create config dictionary
CONFIG = ConfigBlock()
CONFIG.declare(
    "has_pipeline_constraints",
    ConfigValue(
        default=True,
        domain=In([True, False]),
        description="build pipeline constraints",
        doc="""Indicates whether holdup terms should be constructed or not.
**default** - True.
**Valid values:** {
**True** - construct pipeline constraints,
**False** - do not construct pipeline constraints}""",
    ),
)
CONFIG.declare(
    "production_tanks",
    ConfigValue(
        default=ProdTank.individual,
        domain=In(ProdTank),
        description="production tank type selection",
        doc="Type of production tank arrangement (i.e., Individual, Equalized)",
    ),
)

# Creation of a Concrete Model


def create_model(df_sets, df_parameters, default={}):
    model = ConcreteModel()
    # import config dictionary
    model.config = CONFIG(default)
    model.type = "operational"
    model.proprietary_data = df_parameters["proprietary_data"][0]
    ## Define sets ##

    model.s_T = Set(initialize=df_sets["TimePeriods"], doc="Time Periods", ordered=True)
    model.s_PP = Set(initialize=df_sets["ProductionPads"], doc="Production Pads")
    model.s_CP = Set(initialize=df_sets["CompletionsPads"], doc="Completions Pads")
    model.s_A = Set(initialize=df_sets["ProductionTanks"], doc="Production Tanks")
    model.s_P = Set(initialize=(model.s_PP | model.s_CP), doc="Pads")
    model.s_F = Set(initialize=df_sets["FreshwaterSources"], doc="Freshwater Sources")
    model.s_K = Set(initialize=df_sets["SWDSites"], doc="Disposal Sites")
    model.s_S = Set(initialize=df_sets["StorageSites"], doc="Storage Sites")
    model.s_R = Set(initialize=df_sets["TreatmentSites"], doc="Treatment Sites")
    model.s_O = Set(initialize=df_sets["ReuseOptions"], doc="Reuse Options")
    model.s_N = Set(initialize=df_sets["NetworkNodes"], doc=["Network Nodes"])
    model.s_L = Set(
        initialize=(
            model.s_P
            | model.s_F
            | model.s_K
            | model.s_S
            | model.s_R
            | model.s_O
            | model.s_N
        ),
        doc="Locations",
    )

    # COMMENT: Remove pipeline diameter, storage capacity and injection capacity sets
    model.s_D = Set(initialize=["D0"], doc="Pipeline diameters")
    model.s_C = Set(initialize=["C0"], doc="Storage capacities")
    model.s_I = Set(initialize=["I0"], doc="Injection (i.e. disposal) capacities")

    # model.s_P.pprint()
    # model.s_L.pprint()

    ## Define continuous variables ##

    model.v_Z = Var(within=Reals, doc="Objective funcation variable [$]")

    model.v_F_Piped = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        doc="Produced water quantity piped from location l to location l [bbl/day]",
    )
    model.v_F_Trucked = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        doc="Produced water quantity trucked from location l to location l [bbl/day]",
    )
    model.v_F_Sourced = Var(
        model.s_F,
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        doc="Fresh water sourced from source f to completions pad p [bbl/day]",
    )
    model.v_F_PadStorageIn = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        doc="Water put into completions" " pad storage [bbl/day]",
    )
    model.v_F_PadStorageOut = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        doc="Water from completions pad storage" " used for fracturing [bbl/day]",
    )

    if model.config.production_tanks == ProdTank.individual:
        model.v_F_Drain = Var(
            model.s_P,
            model.s_A,
            model.s_T,
            within=NonNegativeReals,
            doc="Produced water drained from" " production tank [bbl/day]",
        )
        model.v_L_ProdTank = Var(
            model.s_P,
            model.s_A,
            model.s_T,
            within=NonNegativeReals,
            doc="Water level in production tank [bbl]",
        )

    elif model.config.production_tanks == ProdTank.equalized:
        model.v_F_Drain = Var(
            model.s_P,
            model.s_T,
            within=NonNegativeReals,
            doc="Produced water drained from" " production tank [bbl/day]",
        )
        model.v_L_ProdTank = Var(
            model.s_P,
            model.s_T,
            within=NonNegativeReals,
            doc="Water level in production tank [bbl]",
        )
    else:
        raise Exception("storage type not supported")

    model.v_L_PadStorage = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        doc="Water level in completions pad storage [bbl]",
    )

    model.v_B_Production = Var(
        model.s_P,
        model.s_T,
        within=NonNegativeReals,
        doc="Produced water for transport from pad [bbl/day]",
    )

    model.v_L_Storage = Var(
        model.s_S,
        model.s_T,
        within=NonNegativeReals,
        doc="Water level at storage site [bbl]",
    )

    model.v_C_Piped = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        doc="Cost of piping produced water from location l to location l [$/day]",
    )
    model.v_C_Trucked = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        doc="Cost of trucking produced water from location l to location l [$/day]",
    )
    model.v_C_Sourced = Var(
        model.s_F,
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        doc="Cost of sourcing fresh water from source f to completion pad p [$/day]",
    )
    model.v_C_Disposal = Var(
        model.s_K,
        model.s_T,
        within=NonNegativeReals,
        doc="Cost of injecting produced water at disposal site [$/day]",
    )
    model.v_C_Treatment = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        doc="Cost of treating produced water at treatment site [$/day]",
    )
    model.v_C_Reuse = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        doc="Cost of reusing produced water at completions site [$/day]",
    )
    model.v_C_Storage = Var(
        model.s_S,
        model.s_T,
        within=NonNegativeReals,
        doc="Cost of storing produced water at storage site [$/day]",
    )
    model.v_R_Storage = Var(
        model.s_S,
        model.s_T,
        within=NonNegativeReals,
        doc="Credit for retrieving stored produced water from storage site [$/bbl]",
    )

    model.v_C_TotalSourced = Var(
        within=NonNegativeReals, doc="Total cost of sourcing freshwater [$]"
    )
    model.v_C_TotalDisposal = Var(
        within=NonNegativeReals, doc="Total cost of injecting produced water [$]"
    )
    model.v_C_TotalTreatment = Var(
        within=NonNegativeReals, doc="Total cost of treating produced water [$]"
    )
    model.v_C_TotalReuse = Var(
        within=NonNegativeReals, doc="Total cost of reusing produced water [$]"
    )
    model.v_C_TotalPiping = Var(
        within=NonNegativeReals, doc="Total cost of piping produced water [$]"
    )
    model.v_C_TotalStorage = Var(
        within=NonNegativeReals, doc="Total cost of storing produced water [$]"
    )
    model.v_C_TotalTrucking = Var(
        within=NonNegativeReals, doc="Total cost of trucking produced water [$]"
    )
    model.v_C_Slack = Var(
        within=NonNegativeReals, doc="Total cost of slack variables [$"
    )
    model.v_R_TotalStorage = Var(
        within=NonNegativeReals, doc="Total credit for withdrawing produced water [$]"
    )

    model.v_F_ReuseDestination = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        doc="Total deliveries to completions pad [bbl/week]",
    )
    model.v_F_DisposalDestination = Var(
        model.s_K,
        model.s_T,
        within=NonNegativeReals,
        doc="Total deliveries to disposal site [bbl/week]",
    )
    model.v_F_TreatmentDestination = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        doc="Total delliveries to treatment site [bbl/week]",
    )

    # COMMENT: Remove the disposal/storage/flow capacity variables
    model.v_D_Capacity = Var(
        model.s_K,
        within=NonNegativeReals,
        doc="Disposal capacity at a disposal site [bbl/day]",
    )
    model.v_X_Capacity = Var(
        model.s_S,
        within=NonNegativeReals,
        doc="Storage capacity at a storage site [bbl/day]",
    )
    model.v_F_Capacity = Var(
        model.s_L,
        model.s_L,
        within=NonNegativeReals,
        doc="Flow capacity along pipeline arc [bbl/day]",
    )

    # COMMENT: Remove the disposal/pipine/storage capital capacity variables
    model.v_C_DisposalCapEx = Var(
        within=NonNegativeReals,
        doc="Capital cost of constructing or expanding disposal capacity [$]",
    )
    model.v_C_PipelineCapEx = Var(
        within=NonNegativeReals,
        doc="Capital cost of constructing or expanding piping capacity [$]",
    )
    model.v_C_StorageCapEx = Var(
        within=NonNegativeReals,
        doc="Capital cost of constructing or expanding storage capacity [$]",
    )

    model.v_S_FracDemand = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        doc="Slack variable to meet the completions demand [bbl/day]",
    )
    model.v_S_Production = Var(
        model.s_PP,
        model.s_T,
        within=NonNegativeReals,
        doc="Slack variable to process the produced water production [bbl/day]",
    )
    model.v_S_Flowback = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        doc="Slack variable to proces flowback water production [bbl/day]",
    )
    model.v_S_PipelineCapacity = Var(
        model.s_L,
        model.s_L,
        within=NonNegativeReals,
        doc="Slack variable to provide necessary pipeline capacity [bbl]",
    )
    model.v_S_StorageCapacity = Var(
        model.s_S,
        within=NonNegativeReals,
        doc="Slack variable to provide necessary storage capacity [bbl]",
    )
    model.v_S_DisposalCapacity = Var(
        model.s_K,
        within=NonNegativeReals,
        doc="Slack variable to provide necessary disposal capacity [bbl/day]",
    )
    model.v_S_TreatmentCapacity = Var(
        model.s_R,
        within=NonNegativeReals,
        doc="Slack variable to provide necessary treatment capacity [bbl/weel]",
    )
    model.v_S_ReuseCapacity = Var(
        model.s_O,
        within=NonNegativeReals,
        doc="Slack variable to provide necessary reuse capacity [bbl/day]",
    )

    ## Define binary variables ##

    # COMMENT: Remove the binary pipeline/storage/disposal variables
    model.vb_y_Pipeline = Var(
        model.s_L,
        model.s_L,
        model.s_D,
        within=Binary,
        doc="New pipeline installed between one location and another location with specific diameter",
    )
    model.vb_y_Storage = Var(
        model.s_S,
        model.s_C,
        within=Binary,
        doc="New or additional storage facility installed at storage site with specific storage capacity",
    )
    model.vb_y_Disposal = Var(
        model.s_K,
        model.s_I,
        within=Binary,
        doc="New or additional disposal facility installed at disposal site with specific injection capacity",
    )
    model.vb_y_Flow = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=Binary,
        doc="Directional flow between two locations",
    )
    model.vb_y_Truck = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=Binary,
        doc="Trucking between two locations",
    )

    # model.vb_z_Pipeline      = Var(model.s_L,model.s_L,model.s_D,model.s_T,within=Binary, doc='Timing of pipeline installation between two locations')
    # model.vb_z_Storage       = Var(model.s_S,model.s_C,model.s_T,within=Binary, doc='Timing of storage facility installation at storage site')
    # model.vb_z_Disposal      = Var(model.s_K,model.s_I,model.s_T,within=Binary, doc='Timing of disposal facility installation at disposal site')

    ## Define set parameters ##

    PCA_Table = {}

    PNA_Table = {}

    PPA_Table = {}

    CNA_Table = {}

    CCA_Table = {}

    NNA_Table = {}

    NCA_Table = {}

    NKA_Table = {}

    NSA_Table = {}

    NRA_Table = {}

    NOA_Table = {}

    FCA_Table = {}

    RNA_Table = {}

    RKA_Table = {}

    SNA_Table = {}

    SCA_Table = {}

    SKA_Table = {}

    SRA_Table = {}

    SOA_Table = {}

    PCT_Table = {}

    PKT_Table = {}

    PST_Table = {}

    PRT_Table = {}

    POT_Table = {}

    CKT_Table = {}

    CST_Table = {}

    CRT_Table = {}

    CCT_Table = {}

    SCT_Table = {}

    CRT_Table = {}

    SCT_Table = {}

    SKT_Table = {}

    RKT_Table = {}

    PAL_Table = {}

    model.p_PCA = Param(
        model.s_PP,
        model.s_CP,
        default=0,
        initialize=PCA_Table,
        doc="Valid production-to-completions pipeline arcs [-]",
    )
    model.p_PNA = Param(
        model.s_PP,
        model.s_N,
        default=0,
        initialize=PNA_Table,
        doc="Valid production-to-node pipeline arcs [-]",
    )
    model.p_PPA = Param(
        model.s_PP,
        model.s_PP,
        default=0,
        initialize=PPA_Table,
        doc="Valid production-to-production pipeline arcs [-]",
    )
    model.p_CNA = Param(
        model.s_CP,
        model.s_N,
        default=0,
        initialize=CNA_Table,
        doc="Valid completion-to-node pipeline arcs [-]",
    )
    model.p_CCA = Param(
        model.s_CP,
        model.s_CP,
        default=0,
        initialize=CCA_Table,
        doc="Valid completion-to-completion pipeline arcs [-]",
    )
    model.p_NNA = Param(
        model.s_N,
        model.s_N,
        default=0,
        initialize=NNA_Table,
        doc="Valid node-to-node pipeline arcs [-]",
    )
    model.p_NCA = Param(
        model.s_N,
        model.s_CP,
        default=0,
        initialize=NCA_Table,
        doc="Valid node-to-completions pipeline arcs [-]",
    )
    model.p_NKA = Param(
        model.s_N,
        model.s_K,
        default=0,
        initialize=NKA_Table,
        doc="Valid node-to-disposal pipeline arcs [-]",
    )
    model.p_NSA = Param(
        model.s_N,
        model.s_S,
        default=0,
        initialize=NSA_Table,
        doc="Valid node-to-storage pipeline arcs [-]",
    )
    model.p_NRA = Param(
        model.s_N,
        model.s_R,
        default=0,
        initialize=NRA_Table,
        doc="Valid node-to-treatment pipeline arcs [-]",
    )
    model.p_NOA = Param(
        model.s_N,
        model.s_O,
        default=0,
        initialize=NOA_Table,
        doc="Valid node-to-reuse pipeline arcs [-]",
    )
    model.p_FCA = Param(
        model.s_F,
        model.s_CP,
        default=0,
        initialize=df_parameters["FCA"],
        doc="Valid freshwater-to-completions pipeline arcs [-]",
    )
    model.p_RNA = Param(
        model.s_R,
        model.s_N,
        default=0,
        initialize=RNA_Table,
        doc="Valid treatment-to-node pipeline arcs [-]",
    )
    model.p_RKA = Param(
        model.s_R,
        model.s_K,
        default=0,
        initialize=RKA_Table,
        doc="Valid treatment-to-disposal pipeline arcs [-]",
    )
    model.p_SNA = Param(
        model.s_S,
        model.s_N,
        default=0,
        initialize=SNA_Table,
        doc="Valid storage-to-node pipeline arcs [-]",
    )
    model.p_SCA = Param(
        model.s_S,
        model.s_CP,
        default=0,
        initialize=SCA_Table,
        doc="Valid storage-to-completions pipeline arcs [-]",
    )
    model.p_SKA = Param(
        model.s_S,
        model.s_K,
        default=0,
        initialize=SKA_Table,
        doc="Valid storage-to-disposal pipeline arcs [-]",
    )
    model.p_SRA = Param(
        model.s_S,
        model.s_R,
        default=0,
        initialize=SRA_Table,
        doc="Valid storage-to-treatment pipeline arcs [-]",
    )
    model.p_SOA = Param(
        model.s_S,
        model.s_O,
        default=0,
        initialize=SOA_Table,
        doc="Valid storage-to-reuse pipeline arcs [-]",
    )

    model.p_PCT = Param(
        model.s_PP,
        model.s_CP,
        default=0,
        initialize=df_parameters["PCT"],
        doc="Valid production-to-completions trucking arcs [-]",
    )
    model.p_FCT = Param(
        model.s_F,
        model.s_CP,
        default=0,
        initialize=df_parameters["FCT"],
        doc="Valid freshwater-to-completions trucking arcs [-]",
    )
    model.p_PKT = Param(
        model.s_PP,
        model.s_K,
        default=0,
        initialize=df_parameters["PKT"],
        doc="Valid production-to-disposal trucking arcs [-]",
    )
    model.p_PST = Param(
        model.s_PP,
        model.s_S,
        default=0,
        initialize=PST_Table,
        doc="Valid production-to-storage trucking arcs [-]",
    )
    model.p_PRT = Param(
        model.s_PP,
        model.s_R,
        default=0,
        initialize=df_parameters["PRT"],
        doc="Valid production-to-treatment trucking arcs [-]",
    )
    model.p_POT = Param(
        model.s_PP,
        model.s_O,
        default=0,
        initialize=POT_Table,
        doc="Valid production-to-reuse trucking arcs [-]",
    )
    model.p_CKT = Param(
        model.s_CP,
        model.s_K,
        default=0,
        initialize=df_parameters["CKT"],
        doc="Valid completions-to-disposal trucking arcs [-]",
    )
    model.p_CST = Param(
        model.s_CP,
        model.s_S,
        default=0,
        initialize=CST_Table,
        doc="Valid completions-to-storage trucking arcs [-]",
    )
    model.p_CRT = Param(
        model.s_CP,
        model.s_R,
        default=0,
        initialize=df_parameters["CRT"],
        doc="Valid completions-to-treatment trucking arcs [-]",
    )
    model.p_CCT = Param(
        model.s_CP,
        model.s_CP,
        default=0,
        initialize=df_parameters["CCT"],
        doc="Valid completions-to-completions trucking arcs [-]",
    )
    model.p_SCT = Param(
        model.s_S,
        model.s_CP,
        default=0,
        initialize=SCT_Table,
        doc="Valid storage-to-completions trucking arcs [-]",
    )
    model.p_SKT = Param(
        model.s_S,
        model.s_K,
        default=0,
        initialize=SKT_Table,
        doc="Valid storage-to-disposal trucking arcs [-]",
    )
    model.p_RKT = Param(
        model.s_R,
        model.s_K,
        default=0,
        initialize=RKT_Table,
        doc="Valid treatment-to-disposal trucking arcs [-]",
    )
    df_parameters["LLT"] = {
        **df_parameters["PCT"],
        **df_parameters["CCT"],
        **df_parameters["CRT"],
        **df_parameters["CKT"],
        **df_parameters["FCT"],
        **df_parameters["PKT"],
        **df_parameters["PRT"],
    }
    model.p_LLT = Param(
        model.s_L,
        model.s_L,
        default=0,
        initialize=df_parameters["LLT"],
        doc="Valid location-to-location trucking arcs [-]",
    )

    if model.config.production_tanks == ProdTank.individual:
        model.p_PAL = Param(
            model.s_P,
            model.s_A,
            default=0,
            initialize=df_parameters["PAL"],
            doc="Valid pad-to-tank links [-]",
        )
    elif model.config.production_tanks == ProdTank.equalized:
        model.p_PAL = Param(
            model.s_P, model.s_A, default=0, doc="Valid pad-to-tank links [-]"
        )
    else:
        raise Exception("storage type not supported")

    # model.p_FCA.pprint()
    # model.p_PKT.pprint()
    # model.p_PKT.pprint()
    # model.p_PCA.pprint()
    # model.p_PNA.pprint()
    # model.p_CNA.pprint()
    # model.p_NNA.pprint()
    # model.p_PAL.pprint()
    # model.p_CCT.pprint()

    ## Define set parameters ##

    CompletionsDemandTable = {}

    ProductionTable = {}

    FlowbackTable = {}

    InitialPipelineCapacityTable = {}

    # COMMENT: For EXISTING/INITAL pipeline capacity (l,l_tilde)=(l_tilde=l); needs implemented!

    InitialDisposalCapacityTable = {}

    InitialStorageCapacityTable = {}

    InitialTreatmentCapacityTable = {}

    InitialReuseCapacityTable = {}

    FreshwaterSourcingAvailabilityTable = {}

    PadOffloadingCapacityTable = {}

    StorageOffloadingCapacityTable = {}

    ProcessingCapacityPadTable = {}

    ProcessingCapacityStorageTable = {}

    PipelineCapacityIncrementsTable = {("D0"): 0}

    DisposalCapacityIncrementsTable = {("I0"): 0}

    StorageDisposalCapacityIncrementsTable = {("C0"): 0}

    TruckingTimeTable = {}

    DisposalCapExTable = {("K02", "I0"): 0}

    StorageCapExTable = {}

    PipelineCapExTable = {}

    DisposalOperationalCostTable = {}

    TreatmentOperationalCostTable = {}

    ReuseOperationalCostTable = {}

    StorageOperationalCostTable = {}

    StorageOperationalCreditTable = {}

    PipelineOperationalCostTable = {}

    TruckingHourlyCostTable = {}

    FreshSourcingCostTable = {}

    InitialTankLevelTable = {}

    model.p_gamma_Completions = Param(
        model.s_P,
        model.s_T,
        default=0,
        initialize=df_parameters["CompletionsDemand"],
        doc="Completions water demand [bbl/day]",
    )
    if model.config.production_tanks == ProdTank.individual:
        model.p_beta_Production = Param(
            model.s_P,
            model.s_A,
            model.s_T,
            default=0,
            initialize=df_parameters["ProductionRates"],
            doc="Produced water supply forecast [bbl/day]",
        )
        model.p_sigma_ProdTank = Param(
            model.s_P, model.s_A, default=500, doc="Production tank capacity [bbl]"
        )
        model.p_lambda_ProdTank = Param(
            model.s_P,
            model.s_A,
            default=0,
            initialize=InitialTankLevelTable,
            doc="Initial water level in " "production tank [bbl]",
        )
    elif model.config.production_tanks == ProdTank.equalized:
        model.p_beta_Production = Param(
            model.s_P,
            model.s_T,
            default=0,
            initialize=df_parameters["PadRates"],
            doc="Produced water supply " "forecast [bbl/day]",
        )
        model.p_sigma_ProdTank = Param(
            model.s_P,
            default=500,
            initialize=df_parameters["ProductionTankCapacity"],
            doc="Combined capacity equalized " "production tanks [bbl]",
        )
        model.p_lambda_ProdTank = Param(
            model.s_P,
            default=0,
            initialize=InitialTankLevelTable,
            doc="Initial water level in " "equalized production tanks [bbl]",
        )
    else:
        raise Exception("storage type not supported")
    model.p_beta_Flowback = Param(
        model.s_P,
        model.s_T,
        default=0,
        initialize=df_parameters["FlowbackRates"],
        doc="Flowback supply forecast for a completions bad [bbl/day]",
    )

    model.p_sigma_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=0,
        initialize=InitialPipelineCapacityTable,
        doc="Initial daily pipeline capacity between two locations [bbl/day]",
    )
    model.p_sigma_Disposal = Param(
        model.s_K,
        default=0,
        initialize=df_parameters["InitialDisposalCapacity"],
        doc="Initial daily disposal capacity at disposal sites [bbl/day]",
    )
    model.p_sigma_Storage = Param(
        model.s_S,
        default=0,
        initialize=InitialStorageCapacityTable,
        doc="Initial storage capacity at storage site [bbl]",
    )
    model.p_sigma_PadStorage = Param(
        model.s_CP,
        default=0,
        initialize=df_parameters["CompletionsPadStorage"],
        doc="Storage capacity at completions site [bbl]",
    )
    model.p_sigma_Treatment = Param(
        model.s_R,
        default=0,
        initialize=df_parameters["TreatmentCapacity"],
        doc="Initial daily treatment capacity at treatment site [bbl/day]",
    )
    model.p_sigma_Reuse = Param(
        model.s_O,
        default=0,
        initialize=InitialReuseCapacityTable,
        doc="Initial daily reuse capacity at reuse site [bbl/day]",
    )
    model.p_sigma_Freshwater = Param(
        model.s_F,
        model.s_T,
        default=0,
        initialize=df_parameters["FreshwaterSourcingAvailability"],
        doc="daily freshwater sourcing capacity at freshwater source [bbl/day]",
    )

    # model.p_sigma_Disposal.pprint()
    # model.p_sigma_Freshwater.pprint()

    model.p_sigma_OffloadingPad = Param(
        model.s_P,
        default=9999999,
        initialize=df_parameters["PadOffloadingCapacity"],
        doc="Weekly truck offloading sourcing capacity per pad [bbl/day]",
    )
    model.p_sigma_OffloadingStorage = Param(
        model.s_S,
        default=9999999,
        initialize=StorageOffloadingCapacityTable,
        doc="Weekly truck offloading capacity per pad [bbl/day]",
    )
    model.p_sigma_MinTruckFlow = Param(
        default=0,
        initialize=df_parameters["MinTruckFlow"],
        doc="Minimum truck capacity [bbl]",
    )
    model.p_sigma_MaxTruckFlow = Param(
        default=0,
        initialize=df_parameters["MaxTruckFlow"],
        doc="Minimum truck capacity [bbl]",
    )
    model.p_sigma_ProcessingPad = Param(
        model.s_P,
        default=9999999,
        initialize=ProcessingCapacityPadTable,
        doc="Weekly processing (e.g. clarification) capacity per pad [bbl/day]",
    )
    model.p_sigma_ProcessingStorage = Param(
        model.s_S,
        default=9999999,
        initialize=ProcessingCapacityStorageTable,
        doc="Weekly processing (e.g. clarification) capacity per storage site [bbl/day]",
    )

    # COMMENT: Remove pipeline/disposal/storage capacity expansion increment parameters
    model.p_delta_Pipeline = Param(
        model.s_D,
        default=10,
        initialize=PipelineCapacityIncrementsTable,
        doc="Pipeline capacity installation/expansion increments [bbl/day]",
    )

    model.p_delta_Disposal = Param(
        model.s_I,
        default=10,
        initialize=DisposalCapacityIncrementsTable,
        doc="Disposal capacity installation/expansion increments [bbl/day]",
    )

    model.p_delta_Storage = Param(
        model.s_C,
        default=10,
        initialize=StorageDisposalCapacityIncrementsTable,
        doc="Storage capacity installation/expansion increments [bbl]",
    )

    model.p_delta_Truck = Param(default=110, doc="Truck capacity [bbl]")

    # COMMENT: Remove disposal/storage/pipeline lead time parameters
    model.p_tau_Disposal = Param(
        model.s_K, default=12, doc="Disposal construction/expansion lead time [days]"
    )

    model.p_tau_Storage = Param(
        model.s_S, default=12, doc="Storage constructin/expansion lead time [days]"
    )

    model.p_tau_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=12,
        doc="Pipeline construction/expansion lead time [days",
    )

    model.p_tau_Trucking = Param(
        model.s_L,
        model.s_L,
        default=9999999,
        initialize=df_parameters["DriveTimes"],
        doc="Drive time between locations [hr]",
    )

    # model.p_tau_Trucking.pprint()

    # COMMENT: Many more parameters missing. See documentation for details.

    model.p_lambda_Storage = Param(
        model.s_S, default=0, doc="Initial storage level at storage site [bbl]"
    )
    model.p_lambda_PadStorage = Param(
        model.s_CP, default=0, doc="Initial storage level at completions site [bbl]"
    )

    model.p_theta_PadStorage = Param(
        model.s_CP, default=0, doc="Terminal storage level at completions site [bbl]"
    )

    model.p_lambda_Pipeline = Param(
        model.s_L, model.s_L, default=9999999, doc="Pipeline segment length [miles]"
    )

    # COMMENT: Remove disosal/storage/pipeline capital cost parameters
    model.p_kappa_Disposal = Param(
        model.s_K,
        model.s_I,
        default=9999999,
        initialize=df_parameters["DisposalPipeCapEx"],
        doc="Disposal construction/expansion capital cost for selected increment [$/bbl]",
    )

    model.p_kappa_Storage = Param(
        model.s_S,
        model.s_C,
        default=9999999,
        initialize=StorageCapExTable,
        doc="Storage construction/expansion capital cost for selected increment [$/bbl]",
    )

    model.p_kappa_Pipeline = Param(
        model.s_L,
        model.s_L,
        model.s_D,
        default=9999999,
        initialize=PipelineCapExTable,
        doc="Pipeline construction/expansion capital cost for selected increment [$/bbl]",
    )

    model.p_pi_Disposal = Param(
        model.s_K,
        default=9999999,
        initialize=df_parameters["DisposalOperationalCost"],
        doc="Disposal operational cost [$/bbl]",
    )
    model.p_pi_Treatment = Param(
        model.s_R,
        default=9999999,
        initialize=df_parameters["TreatmentOperationalCost"],
        doc="Treatment operational cost [$/bbl",
    )
    model.p_pi_Reuse = Param(
        model.s_CP,
        default=9999999,
        initialize=df_parameters["ReuseOperationalCost"],
        doc="Reuse operational cost [$/bbl]",
    )
    model.p_pi_Storage = Param(
        model.s_S,
        default=9999999,
        initialize=StorageOperationalCostTable,
        doc="Storage deposit operational cost [$/bbl]",
    )
    model.p_rho_Storage = Param(
        model.s_S,
        default=0,
        initialize=StorageOperationalCreditTable,
        doc="Storage withdrawal operational credit [$/bbl]",
    )
    model.p_pi_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=0,
        initialize=df_parameters["PipingOperationalCost"],
        doc="Pipeline operational cost [$/bbl]",
    )
    model.p_pi_Trucking = Param(
        model.s_L,
        default=9999999,
        initialize=df_parameters["TruckingHourlyCost"],
        doc="Trucking hourly cost (by source) [$/hour]",
    )
    model.p_pi_Sourcing = Param(
        model.s_F,
        default=9999999,
        initialize=df_parameters["FreshSourcingCost"],
        doc="Fresh sourcing cost [$/bbl]",
    )

    # model.p_pi_Disposal.pprint()
    # model.p_pi_Reuse.pprint()
    # model.p_pi_Pipeline.pprint()

    model.p_M_Flow = Param(default=9999999, doc="Big-M flow parameter [bbl/day]")

    model.p_psi_FracDemand = Param(default=9999999, doc="Slack cost parameter [$]")
    model.p_psi_Production = Param(default=9999999, doc="Slack cost parameter [$]")
    model.p_psi_Flowback = Param(default=9999999, doc="Slack cost parameter [$]")
    model.p_psi_PipelineCapacity = Param(
        default=9999999, doc="Slack cost parameter [$]"
    )
    model.p_psi_StorageCapacity = Param(default=9999999, doc="Slack cost parameter [$]")
    model.p_psi_DisposalCapacity = Param(
        default=9999999, doc="Slack cost parameter [$]"
    )
    model.p_psi_TreatmentCapacity = Param(
        default=9999999, doc="Slack cost parameter [$]"
    )
    model.p_psi_ReuseCapacity = Param(default=9999999, doc="Slack cost parameter [$]")

    # model.p_sigma_Freshwater.pprint()

    ## Define objective function ##

    def ObjectiveFunctionRule(model):
        return model.v_Z == (
            model.v_C_TotalSourced
            + model.v_C_TotalDisposal
            + model.v_C_TotalTreatment
            + model.v_C_TotalReuse
            + model.v_C_TotalPiping
            + model.v_C_TotalStorage
            + model.v_C_TotalTrucking
            + model.v_C_DisposalCapEx
            + model.v_C_StorageCapEx
            + model.v_C_PipelineCapEx
            + model.v_C_Slack
            - model.v_R_TotalStorage
        )

    model.ObjectiveFunction = Constraint(
        rule=ObjectiveFunctionRule, doc="Objective function"
    )

    # model.ObjectiveFunction.pprint()

    ## Define constraints ##

    def CompletionsPadDemandBalanceRule(model, p, t):
        return model.p_gamma_Completions[p, t] == (
            sum(model.v_F_Piped[n, p, t] for n in model.s_N if model.p_NCA[n, p])
            + sum(
                model.v_F_Piped[p_tilde, p, t]
                for p_tilde in model.s_PP
                if model.p_PCA[p_tilde, p]
            )
            + sum(model.v_F_Piped[s, p, t] for s in model.s_S if model.p_SCA[s, p])
            + sum(
                model.v_F_Piped[p_tilde, p, t]
                for p_tilde in model.s_CP
                if model.p_CCA[p_tilde, p]
            )
            + sum(model.v_F_Sourced[f, p, t] for f in model.s_F if model.p_FCA[f, p])
            + sum(
                model.v_F_Trucked[p_tilde, p, t]
                for p_tilde in model.s_PP
                if model.p_PCT[p_tilde, p]
            )
            + sum(model.v_F_Trucked[s, p, t] for s in model.s_S if model.p_SCT[s, p])
            + sum(
                model.v_F_Trucked[p_tilde, p, t]
                for p_tilde in model.s_CP
                if model.p_CCT[p_tilde, p]
            )
            + sum(model.v_F_Trucked[f, p, t] for f in model.s_F if model.p_FCT[f, p])
            + model.v_F_PadStorageOut[p, t]
            - model.v_F_PadStorageIn[p, t]
            + model.v_S_FracDemand[p, t]
        )

    model.CompletionsPadDemandBalance = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadDemandBalanceRule,
        doc="Completions pad demand balance",
    )

    # model.CompletionsPadDemandBalance.pprint()

    def CompletionsPadStorageBalanceRule(model, p, t):
        if t == model.s_T.first():
            return (
                model.v_L_PadStorage[p, t]
                == model.p_lambda_PadStorage[p]
                + model.v_F_PadStorageIn[p, t]
                - model.v_F_PadStorageOut[p, t]
            )
        else:
            return (
                model.v_L_PadStorage[p, t]
                == model.v_L_PadStorage[p, model.s_T.prev(t)]
                + model.v_F_PadStorageIn[p, t]
                - model.v_F_PadStorageOut[p, t]
            )

    model.CompletionsPadStorageBalance = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadStorageBalanceRule,
        doc="Completions pad storage balance",
    )

    # model.CompletionsPadStorageBalance.pprint()

    def CompletionsPadStorageCapacityRule(model, p, t):
        return model.v_L_PadStorage[p, t] <= model.p_sigma_PadStorage[p]

    model.CompletionsPadStorageCapacity = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadStorageCapacityRule,
        doc="Completions pad storage capacity",
    )

    # model.CompletionsPadStorageCapacity.pprint()

    def TerminalCompletionsPadStorageLevelRule(model, p, t):
        if t == model.s_T.last():
            return model.v_L_PadStorage[p, t] <= model.p_theta_PadStorage[p]
        else:
            return Constraint.Skip

    model.TerminalCompletionsPadStorageLevel = Constraint(
        model.s_CP,
        model.s_T,
        rule=TerminalCompletionsPadStorageLevelRule,
        doc="Terminal completions pad storage level",
    )

    # model.TerminalCompletionsPadStorageLevel.pprint()

    def FreshwaterSourcingCapacityRule(model, f, t):
        if not (
            any(model.p_FCA[f, p] for p in model.s_CP)
            or any(model.p_FCT[f, p] for p in model.s_CP)
        ):
            return Constraint.Skip
        return (
            sum(model.v_F_Sourced[f, p, t] for p in model.s_CP if model.p_FCA[f, p])
            + sum(model.v_F_Trucked[f, p, t] for p in model.s_CP if model.p_FCT[f, p])
        ) <= model.p_sigma_Freshwater[f, t]

    model.FreshwaterSourcingCapacity = Constraint(
        model.s_F,
        model.s_T,
        rule=FreshwaterSourcingCapacityRule,
        doc="Freshwater sourcing capacity",
    )

    # model.FreshwaterSourcingCapacity.pprint()

    def CompletionsPadTruckOffloadingCapacityRule(model, p, t):
        return (
            sum(
                model.v_F_Trucked[p_tilde, p, t]
                for p_tilde in model.s_PP
                if model.p_PCT[p_tilde, p]
            )
            + sum(model.v_F_Trucked[s, p, t] for s in model.s_S if model.p_SCT[s, p])
            + sum(
                model.v_F_Trucked[p_tilde, p, t]
                for p_tilde in model.s_CP
                if model.p_CCT[p_tilde, p]
            )
            + sum(model.v_F_Trucked[f, p, t] for f in model.s_F if model.p_FCT[f, p])
        ) <= model.p_sigma_OffloadingPad[p]

    model.CompletionsPadTruckOffloadingCapacity = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadTruckOffloadingCapacityRule,
        doc="Completions pad truck offloading capacity",
    )

    def TrucksMaxCapacityRule(model, l, l_tilde, t):
        if model.p_LLT[l, l_tilde]:
            return (
                model.v_F_Trucked[l, l_tilde, t]
                <= model.p_sigma_MaxTruckFlow * model.vb_y_Truck[l, l_tilde, t]
            )
        else:
            return Constraint.Skip

    model.TrucksMaxCapacity = Constraint(
        model.s_L,
        model.s_L,
        model.s_T,
        rule=TrucksMaxCapacityRule,
        doc="Maximum amount of water that can be transported by trucks",
    )

    def TrucksMinCapacityRule(model, l, l_tilde, t):
        if model.p_LLT[l, l_tilde]:
            return (
                model.v_F_Trucked[l, l_tilde, t]
                >= model.p_sigma_MinTruckFlow * model.vb_y_Truck[l, l_tilde, t]
            )
        else:
            return Constraint.Skip

    model.TrucksMinCapacity = Constraint(
        model.s_L,
        model.s_L,
        model.s_T,
        rule=TrucksMinCapacityRule,
        doc="Minimum amount of water that can be transported by trucks",
    )

    #  model.CompletionsPadTruckOffloadingCapacity.pprint()

    def StorageSiteTruckOffloadingCapacityRule(model, s, t):
        return (
            sum(model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s])
            + sum(model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s])
            <= model.p_sigma_OffloadingStorage[s]
        )

    model.StorageSiteTruckOffloadingCapacity = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageSiteTruckOffloadingCapacityRule,
        doc="Storage site truck offloading capacity",
    )

    # model.StorageSiteTruckOffloadingCapacity.pprint()

    def StorageSiteProcessingCapacityRule(model, s, t):
        return (
            sum(model.v_F_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s])
            + sum(model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s])
            + sum(model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s])
            <= model.p_sigma_ProcessingStorage[s]
        )

    model.StorageSiteProcessingCapacity = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageSiteProcessingCapacityRule,
        doc="Storage site processing capacity",
    )

    # model.StorageSiteProcessingCapacity.pprint()

    if model.config.production_tanks == ProdTank.individual:

        def ProductionTankBalanceRule(model, p, a, t):
            if t == model.s_T.first():
                if p in model.s_P and a in model.s_A:
                    if model.p_PAL[p, a]:
                        return (
                            model.v_L_ProdTank[p, a, t]
                            == model.p_lambda_ProdTank[p, a]
                            + model.p_beta_Production[p, a, t]
                            - model.v_F_Drain[p, a, t]
                        )
                    else:
                        return Constraint.Skip
                else:
                    return Constraint.Skip
            else:
                if p in model.s_P and a in model.s_A:
                    if model.p_PAL[p, a]:
                        return (
                            model.v_L_ProdTank[p, a, t]
                            == model.v_L_ProdTank[p, a, model.s_T.prev(t)]
                            + model.p_beta_Production[p, a, t]
                            - model.v_F_Drain[p, a, t]
                        )
                    else:
                        return Constraint.Skip
                else:
                    return Constraint.Skip

        model.ProductionTankBalance = Constraint(
            model.s_P,
            model.s_A,
            model.s_T,
            rule=ProductionTankBalanceRule,
            doc="Production tank balance",
        )

    elif model.config.production_tanks == ProdTank.equalized:

        def ProductionTankBalanceRule(model, p, t):
            if t == model.s_T.first():
                if p in model.s_P:
                    return (
                        model.v_L_ProdTank[p, t]
                        == model.p_lambda_ProdTank[p]
                        + model.p_beta_Production[p, t]
                        + model.p_beta_Flowback[p, t]
                        - model.v_F_Drain[p, t]
                    )
                else:
                    return Constraint.Skip
            else:
                if p in model.s_P:
                    return (
                        model.v_L_ProdTank[p, t]
                        == model.v_L_ProdTank[p, model.s_T.prev(t)]
                        + model.p_beta_Production[p, t]
                        + model.p_beta_Flowback[p, t]
                        - model.v_F_Drain[p, t]
                    )
                else:
                    return Constraint.Skip

        model.ProductionTankBalance = Constraint(
            model.s_P,
            model.s_T,
            rule=ProductionTankBalanceRule,
            doc="Production tank balance",
        )
    else:
        raise Exception("storage type not supported")
    # model.ProductionTankBalance.pprint()

    if model.config.production_tanks == ProdTank.individual:

        def ProductionTankCapacityRule(model, p, a, t):
            if p in model.s_P and a in model.s_A:
                if model.p_PAL[p, a]:
                    return model.v_L_ProdTank[p, a, t] <= model.p_sigma_ProdTank[p, a]
                else:
                    return Constraint.Skip
            else:
                return Constraint.Skip

        model.ProductionTankCapacity = Constraint(
            model.s_P,
            model.s_A,
            model.s_T,
            rule=ProductionTankCapacityRule,
            doc="Production tank capacity",
        )
    elif model.config.production_tanks == ProdTank.equalized:

        def ProductionTankCapacityRule(model, p, t):
            if p in model.s_P:
                return model.v_L_ProdTank[p, t] <= model.p_sigma_ProdTank[p]
            else:
                return Constraint.Skip

        model.ProductionTankCapacity = Constraint(
            model.s_P,
            model.s_T,
            rule=ProductionTankCapacityRule,
            doc="Production tank capacity",
        )
    else:
        raise Exception("storage type not supported")
    # model.ProductionTankCapacity.pprint()

    if model.config.production_tanks == ProdTank.individual:

        def TankToPadProductionBalanceRule(model, p, t):
            return (
                sum(model.v_F_Drain[p, a, t] for a in model.s_A if model.p_PAL[p, a])
                == model.v_B_Production[p, t]
            )

        model.TankToPadProductionBalance = Constraint(
            model.s_P,
            model.s_T,
            rule=TankToPadProductionBalanceRule,
            doc="Tank-to-pad production balance",
        )
    elif model.config.production_tanks == ProdTank.equalized:

        def TankToPadProductionBalanceRule(model, p, t):
            return model.v_F_Drain[p, t] == model.v_B_Production[p, t]

        model.TankToPadProductionBalance = Constraint(
            model.s_P,
            model.s_T,
            rule=TankToPadProductionBalanceRule,
            doc="Tank-to-pad production balance",
        )
    else:
        raise Exception("storage type not supported")
    # model.TankToPadProductionBalance.pprint()

    if model.config.production_tanks == ProdTank.individual:

        def TerminalProductionTankLevelBalanceRule(model, p, a, t):
            if t == model.s_T.last():
                if p in model.s_P and a in model.s_A:
                    if model.p_PAL[p, a]:
                        return (
                            model.v_L_ProdTank[p, a, t] == model.p_lambda_ProdTank[p, a]
                        )
                    else:
                        return Constraint.Skip
                else:
                    return Constraint.Skip
            else:
                return Constraint.Skip

        model.TerminalProductionTankLevelBalance = Constraint(
            model.s_P,
            model.s_A,
            model.s_T,
            rule=TerminalProductionTankLevelBalanceRule,
            doc="Terminal production tank level balance",
        )
    elif model.config.production_tanks == ProdTank.equalized:

        def TerminalProductionTankLevelBalanceRule(model, p, t):
            if t == model.s_T.last():
                if p in model.s_P:
                    return model.v_L_ProdTank[p, t] == model.p_lambda_ProdTank[p]
                else:
                    return Constraint.Skip
            else:
                return Constraint.Skip

        model.TerminalProductionTankLevelBalance = Constraint(
            model.s_P,
            model.s_T,
            rule=TerminalProductionTankLevelBalanceRule,
            doc="Terminal production tank level balance",
        )
    else:
        raise Exception("storage type not supported")
    # model.TerminalProductionTankLevelBalance.pprint()

    def ProductionPadSupplyBalanceRule(model, p, t):
        return (
            model.v_B_Production[p, t]
            == sum(model.v_F_Piped[p, n, t] for n in model.s_N if model.p_PNA[p, n])
            + sum(
                model.v_F_Piped[p, p_tilde, t]
                for p_tilde in model.s_CP
                if model.p_PCA[p, p_tilde]
            )
            + sum(
                model.v_F_Piped[p, p_tilde, t]
                for p_tilde in model.s_PP
                if model.p_PPA[p, p_tilde]
            )
            + sum(
                model.v_F_Trucked[p, p_tilde, t]
                for p_tilde in model.s_CP
                if model.p_PCT[p, p_tilde]
            )
            + sum(model.v_F_Trucked[p, k, t] for k in model.s_K if model.p_PKT[p, k])
            + sum(model.v_F_Trucked[p, s, t] for s in model.s_S if model.p_PST[p, s])
            + sum(model.v_F_Trucked[p, r, t] for r in model.s_R if model.p_PRT[p, r])
            + sum(model.v_F_Trucked[p, o, t] for o in model.s_O if model.p_POT[p, o])
            + model.v_S_Production[p, t]
        )

    model.ProductionPadSupplyBalance = Constraint(
        model.s_PP,
        model.s_T,
        rule=ProductionPadSupplyBalanceRule,
        doc="Production pad supply balance",
    )

    # model.ProductionPadSupplyBalance.pprint()

    def CompletionsPadSupplyBalanceRule(model, p, t):
        return (
            model.v_B_Production[p, t]
            == sum(model.v_F_Piped[p, n, t] for n in model.s_N if model.p_CNA[p, n])
            + sum(
                model.v_F_Piped[p, p_tilde, t]
                for p_tilde in model.s_CP
                if model.p_CCA[p, p_tilde]
            )
            + sum(model.v_F_Trucked[p, k, t] for k in model.s_K if model.p_CKT[p, k])
            + sum(model.v_F_Trucked[p, s, t] for s in model.s_S if model.p_CST[p, s])
            + sum(model.v_F_Trucked[p, r, t] for r in model.s_R if model.p_CRT[p, r])
            + sum(
                model.v_F_Trucked[p, p_tilde, t]
                for p_tilde in model.s_CP
                if model.p_CCT[p, p_tilde]
            )
            + model.v_S_Flowback[p, t]
        )

    model.CompletionsPadSupplyBalance = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadSupplyBalanceRule,
        doc="Completions pad supply balance (i.e. flowback balance)",
    )

    # model.CompletionsPadSupplyBalance.pprint()

    def NetworkNodeBalanceRule(model, n, t):
        return sum(
            model.v_F_Piped[p, n, t] for p in model.s_PP if model.p_PNA[p, n]
        ) + sum(
            model.v_F_Piped[p, n, t] for p in model.s_CP if model.p_CNA[p, n]
        ) + sum(
            model.v_F_Piped[n_tilde, n, t]
            for n_tilde in model.s_N
            if model.p_NNA[n_tilde, n]
        ) == sum(
            model.v_F_Piped[n, n_tilde, t]
            for n_tilde in model.s_N
            if model.p_NNA[n, n_tilde]
        ) + sum(
            model.v_F_Piped[n, p, t] for p in model.s_CP if model.p_NCA[n, p]
        ) + sum(
            model.v_F_Piped[n, k, t] for k in model.s_K if model.p_NKA[n, k]
        ) + sum(
            model.v_F_Piped[n, r, t] for r in model.s_R if model.p_NRA[n, r]
        ) + sum(
            model.v_F_Piped[n, s, t] for s in model.s_S if model.p_NSA[n, s]
        ) + sum(
            model.v_F_Piped[n, o, t] for o in model.s_O if model.p_NOA[n, o]
        )

    model.NetworkBalance = Constraint(
        model.s_N, model.s_T, rule=NetworkNodeBalanceRule, doc="Network node balance"
    )

    # model.NetworkBalance.pprint()

    def BidirectionalFlowRule1(model, l, l_tilde, t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                return (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.BidirectionalFlow1 = Constraint(
        model.s_L,
        model.s_L,
        model.s_T,
        rule=BidirectionalFlowRule1,
        doc="Bi-directional flow",
    )

    # model.BidirectionalFlow1.pprint()

    def BidirectionalFlowRule2(model, l, l_tilde, t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                return (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.BidirectionalFlow2 = Constraint(
        model.s_L,
        model.s_L,
        model.s_T,
        rule=BidirectionalFlowRule2,
        doc="Bi-directional flow",
    )

    # model.BidirectionalFlow2.pprint()

    def StorageSiteBalanceRule(model, s, t):
        if t == model.s_T.first():
            return model.v_L_Storage[s, t] == model.p_lambda_Storage[s] + sum(
                model.v_F_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s]
            ) - sum(
                model.v_F_Piped[s, n, t] for n in model.s_N if model.p_SNA[s, n]
            ) - sum(
                model.v_F_Piped[s, p, t] for p in model.s_CP if model.p_SCA[s, p]
            ) - sum(
                model.v_F_Piped[s, k, t] for k in model.s_K if model.p_SKA[s, k]
            ) - sum(
                model.v_F_Piped[s, r, t] for r in model.s_R if model.p_SRA[s, r]
            ) - sum(
                model.v_F_Piped[s, o, t] for o in model.s_O if model.p_SOA[s, o]
            ) - sum(
                model.v_F_Trucked[s, p, t] for p in model.s_CP if model.p_SCT[s, p]
            ) - sum(
                model.v_F_Trucked[s, k, t] for k in model.s_K if model.p_SKT[s, k]
            )
        else:
            return model.v_L_Storage[s, t] == model.v_L_Storage[
                s, model.s_T.prev(t)
            ] + sum(
                model.v_F_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s]
            ) - sum(
                model.v_F_Piped[s, n, t] for n in model.s_N if model.p_SNA[s, n]
            ) - sum(
                model.v_F_Piped[s, p, t] for p in model.s_CP if model.p_SCA[s, p]
            ) - sum(
                model.v_F_Piped[s, k, t] for k in model.s_K if model.p_SKA[s, k]
            ) - sum(
                model.v_F_Piped[s, r, t] for r in model.s_R if model.p_SRA[s, r]
            ) - sum(
                model.v_F_Piped[s, o, t] for o in model.s_O if model.p_SOA[s, o]
            ) - sum(
                model.v_F_Trucked[s, p, t] for p in model.s_CP if model.p_SCT[s, p]
            ) - sum(
                model.v_F_Trucked[s, k, t] for k in model.s_K if model.p_SKT[s, k]
            )

    model.StorageSiteBalance = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageSiteBalanceRule,
        doc="Storage site balance rule",
    )

    # model.StorageSiteBalance.pprint()

    def PipelineCapacityExpansionRule(model, l, l_tilde):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                return (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.PipelineCapacityExpansion = Constraint(
        model.s_L,
        model.s_L,
        rule=PipelineCapacityExpansionRule,
        doc="Pipeline capacity construction/expansion",
    )

    # model.PipelineCapacityExpansion.pprint()

    def PipelineCapacityRule(model, l, l_tilde, t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                return model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.PipelineCapacity = Constraint(
        model.s_L,
        model.s_L,
        model.s_T,
        rule=PipelineCapacityRule,
        doc="Pipeline capacity",
    )

    # model.PipelineCapacity.pprint()

    def StorageCapacityExpansionRule(model, s):
        return (
            model.v_X_Capacity[s]
            == model.p_sigma_Storage[s] + model.v_S_StorageCapacity[s]
        )

    model.StorageCapacityExpansion = Constraint(
        model.s_S,
        rule=StorageCapacityExpansionRule,
        doc="Storage capacity construction/expansion",
    )

    # model.StorageCapacityExpansion.pprint()

    def StorageCapacityRule(model, s, t):
        return model.v_L_Storage[s, t] <= model.v_X_Capacity[s]

    model.StorageCapacity = Constraint(
        model.s_S, model.s_T, rule=StorageCapacityRule, doc="Storage capacity"
    )

    # model.StorageCapacity.pprint()

    def DisposalCapacityExpansionRule(model, k):
        return (
            model.v_D_Capacity[k]
            == model.p_sigma_Disposal[k] + model.v_S_DisposalCapacity[k]
        )

    model.DisposalCapacityExpansion = Constraint(
        model.s_K,
        rule=DisposalCapacityExpansionRule,
        doc="Disposal capacity construction/expansion",
    )

    # model.DisposalCapacityExpansion1.pprint()

    def DisposalCapacityRule(model, k, t):
        return (
            sum(model.v_F_Piped[n, k, t] for n in model.s_N if model.p_NKA[n, k])
            + sum(model.v_F_Piped[s, k, t] for s in model.s_S if model.p_SKA[s, k])
            + sum(model.v_F_Trucked[s, k, t] for s in model.s_S if model.p_SKT[s, k])
            + sum(model.v_F_Trucked[p, k, t] for p in model.s_PP if model.p_PKT[p, k])
            + sum(model.v_F_Trucked[p, k, t] for p in model.s_CP if model.p_CKT[p, k])
            + sum(model.v_F_Trucked[r, k, t] for r in model.s_R if model.p_RKT[r, k])
            <= model.v_D_Capacity[k]
        )

    model.DisposalCapacity = Constraint(
        model.s_K, model.s_T, rule=DisposalCapacityRule, doc="Disposal capacity"
    )

    # model.DisposalCapacity.pprint()

    def TreatmentCapacityRule(model, r, t):
        return (
            sum(model.v_F_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r])
            + sum(model.v_F_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r])
            + sum(model.v_F_Trucked[p, r, t] for p in model.s_PP if model.p_PRT[p, r])
            + sum(model.v_F_Trucked[p, r, t] for p in model.s_CP if model.p_CRT[p, r])
            <= model.p_sigma_Treatment[r] + model.v_S_TreatmentCapacity[r]
        )

    model.TreatmentCapacity = Constraint(
        model.s_R, model.s_T, rule=TreatmentCapacityRule, doc="Treatment capacity"
    )

    # model.TreatmentCapacity.pprint()

    def BeneficialReuseCapacityRule(model, o, t):
        return (
            sum(model.v_F_Piped[n, o, t] for n in model.s_N if model.p_NOA[n, o])
            + sum(model.v_F_Piped[s, o, t] for s in model.s_S if model.p_SOA[s, o])
            + sum(model.v_F_Trucked[p, o, t] for p in model.s_PP if model.p_POT[p, o])
            <= model.p_sigma_Reuse[o] + model.v_S_ReuseCapacity[o]
        )

    model.BeneficialReuseCapacity = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseCapacityRule,
        doc="Beneficial reuse capacity",
    )

    # model.BeneficialReuseCapacity.pprint()

    # COMMENT: Beneficial reuse capacity constraint has not been tested yet

    def FreshSourcingCostRule(model, f, p, t):
        return (
            model.v_C_Sourced[f, p, t]
            == (model.v_F_Sourced[f, p, t] + model.v_F_Trucked[f, p, t])
            * model.p_pi_Sourcing[f]
        )

    model.FreshSourcingCost = Constraint(
        model.s_F,
        model.s_CP,
        model.s_T,
        rule=FreshSourcingCostRule,
        doc="Fresh sourcing cost",
    )

    # model.FreshSourcingCost.pprint()

    def TotalFreshSourcingCostRule(model):
        return model.v_C_TotalSourced == sum(
            sum(sum(model.v_C_Sourced[f, p, t] for f in model.s_F) for p in model.s_CP)
            for t in model.s_T
        )

    model.TotalFreshSourcingCost = Constraint(
        rule=TotalFreshSourcingCostRule, doc="Total fresh sourcing cost"
    )

    # model.TotalFreshSourcingCost.pprint()

    def DisposalCostRule(model, k, t):
        return (
            model.v_C_Disposal[k, t]
            == (
                sum(model.v_F_Piped[n, k, t] for n in model.s_N if model.p_NKA[n, k])
                + sum(model.v_F_Piped[r, k, t] for r in model.s_R if model.p_RKA[r, k])
                + sum(model.v_F_Piped[s, k, t] for s in model.s_S if model.p_SKA[s, k])
                + sum(
                    model.v_F_Trucked[p, k, t] for p in model.s_PP if model.p_PKT[p, k]
                )
                + sum(
                    model.v_F_Trucked[p, k, t] for p in model.s_CP if model.p_CKT[p, k]
                )
                + sum(
                    model.v_F_Trucked[s, k, t] for s in model.s_S if model.p_SKT[s, k]
                )
                + sum(
                    model.v_F_Trucked[r, k, t] for r in model.s_R if model.p_RKT[r, k]
                )
            )
            * model.p_pi_Disposal[k]
        )

    model.DisposalCost = Constraint(
        model.s_K, model.s_T, rule=DisposalCostRule, doc="Disposal cost"
    )

    # model.DisposalCost.pprint()

    def TotalDisposalCostRule(model):
        return model.v_C_TotalDisposal == sum(
            sum(model.v_C_Disposal[k, t] for k in model.s_K) for t in model.s_T
        )

    model.TotalDisposalCost = Constraint(
        rule=TotalDisposalCostRule, doc="Total disposal cost"
    )

    # model.TotalDisposalCost.pprint()

    def TreatmentCostRule(model, r, t):
        return (
            model.v_C_Treatment[r, t]
            == (
                sum(model.v_F_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r])
                + sum(model.v_F_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r])
                + sum(
                    model.v_F_Trucked[p, r, t] for p in model.s_PP if model.p_PRT[p, r]
                )
                + sum(
                    model.v_F_Trucked[p, r, t] for p in model.s_CP if model.p_CRT[p, r]
                )
            )
            * model.p_pi_Treatment[r]
        )

    model.TreatmentCost = Constraint(
        model.s_R, model.s_T, rule=TreatmentCostRule, doc="Treatment cost"
    )

    # model.TreatmentCost.pprint()

    def TotalTreatmentCostRule(model):
        return model.v_C_TotalTreatment == sum(
            sum(model.v_C_Treatment[r, t] for r in model.s_R) for t in model.s_T
        )

    model.TotalTreatmentCost = Constraint(
        rule=TotalTreatmentCostRule, doc="Total treatment cost"
    )

    # model.TotalTreatmentCost.pprint()

    def CompletionsReuseCostRule(
        model,
        p,
        t,
    ):
        return model.v_C_Reuse[p, t] == (
            (
                sum(model.v_F_Piped[n, p, t] for n in model.s_N if model.p_NCA[n, p])
                + sum(
                    model.v_F_Piped[p_tilde, p, t]
                    for p_tilde in model.s_PP
                    if model.p_PCA[p_tilde, p]
                )
                + sum(model.v_F_Piped[s, p, t] for s in model.s_S if model.p_SCA[s, p])
                + sum(
                    model.v_F_Piped[p_tilde, p, t]
                    for p_tilde in model.s_CP
                    if model.p_CCA[p_tilde, p]
                )
                + sum(
                    model.v_F_Trucked[p_tilde, p, t]
                    for p_tilde in model.s_PP
                    if model.p_PCT[p_tilde, p]
                )
                + sum(
                    model.v_F_Trucked[p_tilde, p, t]
                    for p_tilde in model.s_CP
                    if model.p_CCT[p_tilde, p]
                )
                + sum(
                    model.v_F_Trucked[s, p, t] for s in model.s_S if model.p_SCT[s, p]
                )
            )
            * model.p_pi_Reuse[p]
        )

    model.CompletionsReuseCost = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsReuseCostRule,
        doc="Reuse completions cost",
    )

    # model.CompletionsReuseCost.pprint()

    def TotalCompletionsReuseCostRule(model):
        return model.v_C_TotalReuse == sum(
            sum(model.v_C_Reuse[p, t] for p in model.s_CP) for t in model.s_T
        )

    model.TotalCompletionsReuseCost = Constraint(
        rule=TotalCompletionsReuseCostRule, doc="Total completions reuse cost"
    )

    # model.TotalCompletionsReuseCost.pprint()

    def PipingCostRule(model, l, l_tilde, t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_CP:
            if model.p_CCA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l, l_tilde]:
                return (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Sourced[l, l_tilde, t]
                    * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.PipingCost = Constraint(
        model.s_L, model.s_L, model.s_T, rule=PipingCostRule, doc="Piping cost"
    )

    # model.PipingCost.pprint()

    def TotalPipingCostRule(model):
        return model.v_C_TotalPiping == (
            sum(
                sum(
                    sum(
                        model.v_C_Piped[p, p_tilde, t]
                        for p in model.s_PP
                        if model.p_PCA[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
                )
                + sum(
                    sum(
                        model.v_C_Piped[p, n, t]
                        for p in model.s_PP
                        if model.p_PNA[p, n]
                    )
                    for n in model.s_N
                )
                + sum(
                    sum(
                        model.v_C_Piped[p, p_tilde, t]
                        for p in model.s_PP
                        if model.p_PPA[p, p_tilde]
                    )
                    for p_tilde in model.s_PP
                )
                + sum(
                    sum(
                        model.v_C_Piped[p, n, t]
                        for p in model.s_CP
                        if model.p_CNA[p, n]
                    )
                    for n in model.s_N
                )
                + sum(
                    sum(
                        model.v_C_Piped[n, n_tilde, t]
                        for n in model.s_N
                        if model.p_NNA[n, n_tilde]
                    )
                    for n_tilde in model.s_N
                )
                + sum(
                    sum(
                        model.v_C_Piped[n, p, t] for n in model.s_N if model.p_NCA[n, p]
                    )
                    for p in model.s_CP
                )
                + sum(
                    sum(
                        model.v_C_Piped[n, k, t] for n in model.s_N if model.p_NKA[n, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_C_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s]
                    )
                    for s in model.s_S
                )
                + sum(
                    sum(
                        model.v_C_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r]
                    )
                    for r in model.s_R
                )
                + sum(
                    sum(
                        model.v_C_Piped[n, o, t] for n in model.s_N if model.p_NOA[n, o]
                    )
                    for o in model.s_O
                )
                + sum(
                    sum(
                        model.v_C_Piped[f, p, t] for f in model.s_F if model.p_FCA[f, p]
                    )
                    for p in model.s_CP
                )
                + sum(
                    sum(
                        model.v_C_Piped[r, n, t] for r in model.s_R if model.p_RNA[r, n]
                    )
                    for n in model.s_N
                )
                + sum(
                    sum(
                        model.v_C_Piped[r, k, t] for r in model.s_R if model.p_RKA[r, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_C_Piped[s, n, t] for s in model.s_S if model.p_SNA[s, n]
                    )
                    for n in model.s_N
                )
                + sum(
                    sum(
                        model.v_C_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r]
                    )
                    for r in model.s_R
                )
                + sum(
                    sum(
                        model.v_C_Piped[s, o, t] for s in model.s_S if model.p_SOA[s, o]
                    )
                    for o in model.s_O
                )
                + sum(
                    sum(
                        model.v_C_Piped[f, p, t] for f in model.s_F if model.p_FCA[f, p]
                    )
                    for p in model.s_CP
                )
                + sum(
                    sum(
                        model.v_C_Piped[p, p_tilde, t]
                        for p in model.s_CP
                        if model.p_CCA[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
                )
                for t in model.s_T
            )
        )

    model.TotalPipingCost = Constraint(
        rule=TotalPipingCostRule, doc="Total piping cost"
    )

    # model.TotalPipingCost.pprint()

    def StorageDepositCostRule(model, s, t):
        return model.v_C_Storage[s, t] == (
            (
                sum(model.v_F_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s])
                + sum(
                    model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s]
                )
            )
            * model.p_pi_Storage[s]
        )

    model.StorageDepositCost = Constraint(
        model.s_S, model.s_T, rule=StorageDepositCostRule, doc="Storage deposit cost"
    )

    # model.StorageDepositCost.pprint()

    def TotalStorageCostRule(model):
        return model.v_C_TotalStorage == sum(
            sum(model.v_C_Storage[s, t] for s in model.s_S) for t in model.s_T
        )

    model.TotalStorageCost = Constraint(
        rule=TotalStorageCostRule, doc="Total storage deposit cost"
    )

    # model.TotalStorageCost.pprint()

    def StorageWithdrawalCreditRule(model, s, t):
        return model.v_R_Storage[s, t] == (
            (
                sum(model.v_F_Piped[s, n, t] for n in model.s_N if model.p_SNA[s, n])
                + sum(model.v_F_Piped[s, p, t] for p in model.s_CP if model.p_SCA[s, p])
                + sum(model.v_F_Piped[s, k, t] for k in model.s_K if model.p_SKA[s, k])
                + sum(model.v_F_Piped[s, r, t] for r in model.s_R if model.p_SRA[s, r])
                + sum(model.v_F_Piped[s, o, t] for o in model.s_O if model.p_SOA[s, o])
                + sum(
                    model.v_F_Trucked[s, p, t] for p in model.s_CP if model.p_SCT[s, p]
                )
                + sum(
                    model.v_F_Trucked[s, k, t] for k in model.s_K if model.p_SKT[s, k]
                )
            )
            * model.p_rho_Storage[s]
        )

    model.StorageWithdrawalCredit = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageWithdrawalCreditRule,
        doc="Storage withdrawal credit",
    )

    # model.StorageWithdrawalCredit.pprint()

    def TotalStorageWithdrawalCreditRule(model):
        return model.v_R_TotalStorage == sum(
            sum(model.v_R_Storage[s, t] for s in model.s_S) for t in model.s_T
        )

    model.TotalStorageWithdrawalCredit = Constraint(
        rule=TotalStorageWithdrawalCreditRule, doc="Total storage withdrawal credit"
    )

    # model.TotalStorageWithdrawalCredit.pprint()

    def TruckingCostRule(model, l, l_tilde, t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_K:
            if model.p_PKT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_S:
            if model.p_PST[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_R:
            if model.p_PRT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_O:
            if model.p_POT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_K:
            if model.p_CKT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_CP:
            if model.p_CCT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_S:
            if model.p_CST[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_R:
            if model.p_CRT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKT[l, l_tilde]:
                return (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.TruckingCost = Constraint(
        model.s_L, model.s_L, model.s_T, rule=TruckingCostRule, doc="Trucking cost"
    )

    # model.TruckingCost.pprint()

    def TotalTruckingCostRule(model):
        return model.v_C_TotalTrucking == (
            sum(
                sum(
                    sum(
                        model.v_C_Trucked[p, p_tilde, t]
                        for p in model.s_PP
                        if model.p_PCT[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
                )
                + sum(
                    sum(
                        model.v_C_Trucked[p, k, t]
                        for p in model.s_PP
                        if model.p_PKT[p, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_C_Trucked[p, s, t]
                        for p in model.s_PP
                        if model.p_PST[p, s]
                    )
                    for s in model.s_S
                )
                + sum(
                    sum(
                        model.v_C_Trucked[p, r, t]
                        for p in model.s_PP
                        if model.p_PRT[p, r]
                    )
                    for r in model.s_R
                )
                + sum(
                    sum(
                        model.v_C_Trucked[p, o, t]
                        for p in model.s_PP
                        if model.p_POT[p, o]
                    )
                    for o in model.s_O
                )
                + sum(
                    sum(
                        model.v_C_Trucked[p, k, t]
                        for p in model.s_CP
                        if model.p_CKT[p, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_C_Trucked[p, s, t]
                        for p in model.s_CP
                        if model.p_CST[p, s]
                    )
                    for s in model.s_S
                )
                + sum(
                    sum(
                        model.v_C_Trucked[p, r, t]
                        for p in model.s_CP
                        if model.p_CRT[p, r]
                    )
                    for r in model.s_R
                )
                + sum(
                    sum(
                        model.v_C_Trucked[s, p, t]
                        for s in model.s_S
                        if model.p_SCT[s, p]
                    )
                    for p in model.s_CP
                )
                + sum(
                    sum(
                        model.v_C_Trucked[s, k, t]
                        for s in model.s_S
                        if model.p_SKT[s, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_C_Trucked[r, k, t]
                        for r in model.s_R
                        if model.p_RKT[r, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_C_Trucked[f, p, t]
                        for f in model.s_F
                        if model.p_FCT[f, p]
                    )
                    for p in model.s_CP
                )
                + sum(
                    sum(
                        model.v_C_Trucked[p, p_tilde, t]
                        for p in model.s_CP
                        if model.p_CCT[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
                )
                for t in model.s_T
            )
        )

    model.TotalTruckingCost = Constraint(
        rule=TotalTruckingCostRule, doc="Total trucking cost"
    )

    # model.TotalTruckingCost.pprint()

    def SlackCostsRule(model):
        return model.v_C_Slack == (
            sum(
                sum(
                    model.v_S_FracDemand[p, t] * model.p_psi_FracDemand
                    for p in model.s_CP
                )
                for t in model.s_T
            )
            + sum(
                sum(
                    model.v_S_Production[p, t] * model.p_psi_Production
                    for p in model.s_PP
                )
                for t in model.s_T
            )
            + sum(
                sum(model.v_S_Flowback[p, t] * model.p_psi_Flowback for p in model.s_CP)
                for t in model.s_T
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[p, p_tilde]
                    for p in model.s_PP
                    if model.p_PCA[p, p_tilde]
                )
                for p_tilde in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[p, n]
                    for p in model.s_PP
                    if model.p_PNA[p, n]
                )
                for n in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[p, p_tilde]
                    for p in model.s_PP
                    if model.p_PPA[p, p_tilde]
                )
                for p_tilde in model.s_PP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[p, n]
                    for p in model.s_CP
                    if model.p_CNA[p, n]
                )
                for n in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, n_tilde]
                    for n in model.s_N
                    if model.p_NNA[n, n_tilde]
                )
                for n_tilde in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, p]
                    for n in model.s_N
                    if model.p_NCA[n, p]
                )
                for p in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, k]
                    for n in model.s_N
                    if model.p_NKA[n, k]
                )
                for k in model.s_K
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, s]
                    for n in model.s_N
                    if model.p_NSA[n, s]
                )
                for s in model.s_S
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, r]
                    for n in model.s_N
                    if model.p_NRA[n, r]
                )
                for r in model.s_R
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, o]
                    for n in model.s_N
                    if model.p_NOA[n, o]
                )
                for o in model.s_O
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[f, p]
                    for f in model.s_F
                    if model.p_FCA[f, p]
                )
                for p in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[r, n]
                    for r in model.s_R
                    if model.p_RNA[r, n]
                )
                for n in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[r, k]
                    for r in model.s_R
                    if model.p_RKA[r, k]
                )
                for k in model.s_K
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, n]
                    for s in model.s_S
                    if model.p_SNA[s, n]
                )
                for n in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, p]
                    for s in model.s_S
                    if model.p_SCA[s, p]
                )
                for p in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, k]
                    for s in model.s_S
                    if model.p_SKA[s, k]
                )
                for k in model.s_K
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, r]
                    for s in model.s_S
                    if model.p_SRA[s, r]
                )
                for r in model.s_R
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, o]
                    for s in model.s_S
                    if model.p_SOA[s, o]
                )
                for o in model.s_O
            )
            + sum(
                model.v_S_StorageCapacity[s] * model.p_psi_StorageCapacity
                for s in model.s_S
            )
            + sum(
                model.v_S_DisposalCapacity[k] * model.p_psi_DisposalCapacity
                for k in model.s_K
            )
            + sum(
                model.v_S_TreatmentCapacity[r] * model.p_psi_TreatmentCapacity
                for r in model.s_R
            )
            + sum(
                model.v_S_ReuseCapacity[o] * model.p_psi_ReuseCapacity
                for o in model.s_O
            )
        )

    model.SlackCosts = Constraint(rule=SlackCostsRule, doc="Slack costs")

    def ReuseDestinationDeliveriesRule(model, p, t):
        return model.v_F_ReuseDestination[p, t] == sum(
            model.v_F_Piped[l, p, t] + model.v_F_Trucked[l, p, t] for l in model.s_L
        )

    model.ReuseDestinationDeliveries = Constraint(
        model.s_CP,
        model.s_T,
        rule=ReuseDestinationDeliveriesRule,
        doc="Reuse destinations volume",
    )

    # model.ReuseDestinationDeliveries.pprint()

    def DisposalDestinationDeliveriesRule(model, k, t):
        return model.v_F_DisposalDestination[k, t] == sum(
            model.v_F_Piped[l, k, t] + model.v_F_Trucked[l, k, t] for l in model.s_L
        )

    model.DisposalDestinationDeliveries = Constraint(
        model.s_K,
        model.s_T,
        rule=DisposalDestinationDeliveriesRule,
        doc="Disposal destinations volume",
    )

    # model.DisposalDestinationDeliveries.pprint()

    def TreatmentDestinationDeliveriesRule(model, r, t):
        return model.v_F_TreatmentDestination[r, t] == sum(
            model.v_F_Piped[l, r, t] + model.v_F_Trucked[l, r, t] for l in model.s_L
        )

    model.TreatmentDestinationDeliveries = Constraint(
        model.s_R,
        model.s_T,
        rule=TreatmentDestinationDeliveriesRule,
        doc="Treatment destinations volume",
    )

    # model.TreatmentDestinationDeliveries.pprint()

    ## Fixing Decision Variables ##

    # # model.v_F_Piped['PP1','SS1'].fix(3500)

    # model.vb_y_Disposal['K02','I0'].fix(0)

    # model.v_F_PadStorageIn['CP01','T2'].fix(2000)

    ## Define Objective and Solve Statement ##

    model.objective = Objective(
        expr=model.v_Z, sense=minimize, doc="Objective function"
    )

    return model


if __name__ == "__main__":
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "ProductionTanks",
        "FreshwaterSources",
        "StorageSites",
        "SWDSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
    ]
    parameter_list = [
        "FCA",
        "PCT",
        "FCT",
        "CCT",
        "PKT",
        "PRT",
        "CKT",
        "CRT",
        "PAL",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "ProductionTankCapacity",
        "InitialDisposalCapacity",
        "CompletionsPadStorage",
        "TreatmentCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "DriveTimes",
        "DisposalPipeCapEx",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PipingOperationalCost",
        "TruckingHourlyCost",
        "FreshSourcingCost",
        "ProductionRates",
    ]
    with resources.path(
        "pareto.case_studies", "EXAMPLE_INPUT_DATA_FILE_generic_operational_model.xlsx"
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    operational_model = create_model(
        df_sets,
        df_parameters,
        default={
            "has_pipeline_constraints": True,
            "production_tanks": ProdTank.individual,
        },
    )

    # import pyomo solver
    opt = get_solver("gurobi")
    # solve mathematical model
    results = opt.solve(operational_model, tee=True)
    results.write()
    print("\nDisplaying Solution\n" + "-" * 60)
    # pyomo_postprocess(None, model, results)
