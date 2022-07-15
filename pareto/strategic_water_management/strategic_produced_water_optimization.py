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
# - Implemented calculation of maximum flows based on pipeline diameters

# Import
from cmath import nan
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
    Any,
    units as pyunits,
    Block,
    Suffix,
    TransformationFactory,
    value,
)

from pyomo.core.base.constraint import simple_constraint_rule
from pyomo.core.expr.current import identify_variables

# from gurobipy import *
from pyomo.common.config import ConfigBlock, ConfigValue, In
from enum import Enum

from pareto.utilities.solvers import get_solver, set_timeout
from pyomo.opt import TerminationCondition


class Objectives(Enum):
    cost = 0
    reuse = 1


class PipelineCapacity(Enum):
    calculated = 0
    input = 1


class PipelineCost(Enum):
    distance_based = 0
    capacity_based = 1


class IncludeNodeCapacity(Enum):
    false = 0
    true = 1


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
    "objective",
    ConfigValue(
        default=Objectives.cost,
        domain=In(Objectives),
        description="alternate objectives selection",
        doc="Alternate objective functions (i.e., minimize cost, maximize reuse)",
    ),
)

CONFIG.declare(
    "pipeline_capacity",
    ConfigValue(
        default=PipelineCapacity.input,
        domain=In(PipelineCapacity),
        description="alternate pipeline capacity selection",
        doc="""Alternate pipeline capacity selection (calculated or input)
        ***default*** - PipelineCapacity.input
        **Valid Values:** - {
        **PipelineCapacity.input** - use input for pipeline capacity,
        **PipelineCapacity.calculated** - calculate pipeline capacity from pipeline diameters 
        }""",
    ),
)

CONFIG.declare(
    "pipeline_cost",
    ConfigValue(
        default=PipelineCost.capacity_based,
        domain=In(PipelineCost),
        description="alternate pipeline cost selection",
        doc="""Alternate pipeline capex cost structures (distance or capacity based)
        ***default*** - PipelineCost.capacity_based
        **Valid Values:** - {
        **PipelineCost.capacity_based** - use pipeline capacities and rate in [currency/volume] to calculate pipeline capex costs,
        **PipelineCost.distance_based** - use pipeline distances and rate in [currency/(diameter-distance)] to calculate pipeline capex costs
        }""",
    ),
)

CONFIG.declare(
    "node_capacity",
    ConfigValue(
        default=IncludeNodeCapacity.true,
        domain=In(IncludeNodeCapacity),
        description="Node Capacity",
        doc="""Selection to include Node Capacity
        ***default*** - IncludeNodeCapacity.True
        **Valid Values:** - {
        **IncludeNodeCapacity.True** - Include network node capacity constraints,
        **IncludeNodeCapacity.Fales** - Exclude network node capacity constraints
        }""",
    ),
)
# Currency base units are not inherently defined by default
pyunits.load_definitions_from_strings(["USD = [currency]"])

# return the units container used for strategic model
# this is needed for the testing_strategic_model.py for checking units consistency
def get_strategic_model_unit_container():
    return pyunits


# Creation of a Concrete Model


def create_model(df_sets, df_parameters, default={}):
    model = ConcreteModel()

    # import config dictionary
    model.config = CONFIG(default)
    model.type = "strategic"
    model.df_sets = df_sets
    model.df_parameters = df_parameters

    # Convert user unit selection to a user_units dictionary
    model.user_units = {}
    for user_input in model.df_parameters["Units"]:
        # Concentration is a relationship between two units, so requires some manipulation from user input
        if user_input == "concentration":
            split = model.df_parameters["Units"][user_input].split("/")
            mass = split[0]
            vol = split[1]
            exec(
                "model.user_units['concentration'] = pyunits.%s / pyunits.%s"
                % (mass, vol)
            )
        # Pyunits defines oil_bbl separately from bbl. Users will see 'bbl', but pyunits are defined in oil_bbl
        elif user_input == "volume":
            user_volume = model.df_parameters["Units"][user_input]
            if user_volume == "bbl":
                exec("model.user_units['volume'] = pyunits.%s" % ("oil_bbl"))
            elif user_volume == "kbbl":
                exec("model.user_units['volume'] = pyunits.%s" % ("koil_bbl"))

        # Decision Period is not a user_unit. We will define this as a separate variable.
        elif user_input == "decision period":
            exec(
                "model.decision_period = pyunits.%s"
                % model.df_parameters["Units"][user_input]
            )
        # All other units can be interpreted directly from user input
        else:
            exec(
                "model.user_units['%s'] = pyunits.%s"
                % (user_input, df_parameters["Units"][user_input])
            )

    model.model_units = {
        "volume": pyunits.koil_bbl,
        "distance": pyunits.mile,
        "diameter": pyunits.inch,
        "concentration": pyunits.kg / pyunits.liter,
        "currency": pyunits.kUSD,
    }

    # Units that are most helpful for troubleshooting
    model.unscaled_model_display_units = {
        "volume": pyunits.oil_bbl,
        "distance": pyunits.mile,
        "diameter": pyunits.inch,
        "concentration": pyunits.mg / pyunits.liter,
        "currency": pyunits.USD,
    }

    # Defining compound units
    model.user_units["volume_time"] = (
        model.user_units["volume"] / model.user_units["time"]
    )
    model.user_units["currency_time"] = (
        model.user_units["currency"] / model.user_units["time"]
    )
    model.user_units["pipe_cost_distance"] = model.user_units["currency"] / (
        model.user_units["diameter"] * model.user_units["distance"]
    )
    model.user_units["pipe_cost_capacity"] = model.user_units["currency"] / (
        model.user_units["volume"] / model.user_units["time"]
    )
    model.user_units["currency_volume"] = (
        model.user_units["currency"] / model.user_units["volume"]
    )
    model.user_units["currency_volume_time"] = (
        model.user_units["currency"] / model.user_units["volume_time"]
    )

    model.model_units["volume_time"] = (
        model.model_units["volume"] / model.decision_period
    )
    model.model_units["currency_time"] = (
        model.model_units["currency"] / model.decision_period
    )
    model.model_units["pipe_cost_distance"] = model.model_units["currency"] / (
        model.model_units["diameter"] * model.model_units["distance"]
    )
    model.model_units["pipe_cost_capacity"] = model.model_units["currency"] / (
        model.model_units["volume"] / model.decision_period
    )
    model.model_units["currency_volume"] = (
        model.model_units["currency"] / model.model_units["volume"]
    )
    model.model_units["currency_volume_time"] = (
        model.model_units["currency"] / model.model_units["volume_time"]
    )

    model.unscaled_model_display_units["volume_time"] = (
        model.unscaled_model_display_units["volume"] / model.decision_period
    )
    model.unscaled_model_display_units["currency_time"] = (
        model.unscaled_model_display_units["currency"] / model.decision_period
    )
    model.unscaled_model_display_units[
        "pipe_cost_distance"
    ] = model.unscaled_model_display_units["currency"] / (
        model.unscaled_model_display_units["diameter"]
        * model.unscaled_model_display_units["distance"]
    )
    model.unscaled_model_display_units[
        "pipe_cost_capacity"
    ] = model.unscaled_model_display_units["currency"] / (
        model.unscaled_model_display_units["volume"] / model.decision_period
    )
    model.unscaled_model_display_units["currency_volume"] = (
        model.unscaled_model_display_units["currency"]
        / model.unscaled_model_display_units["volume"]
    )
    model.unscaled_model_display_units["currency_volume_time"] = (
        model.unscaled_model_display_units["currency"]
        / model.unscaled_model_display_units["volume_time"]
    )

    # Create dictionary to map model units to user units to assist generating results in the user units
    model.model_to_user_units = {}
    for unit in model.model_units:
        model_unit = model.model_units[unit].to_string()
        if "/" in model_unit:
            model_unit = "(" + model_unit + ")"
        user_unit = model.user_units[unit]
        model.model_to_user_units[model_unit] = user_unit

    # Create dictionary to map model units to user units to assist generating results in units relative to time discretization
    model.model_to_unscaled_model_display_units = {}
    for unit in model.model_units:
        model_unit = model.model_units[unit].to_string()
        if "/" in model_unit:
            model_unit = "(" + model_unit + ")"
        developer_output = model.unscaled_model_display_units[unit]
        model.model_to_unscaled_model_display_units[model_unit] = developer_output

    model.proprietary_data = df_parameters["proprietary_data"][0]

    ## Define sets ##

    model.s_T = Set(
        initialize=model.df_sets["TimePeriods"], doc="Time Periods", ordered=True
    )
    model.s_PP = Set(initialize=model.df_sets["ProductionPads"], doc="Production Pads")
    model.s_CP = Set(
        initialize=model.df_sets["CompletionsPads"], doc="Completions Pads"
    )
    model.s_P = Set(initialize=(model.s_PP | model.s_CP), doc="Pads")
    model.s_F = Set(
        initialize=model.df_sets["FreshwaterSources"], doc="Freshwater Sources"
    )
    model.s_K = Set(initialize=model.df_sets["SWDSites"], doc="Disposal Sites")
    model.s_S = Set(initialize=model.df_sets["StorageSites"], doc="Storage Sites")
    model.s_R = Set(initialize=model.df_sets["TreatmentSites"], doc="Treatment Sites")
    model.s_O = Set(initialize=model.df_sets["ReuseOptions"], doc="Reuse Options")
    model.s_N = Set(initialize=model.df_sets["NetworkNodes"], doc="Network Nodes")
    model.s_W = Set(
        initialize=model.df_sets["WaterQualityComponents"],
        doc="Water Quality Components",
    )

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
    model.s_D = Set(
        initialize=model.df_sets["PipelineDiameters"], doc="Pipeline diameters"
    )
    model.s_C = Set(
        initialize=model.df_sets["StorageCapacities"], doc="Storage capacities"
    )
    model.s_J = Set(
        initialize=model.df_sets["TreatmentCapacities"], doc="Treatment capacities"
    )
    model.s_I = Set(
        initialize=model.df_sets["InjectionCapacities"],
        doc="Injection (i.e. disposal) capacities",
    )

    model.s_B = Set(
        initialize=model.df_sets["TreatmentTechnologies"],
        doc="Treatment Technologies")

    # model.s_P.pprint()
    # model.s_L.pprint()

    ## Define continuous variables ##

    model.v_Z = Var(
        within=Reals,
        units=model.model_units["currency"],
        doc="Objective function variable [currency]",
    )

    model.v_F_Piped = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Produced water quantity piped from location l to location l [volume/time]",
    )
    model.v_F_Trucked = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Produced water quantity trucked from location l to location l [volume/time]",
    )
    model.v_F_Sourced = Var(
        model.s_F,
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Fresh water sourced from source f to completions pad p [volume/time]",
    )

    model.v_F_PadStorageIn = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Water put into completions pad storage [volume/time]",
    )
    model.v_F_PadStorageOut = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Water from completions pad storage used for fracturing [volume/time]",
    )
    model.v_F_WaterRemoved = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Water leftover from the treatment process [volume/time]",
    )

    model.v_L_Storage = Var(
        model.s_S,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume"],
        doc="Water level at storage site [volume]",
    )
    model.v_L_PadStorage = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume"],
        doc="Water level in completions pad storage [volume]",
    )

    model.v_F_TotalTrucked = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume water trucked [volume]",
    )
    model.v_F_TotalSourced = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume freshwater sourced [volume]",
    )
    model.v_F_TotalDisposed = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume of water disposed [volume]",
    )
    model.v_F_TotalReused = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume of produced water reused [volume]",
    )

    model.v_C_Piped = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of piping produced water from location l to location l [currency/time]",
    )
    model.v_C_Trucked = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of trucking produced water from location l to location l [currency/time]",
    )
    model.v_C_Sourced = Var(
        model.s_F,
        model.s_CP,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of sourcing fresh water from source f to completion pad p [currency/time]",
    )
    model.v_C_Disposal = Var(
        model.s_K,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of injecting produced water at disposal site [currency/time]",
    )
    model.v_C_Treatment = Var(
        model.s_R,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of treating produced water at treatment site [currency/time]",
    )
    model.v_C_Reuse = Var(
        model.s_CP,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of reusing produced water at completions site [currency/time]",
    )
    model.v_C_Storage = Var(
        model.s_S,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of storing produced water at storage site [currency/time]",
    )
    model.v_R_Storage = Var(
        model.s_S,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Credit for retrieving stored produced water from storage site [currency/time]",
    )

    model.v_C_TotalSourced = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of sourcing freshwater [currency]",
    )
    model.v_C_TotalDisposal = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of injecting produced water [currency]",
    )
    model.v_C_TotalTreatment = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of treating produced water [currency]",
    )
    model.v_C_TotalReuse = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of reusing produced water [currency]",
    )
    model.v_C_TotalPiping = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of piping produced water [currency]",
    )
    model.v_C_TotalStorage = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of storing produced water [currency]",
    )
    model.v_C_TotalTrucking = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of trucking produced water [currency]",
    )
    model.v_C_Slack = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of slack variables [currency]",
    )
    model.v_R_TotalStorage = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total credit for withdrawing produced water [currency]",
    )

    model.v_F_ReuseDestination = Var(
        model.s_CP,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to completions pad [volume/time]",
    )
    model.v_F_DisposalDestination = Var(
        model.s_K,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to disposal site [volume/time]",
    )
    model.v_F_BeneficialReuseDestination = Var(
        model.s_O,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to Beneficial Reuse Site [volume/time]",
    )
    model.v_F_CompletionsDestination = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to completions pad that meet completions demand [volume/time]",
    )

    model.v_D_Capacity = Var(
        model.s_K,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Disposal capacity at a disposal site [volume/time]",
    )
    model.v_X_Capacity = Var(
        model.s_S,
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Storage capacity at a storage site [volume]",
    )
    model.v_T_Capacity = Var(
        model.s_R,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Treatment capacity at a treatment site [volume/time]",
    )
    model.v_F_Capacity = Var(
        model.s_L,
        model.s_L,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Flow capacity along pipeline arc [volume/time]",
    )

    model.v_C_DisposalCapEx = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Capital cost of constructing or expanding disposal capacity [currency]",
    )
    model.v_C_PipelineCapEx = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Capital cost of constructing or expanding piping capacity [currency]",
    )
    model.v_C_StorageCapEx = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Capital cost of constructing or expanding storage capacity [currency]",
    )
    model.v_C_TreatmentCapEx = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Capital cost of constructing or expanding treatment capacity [currency]",
    )

    model.v_S_FracDemand = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Slack variable to meet the completions demand [volume/time]",
    )
    model.v_S_Production = Var(
        model.s_PP,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Slack variable to process the produced water production [volume/time]",
    )
    model.v_S_Flowback = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Slack variable to proces flowback water production [volume/time]",
    )
    model.v_S_PipelineCapacity = Var(
        model.s_L,
        model.s_L,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Slack variable to provide necessary pipeline capacity [volume/time]",
    )
    model.v_S_StorageCapacity = Var(
        model.s_S,
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Slack variable to provide necessary storage capacity [volume]",
    )
    model.v_S_DisposalCapacity = Var(
        model.s_K,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Slack variable to provide necessary disposal capacity [volume/time]",
    )
    model.v_S_TreatmentCapacity = Var(
        model.s_R,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Slack variable to provide necessary treatment capacity [volume/time]",
    )
    model.v_S_ReuseCapacity = Var(
        model.s_O,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Slack variable to provide necessary reuse capacity [volume/time]",
    )

    model.v_F_StorageEvaporationStream = Var(
        model.s_S,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        doc="Water at storage lost to evaporation [bbl/week]",
    )

    model.v_F_ResidualWater = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Flow of residual out at a treatment site [volume/time]",
    )

    model.v_F_TreatedWater = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Flow of treated water out at a treatment site [volume/time]",
    )

    ## Define binary variables ##

    model.vb_y_Pipeline = Var(
        model.s_L,
        model.s_L,
        model.s_D,
        within=Binary,
        initialize=0,
        doc="New pipeline installed between one location and another location with specific diameter",
    )
    model.vb_y_Storage = Var(
        model.s_S,
        model.s_C,
        within=Binary,
        initialize=0,
        doc="New or additional storage capacity installed at storage site with specific storage capacity",
    )
    model.vb_y_Treatment = Var(
        model.s_R,
        model.s_B,
        model.s_J,
        within=Binary,
        initialize=0,
        doc="New or additional treatment capacity installed at treatment site with specific treatment capacity",
    )
    # model.vb_y_Treatment = Var(
    #     model.s_R,
    #     model.s_J,
    #     within=Binary,
    #     initialize=0,
    #     doc="New or additional treatment capacity installed at treatment site with specific treatment capacity",
    # )
    model.vb_y_Disposal = Var(
        model.s_K,
        model.s_I,
        within=Binary,
        initialize=0,
        doc="New or additional disposal capacity installed at disposal site with specific injection capacity",
    )
    model.vb_y_Flow = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=Binary,
        initialize=0,
        doc="Directional flow between two locations",
    )

    # model.vb_z_Pipeline      = Var(model.s_L,model.s_L,model.s_D,model.s_T,within=Binary, doc='Timing of pipeline installation between two locations')
    # model.vb_z_Storage       = Var(model.s_S,model.s_C,model.s_T,within=Binary, doc='Timing of storage facility installation at storage site')
    # model.vb_z_Disposal      = Var(model.s_K,model.s_I,model.s_T,within=Binary, doc='Timing of disposal facility installation at disposal site')

    ## Pre-process Data ##
    # df_parameters = _preprocess_data(model, df_parameters)
    _preprocess_data(model)

    ## Define set parameters ##

    PCA_Table = {}

    PNA_Table = {}

    PPA_Table = {}

    CNA_Table = {}

    NNA_Table = {}

    NCA_Table = {}

    NKA_Table = {}

    NSA_Table = {}

    NRA_Table = {}

    NOA_Table = {}

    FCA_Table = {}

    RNA_Table = {}

    RKA_Table = {}

    RSA_Table = {}

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

    SCT_Table = {}

    CRT_Table = {}

    SCT_Table = {}

    SKT_Table = {}

    RKT_Table = {}

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
        initialize=model.df_parameters["PNA"],
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
        initialize=model.df_parameters["CNA"],
        doc="Valid completion-to-node pipeline arcs [-]",
    )
    model.p_CCA = Param(
        model.s_CP,
        model.s_CP,
        default=0,
        initialize=model.df_parameters["CCA"],
        doc="Valid completions-to-completions pipelin arcs [-]",
    )
    model.p_NNA = Param(
        model.s_N,
        model.s_N,
        default=0,
        initialize=model.df_parameters["NNA"],
        doc="Valid node-to-node pipeline arcs [-]",
    )
    model.p_NCA = Param(
        model.s_N,
        model.s_CP,
        default=0,
        initialize=model.df_parameters["NCA"],
        doc="Valid node-to-completions pipeline arcs [-]",
    )
    model.p_NKA = Param(
        model.s_N,
        model.s_K,
        default=0,
        initialize=model.df_parameters["NKA"],
        doc="Valid node-to-disposal pipeline arcs [-]",
    )
    model.p_NSA = Param(
        model.s_N,
        model.s_S,
        default=0,
        initialize=model.df_parameters["NSA"],
        doc="Valid node-to-storage pipeline arcs [-]",
    )
    model.p_NRA = Param(
        model.s_N,
        model.s_R,
        default=0,
        initialize=model.df_parameters["NRA"],
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
        initialize=model.df_parameters["FCA"],
        doc="Valid freshwater-to-completions pipeline arcs [-]",
    )
    model.p_RCA = Param(
        model.s_R,
        model.s_CP,
        default=0,
        initialize=model.df_parameters["RCA"],
        doc="Valid treatment-to-completions layflat arcs [-]",
    )
    model.p_RNA = Param(
        model.s_R,
        model.s_N,
        default=0,
        initialize=model.df_parameters["RNA"],
        doc="Valid treatment-to-node pipeline arcs [-]",
    )
    model.p_RKA = Param(
        model.s_R,
        model.s_K,
        default=0,
        initialize=RKA_Table,
        doc="Valid treatment-to-disposal pipeline arcs [-]",
    )
    model.p_RSA = Param(
        model.s_R,
        model.s_S,
        default=0,
        initialize=RSA_Table,
        doc="Valid treatment-to-storage pipeline arcs [-]",
    )
    model.p_SNA = Param(
        model.s_S,
        model.s_N,
        default=0,
        initialize=model.df_parameters["SNA"],
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
        initialize=model.df_parameters["PCT"],
        doc="Valid production-to-completions trucking arcs [-]",
    )
    model.p_FCT = Param(
        model.s_F,
        model.s_CP,
        default=0,
        initialize=model.df_parameters["FCT"],
        doc="Valid freshwater-to-completions trucking arcs [-]",
    )
    model.p_PKT = Param(
        model.s_PP,
        model.s_K,
        default=0,
        initialize=model.df_parameters["PKT"],
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
        initialize=PRT_Table,
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
        initialize=model.df_parameters["CKT"],
        doc="Valid completions-to-disposal trucking arcs [-]",
    )
    model.p_CST = Param(
        model.s_CP,
        model.s_S,
        default=0,
        initialize=model.df_parameters["CST"],
        doc="Valid completions-to-storage trucking arcs [-]",
    )
    model.p_CRT = Param(
        model.s_CP,
        model.s_R,
        default=0,
        initialize=CRT_Table,
        doc="Valid completions-to-treatment trucking arcs [-]",
    )
    model.p_CCT = Param(
        model.s_CP,
        model.s_CP,
        default=0,
        initialize=model.df_parameters["CCT"],
        doc="Valid completion-to-completion trucking arcs [-]",
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

    # model.p_NNC = Param(
    #     model.s_N,
    #     default=0
    #     initialize=
    # )

    # model.p_PCA.pprint()
    # model.p_PNA.pprint()
    # model.p_CNA.pprint()
    # model.p_NNA.pprint()
    # model.p_CCA.pprint()

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

    TreatmentCapExTable = {}

    PipelineCapExTable = {}

    DisposalOperationalCostTable = {}

    TreatmentOperationalCostTable = {}

    ReuseOperationalCostTable = {}

    StorageOperationalCostTable = {}

    StorageOperationalCreditTable = {}

    PipelineOperationalCostTable = {}

    TruckingHourlyCostTable = {}

    FreshSourcingCostTable = {}

    model.p_alpha_AnnualizationRate = Param(
        default=1,
        initialize=model.df_parameters["AnnualizationRate"],
        doc="Annualization rate [%]",
    )
    model.p_gamma_Completions = Param(
        model.s_P,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["CompletionsDemand"].items()
        },
        units=model.model_units["volume_time"],
        doc="Completions water demand [volume/time]",
    )
    model.p_gamma_TotalDemand = Param(
        default=0,
        initialize=sum(
            sum(model.p_gamma_Completions[p, t] for p in model.s_P) for t in model.s_T
        ),
        units=model.model_units["volume"],
        doc="Total water demand over the planning horizon [volume]",
        mutable=True,
    )
    model.p_beta_Production = Param(
        model.s_P,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["PadRates"].items()
        },
        units=model.model_units["volume_time"],
        doc="Produced water supply forecast [volume/time]",
    )
    model.p_beta_Flowback = Param(
        model.s_P,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["FlowbackRates"].items()
        },
        units=model.model_units["volume_time"],
        doc="Flowback supply forecast for a completions bad [volume/time]",
    )
    model.p_beta_TotalProd = Param(
        default=0,
        initialize=sum(
            sum(
                model.p_beta_Production[p, t] + model.p_beta_Flowback[p, t]
                for p in model.s_P
            )
            for t in model.s_T
        ),
        units=model.model_units["volume"],
        doc="Combined water supply forecast (flowback & production) over the planning horizon [volume]",
        mutable=True,
    )
    model.p_sigma_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["InitialPipelineCapacity"].items()
        },
        units=model.model_units["volume_time"],
        doc="Initial pipeline capacity between two locations [volume/time]",
    )
    model.p_sigma_Disposal = Param(
        model.s_K,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["InitialDisposalCapacity"].items()
        },
        units=model.model_units["volume_time"],
        doc="Initial disposal capacity at disposal sites [volume/time]",
    )
    model.p_sigma_Storage = Param(
        model.s_S,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume"],
                to_units=model.model_units["volume"],
            )
            for key, value in model.df_parameters["InitialStorageCapacity"].items()
        },
        units=model.model_units["volume"],
        doc="Initial storage capacity at storage site [volume]",
    )
    model.p_sigma_PadStorage = Param(
        model.s_CP,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume"],
                to_units=model.model_units["volume"],
            )
            for key, value in model.df_parameters["CompletionsPadStorage"].items()
        },
        units=model.model_units["volume"],
        doc="Storage capacity at completions site [volume]",
    )
    model.p_sigma_Treatment = Param(
        model.s_R,
        model.s_B,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["InitialTreatmentCapacity"].items()
        },
        units=model.model_units["volume_time"],
        doc="Initial treatment capacity at treatment site [volume/time]",
    )
    model.p_sigma_Reuse = Param(
        model.s_O,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in InitialReuseCapacityTable.items()
        },
        units=model.model_units["volume_time"],
        doc="Initial reuse capacity at reuse site [volume/time]",
    )
    model.p_sigma_Freshwater = Param(
        model.s_F,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters[
                "FreshwaterSourcingAvailability"
            ].items()
        },
        units=model.model_units["volume_time"],
        doc="Freshwater sourcing capacity at freshwater source [volume/time]",
        mutable=True,
    )

    model.p_sigma_OffloadingPad = Param(
        model.s_P,
        default=9999,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["PadOffloadingCapacity"].items()
        },
        units=model.model_units["volume_time"],
        doc="Truck offloading sourcing capacity per pad [volume/time]",
        mutable=True,
    )
    model.p_sigma_OffloadingStorage = Param(
        model.s_S,
        default=9999,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in StorageOffloadingCapacityTable.items()
        },
        units=model.model_units["volume_time"],
        doc="Truck offloading capacity per pad [volume/time]",
        mutable=True,
    )
    model.p_sigma_ProcessingPad = Param(
        model.s_P,
        default=9999,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in ProcessingCapacityPadTable.items()
        },
        units=model.model_units["volume_time"],
        doc="Processing (e.g. clarification) capacity per pad [volume/time]",
        mutable=True,
    )
    model.p_sigma_ProcessingStorage = Param(
        model.s_S,
        default=9999,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in ProcessingCapacityStorageTable.items()
        },
        units=model.model_units["volume_time"],
        doc="Processing (e.g. clarification) capacity per storage site [volume/time]",
        mutable=True,
    )
    if model.config.node_capacity == IncludeNodeCapacity.true:
        model.p_sigma_NetworkNode = Param(
            model.s_N,
            default=nan,
            within=Any,
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["volume_time"],
                    to_units=model.model_units["volume_time"],
                )
                for key, value in df_parameters["NodeCapacities"].items()
            },
            units=model.model_units["volume_time"],
            doc="Capacity per network node [volume/time]",
        )

    model.p_epsilon_Treatment = Param(
        model.s_R,
        model.s_W,
        default=1.0,
        initialize=model.df_parameters["TreatmentEfficiency"],
        doc="Treatment efficiency [%]",
    )

    model.p_W_TreatmentComponent = Param(
        model.s_R,
        default=model.s_W.first(),
        within=model.s_W,
        doc="Water quality component treated at site",
    )
    # Note PipelineCapacityIncrements_Calculated is set in _pre_process. These values are already in model units, they
    # do not need to be calculated
    if model.config.pipeline_capacity == PipelineCapacity.calculated:
        model.p_delta_Pipeline = Param(
            model.s_D,
            default=0,
            initialize=model.df_parameters["PipelineCapacityIncrements_Calculated"],
            units=model.model_units["volume_time"],
            doc="Pipeline capacity installation/expansion increments [volume/time]",
        )
    elif model.config.pipeline_capacity == PipelineCapacity.input:
        model.p_delta_Pipeline = Param(
            model.s_D,
            default=0,
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["volume_time"],
                    to_units=model.model_units["volume_time"],
                )
                for key, value in model.df_parameters[
                    "PipelineCapacityIncrements"
                ].items()
            },
            units=model.model_units["volume_time"],
            doc="Pipeline capacity installation/expansion increments [volume/time]",
        )

    model.p_delta_Disposal = Param(
        model.s_I,
        default=pyunits.convert_value(
            10,
            from_units=pyunits.oil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["DisposalCapacityIncrements"].items()
        },
        units=model.model_units["volume_time"],
        doc="Disposal capacity installation/expansion increments [volume/time]",
    )

    model.p_delta_Storage = Param(
        model.s_C,
        default=pyunits.convert_value(
            10,
            from_units=pyunits.oil_bbl,
            to_units=model.model_units["volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume"],
                to_units=model.model_units["volume"],
            )
            for key, value in model.df_parameters["StorageCapacityIncrements"].items()
        },
        units=model.model_units["volume"],
        doc="Storage capacity installation/expansion increments [volume]",
    )
    model.p_delta_Treatment = Param(
        model.s_B,
        model.s_J,
        default=pyunits.convert_value(
            10,
            from_units=pyunits.oil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["TreatmentCapacityIncrements"].items()
        },
        units=model.model_units["volume_time"],
        doc="Treatment capacity installation/expansion increments [volume/time]",
    )

    model.p_delta_Truck = Param(
        default=pyunits.convert_value(
            110, from_units=pyunits.oil_bbl, to_units=model.model_units["volume"]
        ),
        units=model.model_units["volume"],
        doc="Truck capacity [volume]",
    )

    model.p_tau_Disposal = Param(
        model.s_K,
        default=pyunits.convert_value(
            12, from_units=pyunits.week, to_units=model.decision_period
        ),
        units=model.decision_period,
        doc="Disposal construction/expansion lead time [time]",
    )

    model.p_tau_Storage = Param(
        model.s_S,
        default=pyunits.convert_value(
            12, from_units=pyunits.week, to_units=model.decision_period
        ),
        units=model.decision_period,
        doc="Storage construction/expansion lead time [time]",
    )

    model.p_tau_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=pyunits.convert_value(
            12, from_units=pyunits.week, to_units=model.decision_period
        ),
        units=model.decision_period,
        doc="Pipeline construction/expansion lead time [time]",
    )

    # COMMENT: It is expected that the units for this parameter are hours, which usually differs from the time units used
    # for flow rates, e.g., day, week, month. Therefore, for the sake of simplicity, no units are defined for this parameter,
    # as the hr units will cancel out with the units in model.p_pi_Trucking which is the hourly cost of trucking.
    model.p_tau_Trucking = Param(
        model.s_L,
        model.s_L,
        default=12,
        initialize=model.df_parameters["TruckingTime"],
        doc="Drive time between locations [hr]",
    )

    # COMMENT: Many more parameters missing. See documentation for details.

    model.p_lambda_Storage = Param(
        model.s_S,
        default=0,
        units=model.model_units["volume"],
        doc="Initial storage level at storage site [volume]",
    )

    model.p_lambda_PadStorage = Param(
        model.s_CP,
        default=0,
        units=model.model_units["volume"],
        doc="Initial storage level at completions site [volume]",
    )

    model.p_theta_Storage = Param(
        model.s_S,
        default=0,
        units=model.model_units["volume"],
        doc="Terminal storage level at storage site [volume]",
    )

    model.p_theta_PadStorage = Param(
        model.s_CP,
        default=0,
        units=model.model_units["volume"],
        doc="Terminal storage level at completions site [volume]",
    )

    PipelineExpansionDistance_convert_to_model = {
        key: pyunits.convert_value(
            value,
            from_units=model.user_units["distance"],
            to_units=model.model_units["distance"],
        )
        for key, value in model.df_parameters["PipelineExpansionDistance"].items()
    }
    model.p_lambda_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=max(PipelineExpansionDistance_convert_to_model.values()) * 100
        if PipelineExpansionDistance_convert_to_model
        else pyunits.convert_value(
            10000, from_units=pyunits.miles, to_units=model.model_units["distance"]
        ),
        initialize=PipelineExpansionDistance_convert_to_model,
        units=model.model_units["distance"],
        doc="Pipeline segment length [distance]",
    )

    model.p_kappa_Disposal = Param(
        model.s_K,
        model.s_I,
        default=pyunits.convert_value(
            20,
            from_units=pyunits.USD / (pyunits.oil_bbl / pyunits.day),
            to_units=model.model_units["currency_volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume_time"],
                to_units=model.model_units["currency_volume_time"],
            )
            for key, value in model.df_parameters["DisposalExpansionCost"].items()
        },
        units=model.model_units["currency_volume_time"],
        doc="Disposal construction/expansion capital cost for selected increment [currency/(volume/time)]",
    )

    model.p_kappa_Storage = Param(
        model.s_S,
        model.s_C,
        default=pyunits.convert_value(
            0.1,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in model.df_parameters["StorageExpansionCost"].items()
        },
        units=model.model_units["currency_volume"],
        doc="Storage construction/expansion capital cost for selected increment [currency/volume]",
    )

    model.p_kappa_Treatment = Param(
        model.s_R,
        model.s_B,
        model.s_J,
        default=pyunits.convert_value(
            10,
            from_units=pyunits.USD / (pyunits.oil_bbl / pyunits.day),
            to_units=model.model_units["currency_volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume_time"],
                to_units=model.model_units["currency_volume_time"],
            )
            for key, value in model.df_parameters["TreatmentExpansionCost"].items()
        },
        units=model.model_units["currency_volume_time"],
        doc="Treatment construction/expansion capital cost for selected increment [currency/(volume/time)]",
    )

    model.p_omega_EvaporationRate = Param(
        default=pyunits.convert_value(
            3000,
            from_units=pyunits.oil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        units=model.model_units["volume_time"],
        doc="Evaporation Rate per week [volume/time]",
    )

    if model.config.pipeline_cost == PipelineCost.distance_based:
        model.p_kappa_Pipeline = Param(
            default=pyunits.convert_value(
                120000,
                from_units=pyunits.USD / (pyunits.inch * pyunits.mile),
                to_units=model.model_units["pipe_cost_distance"],
            ),
            initialize=pyunits.convert_value(
                model.df_parameters["PipelineCapexDistanceBased"][
                    "pipeline_expansion_cost"
                ],
                from_units=model.user_units["pipe_cost_distance"],
                to_units=model.model_units["pipe_cost_distance"],
            ),
            units=model.model_units["pipe_cost_distance"],
            doc="Pipeline construction/expansion capital cost for selected increment [[currency/(diameter-distance)]",
        )

        model.p_mu_Pipeline = Param(
            model.s_D,
            default=0,
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["diameter"],
                    to_units=model.model_units["diameter"],
                )
                for key, value in model.df_parameters["PipelineDiameterValues"].items()
            },
            units=model.model_units["diameter"],
            doc="Pipeline capacity installation/expansion increments [diameter]",
        )

    elif model.config.pipeline_cost == PipelineCost.capacity_based:
        model.p_kappa_Pipeline = Param(
            model.s_L,
            model.s_L,
            model.s_D,
            default=pyunits.convert_value(
                30,
                from_units=pyunits.USD / (pyunits.oil_bbl / pyunits.day),
                to_units=model.model_units["pipe_cost_capacity"],
            ),
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["pipe_cost_capacity"],
                    to_units=model.model_units["pipe_cost_capacity"],
                )
                for key, value in model.df_parameters[
                    "PipelineCapexCapacityBased"
                ].items()
            },
            units=model.model_units["pipe_cost_capacity"],
            doc="Pipeline construction/expansion capital cost for selected increment [currency/volume/time]",
        )

    # model.p_kappa_Disposal.pprint()
    # model.p_kappa_Storage.pprint()
    # model.p_kappa_Treatment.pprint()
    # model.p_kappa_Pipeline.pprint()
    DisposalOperationalCost_convert_to_model = {
        key: pyunits.convert_value(
            value,
            from_units=model.user_units["currency_volume"],
            to_units=model.model_units["currency_volume"],
        )
        for key, value in model.df_parameters["DisposalOperationalCost"].items()
    }
    model.p_pi_Disposal = Param(
        model.s_K,
        default=max(DisposalOperationalCost_convert_to_model.values()) * 100
        if DisposalOperationalCost_convert_to_model
        else pyunits.convert_value(
            25,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize=DisposalOperationalCost_convert_to_model,
        units=model.model_units["currency_volume"],
        doc="Disposal operational cost [currency/volume]",
    )
    model.p_pi_Treatment = Param(
        model.s_R,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in model.df_parameters["TreatmentOperationalCost"].items()
        },
        units=model.model_units["currency_volume"],
        doc="Treatment operational cost [currency/volume]",
    )
    ReuseOperationalCost_convert_to_model = {
        key: pyunits.convert_value(
            value,
            from_units=model.user_units["currency_volume"],
            to_units=model.model_units["currency_volume"],
        )
        for key, value in model.df_parameters["ReuseOperationalCost"].items()
    }
    model.p_pi_Reuse = Param(
        model.s_CP,
        default=max(ReuseOperationalCost_convert_to_model.values()) * 100
        if ReuseOperationalCost_convert_to_model
        else pyunits.convert_value(
            25,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize=ReuseOperationalCost_convert_to_model,
        units=model.model_units["currency_volume"],
        doc="Reuse operational cost [currency/volume]",
    )
    model.p_pi_Storage = Param(
        model.s_S,
        default=pyunits.convert_value(
            1,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in StorageOperationalCostTable.items()
        },
        units=model.model_units["currency_volume"],
        doc="Storage deposit operational cost [currency/volume]",
    )
    model.p_rho_Storage = Param(
        model.s_S,
        default=pyunits.convert_value(
            0.99,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in StorageOperationalCreditTable.items()
        },
        units=model.model_units["currency_volume"],
        doc="Storage withdrawal operational credit [currency/volume]",
    )
    model.p_pi_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=pyunits.convert_value(
            0.01,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in model.df_parameters["PipelineOperationalCost"].items()
        },
        units=model.model_units["currency_volume"],
        doc="Pipeline operational cost [currency/volume]",
    )
    # COMMENT: For this parameter only currency units are defined, as the hourly rate is canceled out with the
    # trucking time units from parameter p_Tau_Trucking. This is to avoid adding an extra unit for time which may
    # be confusing
    model.p_pi_Trucking = Param(
        model.s_L,
        default=max(model.df_parameters["TruckingHourlyCost"].values()) * 100
        if model.df_parameters["TruckingHourlyCost"]
        else pyunits.convert_value(
            15000,
            from_units=model.user_units["currency"],
            to_units=model.model_units["currency"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency"],
                to_units=model.model_units["currency"],
            )
            for key, value in model.df_parameters["TruckingHourlyCost"].items()
        },
        units=model.model_units["currency"],
        doc="Trucking hourly cost (by source) [currency/hr]",
    )
    FreshSourcingCost_convert_to_model = {
        key: pyunits.convert_value(
            value,
            from_units=model.user_units["currency_volume"],
            to_units=model.model_units["currency_volume"],
        )
        for key, value in model.df_parameters["FreshSourcingCost"].items()
    }
    model.p_pi_Sourcing = Param(
        model.s_F,
        default=max(FreshSourcingCost_convert_to_model.values()) * 100
        if FreshSourcingCost_convert_to_model
        else pyunits.convert_value(
            150,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize=FreshSourcingCost_convert_to_model,
        units=model.model_units["currency_volume"],
        doc="Fresh sourcing cost [currency/volume]",
    )

    model.p_M_Flow = Param(
        default=99999,
        units=model.model_units["volume_time"],
        doc="Big-M flow parameter [volume/time]",
    )

    model.p_psi_FracDemand = Param(
        default=99999,
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_Production = Param(
        default=99999,
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_Flowback = Param(
        default=99999,
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_PipelineCapacity = Param(
        default=99999,
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_StorageCapacity = Param(
        default=99999,
        units=model.model_units["currency_volume"],
        doc="Slack cost parameter [currency/volume]",
    )
    model.p_psi_DisposalCapacity = Param(
        default=99999,
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_TreatmentCapacity = Param(
        default=99999,
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_ReuseCapacity = Param(
        default=99999,
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )

    # model.p_sigma_Freshwater.pprint()

    ## Define cost objective function ##

    if model.config.objective == Objectives.cost:

        def CostObjectiveFunctionRule(model):
            return model.v_Z == (
                model.v_C_TotalSourced
                + model.v_C_TotalDisposal
                + model.v_C_TotalTreatment
                + model.v_C_TotalReuse
                + model.v_C_TotalPiping
                + model.v_C_TotalStorage
                + model.v_C_TotalTrucking
                + model.p_alpha_AnnualizationRate
                * (
                    model.v_C_DisposalCapEx
                    + model.v_C_StorageCapEx
                    + model.v_C_TreatmentCapEx
                    + model.v_C_PipelineCapEx
                )
                + model.v_C_Slack
                - model.v_R_TotalStorage
            )

        model.CostObjectiveFunction = Constraint(
            rule=CostObjectiveFunctionRule, doc="Cost objective function"
        )

        # model.CostObjectiveFunction.pprint()

    ## Define reuse objective function ##

    elif model.config.objective == Objectives.reuse:

        def ReuseObjectiveFunctionRule(model):
            return model.v_Z == -(
                model.v_F_TotalReused / model.p_beta_TotalProd
            ) + 1 / 38446652 * (
                model.v_C_TotalSourced
                + model.v_C_TotalDisposal
                + model.v_C_TotalTreatment
                + model.v_C_TotalReuse
                + model.v_C_TotalPiping
                + model.v_C_TotalStorage
                + model.v_C_TotalTrucking
                + model.p_alpha_AnnualizationRate
                * (
                    model.v_C_DisposalCapEx
                    + model.v_C_StorageCapEx
                    + model.v_C_TreatmentCapEx
                    + model.v_C_PipelineCapEx
                )
                + model.v_C_Slack
                - model.v_R_TotalStorage
            )

        model.ReuseObjectiveFunction = Constraint(
            rule=ReuseObjectiveFunctionRule, doc="Reuse objective function"
        )

        # model.ReuseObjectiveFunction.pprint()

    else:
        raise Exception("objective not supported")

    ## Define constraints ##

    def CompletionsPadDemandBalanceRule(model, p, t):
        constraint = model.p_gamma_Completions[p, t] == (
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
            + sum(model.v_F_Piped[r, p, t] for r in model.s_R if model.p_RCA[r, p])
            + sum(model.v_F_Sourced[f, p, t] for f in model.s_F if model.p_FCA[f, p])
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
            + sum(model.v_F_Trucked[s, p, t] for s in model.s_S if model.p_SCT[s, p])
            + sum(model.v_F_Trucked[f, p, t] for f in model.s_F if model.p_FCT[f, p])
            + model.v_F_PadStorageOut[p, t]
            - model.v_F_PadStorageIn[p, t]
            + model.v_S_FracDemand[p, t]
        )

        return process_constraint(constraint)

    model.CompletionsPadDemandBalance = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadDemandBalanceRule,
        doc="Completions pad demand balance",
    )

    # model.CompletionsPadDemandBalance['CP02','T24'].pprint()

    def CompletionsPadStorageBalanceRule(model, p, t):
        if t == model.s_T.first():
            constraint = model.v_L_PadStorage[p, t] == model.p_lambda_PadStorage[p] + (
                model.v_F_PadStorageIn[p, t] - model.v_F_PadStorageOut[p, t]
            )
        else:
            constraint = model.v_L_PadStorage[p, t] == model.v_L_PadStorage[
                p, model.s_T.prev(t)
            ] + (model.v_F_PadStorageIn[p, t] - model.v_F_PadStorageOut[p, t])

        return process_constraint(constraint)

    model.CompletionsPadStorageBalance = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadStorageBalanceRule,
        doc="Completions pad storage balance",
    )

    # model.CompletionsPadStorageBalance.pprint()

    def CompletionsPadStorageCapacityRule(model, p, t):
        constraint = model.v_L_PadStorage[p, t] <= model.p_sigma_PadStorage[p]

        return process_constraint(constraint)

    model.CompletionsPadStorageCapacity = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadStorageCapacityRule,
        doc="Completions pad storage capacity",
    )

    # model.CompletionsPadStorageCapacity.pprint()

    def TerminalCompletionsPadStorageLevelRule(model, p, t):
        if t == model.s_T.last():
            constraint = model.v_L_PadStorage[p, t] <= model.p_theta_PadStorage[p]
        else:
            return Constraint.Skip

        return process_constraint(constraint)

    model.TerminalCompletionsPadStorageLevel = Constraint(
        model.s_CP,
        model.s_T,
        rule=TerminalCompletionsPadStorageLevelRule,
        doc="Terminal completions pad storage level",
    )

    # model.TerminalCompletionsPadStorageLevel.pprint()

    def FreshwaterSourcingCapacityRule(model, f, t):
        constraint = (
            sum(model.v_F_Sourced[f, p, t] for p in model.s_CP if model.p_FCA[f, p])
            + sum(model.v_F_Trucked[f, p, t] for p in model.s_CP if model.p_FCT[f, p])
            <= model.p_sigma_Freshwater[f, t]
        )

        return process_constraint(constraint)

    model.FreshwaterSourcingCapacity = Constraint(
        model.s_F,
        model.s_T,
        rule=FreshwaterSourcingCapacityRule,
        doc="Freshwater sourcing capacity",
    )

    # model.FreshwaterSourcingCapacity.pprint()

    def CompletionsPadTruckOffloadingCapacityRule(model, p, t):

        constraint = (
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
            <= model.p_sigma_OffloadingPad[p]
        )

        return process_constraint(constraint)

    model.CompletionsPadTruckOffloadingCapacity = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadTruckOffloadingCapacityRule,
        doc="Completions pad truck offloading capacity",
    )

    # model.CompletionsPadTruckOffloadingCapacity.pprint()

    def StorageSiteTruckOffloadingCapacityRule(model, s, t):
        constraint = (
            sum(model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s])
            + sum(model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s])
            <= model.p_sigma_OffloadingStorage[s]
        )

        return process_constraint(constraint)

    model.StorageSiteTruckOffloadingCapacity = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageSiteTruckOffloadingCapacityRule,
        doc="Storage site truck offloading capacity",
    )

    # model.StorageSiteTruckOffloadingCapacity.pprint()

    def StorageSiteProcessingCapacityRule(model, s, t):
        constraint = (
            sum(model.v_F_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s])
            + sum(model.v_F_Piped[r, s, t] for r in model.s_R if model.p_RSA[r, s])
            + sum(model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s])
            + sum(model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s])
            <= model.p_sigma_ProcessingStorage[s]
        )

        return process_constraint(constraint)

    model.StorageSiteProcessingCapacity = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageSiteProcessingCapacityRule,
        doc="Storage site processing capacity",
    )

    # model.StorageSiteProcessingCapacity.pprint()

    def ProductionPadSupplyBalanceRule(model, p, t):
        constraint = (
            model.p_beta_Production[p, t]
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
        return process_constraint(constraint)

    model.ProductionPadSupplyBalance = Constraint(
        model.s_PP,
        model.s_T,
        rule=ProductionPadSupplyBalanceRule,
        doc="Production pad supply balance",
    )

    # model.ProductionPadSupplyBalance.pprint()

    def CompletionsPadSupplyBalanceRule(model, p, t):
        return (
            model.p_beta_Flowback[p, t]
            == sum(model.v_F_Piped[p, n, t] for n in model.s_N if model.p_CNA[p, n])
            + sum(
                model.v_F_Piped[p, p_tilde, t]
                for p_tilde in model.s_CP
                if model.p_CCA[p, p_tilde]
            )
            + sum(model.v_F_Trucked[p, k, t] for k in model.s_K if model.p_CKT[p, k])
            + sum(
                model.v_F_Trucked[p, p_tilde, t]
                for p_tilde in model.s_CP
                if model.p_CCT[p, p_tilde]
            )
            + sum(model.v_F_Trucked[p, s, t] for s in model.s_S if model.p_CST[p, s])
            + sum(model.v_F_Trucked[p, r, t] for r in model.s_R if model.p_CRT[p, r])
            + model.v_S_Flowback[p, t]
        )

        # return process_constraint(constraint)

    model.CompletionsPadSupplyBalance = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadSupplyBalanceRule,
        doc="Completions pad supply balance (i.e. flowback balance",
    )

    # model.CompletionsPadSupplyBalance.pprint()

    def NetworkNodeBalanceRule(model, n, t):
        constraint = sum(
            model.v_F_Piped[p, n, t] for p in model.s_PP if model.p_PNA[p, n]
        ) + sum(
            model.v_F_Piped[p, n, t] for p in model.s_CP if model.p_CNA[p, n]
        ) + sum(
            model.v_F_Piped[n_tilde, n, t]
            for n_tilde in model.s_N
            if model.p_NNA[n_tilde, n]
        ) + sum(
            model.v_F_Piped[s, n, t] for s in model.s_S if model.p_SNA[s, n]
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

        return process_constraint(constraint)

    model.NetworkBalance = Constraint(
        model.s_N, model.s_T, rule=NetworkNodeBalanceRule, doc="Network node balance"
    )

    # model.NetworkBalance['N12','T05'].pprint()

    def BidirectionalFlowRule1(model, l, l_tilde, t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                constraint = (
                    model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
                )
                return process_constraint(constraint)
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
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t]
                    <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
                )
                return process_constraint(constraint)
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
            constraint = model.v_L_Storage[s, t] == model.p_lambda_Storage[s] + (
                sum(model.v_F_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s])
                + sum(model.v_F_Piped[r, s, t] for r in model.s_R if model.p_RSA[r, s])
                + sum(
                    model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s]
                )
                + sum(
                    model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s]
                )
                - sum(model.v_F_Piped[s, n, t] for n in model.s_N if model.p_SNA[s, n])
                - sum(model.v_F_Piped[s, p, t] for p in model.s_CP if model.p_SCA[s, p])
                - sum(model.v_F_Piped[s, k, t] for k in model.s_K if model.p_SKA[s, k])
                - sum(model.v_F_Piped[s, r, t] for r in model.s_R if model.p_SRA[s, r])
                - sum(model.v_F_Piped[s, o, t] for o in model.s_O if model.p_SOA[s, o])
                - sum(
                    model.v_F_Trucked[s, p, t] for p in model.s_CP if model.p_SCT[s, p]
                )
                - sum(
                    model.v_F_Trucked[s, k, t] for k in model.s_K if model.p_SKT[s, k]
                )
                - model.v_F_StorageEvaporationStream[s, t]
            )
        else:
            constraint = model.v_L_Storage[s, t] == model.v_L_Storage[
                s, model.s_T.prev(t)
            ] + (
                sum(model.v_F_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s])
                + sum(model.v_F_Piped[r, s, t] for r in model.s_R if model.p_RSA[r, s])
                + sum(
                    model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s]
                )
                + sum(
                    model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s]
                )
                - sum(model.v_F_Piped[s, n, t] for n in model.s_N if model.p_SNA[s, n])
                - sum(model.v_F_Piped[s, p, t] for p in model.s_CP if model.p_SCA[s, p])
                - sum(model.v_F_Piped[s, k, t] for k in model.s_K if model.p_SKA[s, k])
                - sum(model.v_F_Piped[s, r, t] for r in model.s_R if model.p_SRA[s, r])
                - sum(model.v_F_Piped[s, o, t] for o in model.s_O if model.p_SOA[s, o])
                - sum(
                    model.v_F_Trucked[s, p, t] for p in model.s_CP if model.p_SCT[s, p]
                )
                - sum(
                    model.v_F_Trucked[s, k, t] for k in model.s_K if model.p_SKT[s, k]
                )
                - model.v_F_StorageEvaporationStream[s, t]
            )

        return process_constraint(constraint)

    model.StorageSiteBalance = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageSiteBalanceRule,
        doc="Storage site balance rule",
    )

    # model.StorageSiteBalance.pprint()

    def TerminalStorageLevelRule(model, s, t):
        if t == model.s_T.last():
            constraint = model.v_L_Storage[s, t] <= model.p_theta_Storage[s]
        else:
            return Constraint.Skip

        return process_constraint(constraint)

    model.TerminalStorageLevel = Constraint(
        model.s_S,
        model.s_T,
        rule=TerminalStorageLevelRule,
        doc="Terminal storage site level",
    )

    # model.TerminalStorageLevel.pprint()

    def PipelineCapacityExpansionRule(model, l, l_tilde):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d]
                        * (
                            model.vb_y_Pipeline[l, l_tilde, d]
                            + model.vb_y_Pipeline[l_tilde, l, d]
                        )
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d]
                        * (
                            model.vb_y_Pipeline[l, l_tilde, d]
                            + model.vb_y_Pipeline[l_tilde, l, d]
                        )
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d]
                        * (
                            model.vb_y_Pipeline[l, l_tilde, d]
                            + model.vb_y_Pipeline[l_tilde, l, d]
                        )
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d]
                        * (
                            model.vb_y_Pipeline[l, l_tilde, d]
                            + model.vb_y_Pipeline[l_tilde, l, d]
                        )
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d]
                        * (
                            model.vb_y_Pipeline[l, l_tilde, d]
                            + model.vb_y_Pipeline[l_tilde, l, d]
                        )
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d]
                        * (
                            model.vb_y_Pipeline[l, l_tilde, d]
                            + model.vb_y_Pipeline[l_tilde, l, d]
                        )
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d]
                        * (
                            model.vb_y_Pipeline[l, l_tilde, d]
                            + model.vb_y_Pipeline[l_tilde, l, d]
                        )
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d]
                        * (
                            model.vb_y_Pipeline[l, l_tilde, d]
                            + model.vb_y_Pipeline[l_tilde, l, d]
                        )
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_S:
            if model.p_RSA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * (model.vb_y_Pipeline[l, l_tilde, d])
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)
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

    # model.PipelineCapacityExpansion['N03','N04'].pprint()

    # def BiDirectionalPipelineCapacityRestrictionRule(model,l,l_tilde,d):
    #     return (model.vb_y_Pipeline[l,l_tilde,d] + model.vb_y_Pipeline[l_tilde,l,d] <= 1)
    # model.BiDirectionalPipelineCapacityRestriction = Constraint(model.s_L,model.s_L,model.s_D,rule=BiDirectionalPipelineCapacityRestrictionRule, doc='Bi-directional pipeline capacity restriction')

    # model.BiDirectionalPipelineCapacityRestriction.pprint()

    def PipelineCapacityRule(model, l, l_tilde, t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                constraint = (
                    model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
                )
                return process_constraint(constraint)
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

    # only include network node capacity constraint if config is set to true
    if model.config.node_capacity == IncludeNodeCapacity.true:

        def NetworkNodeCapacityRule(model, n, t):
            if value(model.p_sigma_NetworkNode[n]) > 0:
                constraint = (
                    sum(
                        model.v_F_Piped[p, n, t]
                        for p in model.s_PP
                        if model.p_PNA[p, n]
                    )
                    + sum(
                        model.v_F_Piped[p, n, t]
                        for p in model.s_CP
                        if model.p_CNA[p, n]
                    )
                    + sum(
                        model.v_F_Piped[n_tilde, n, t]
                        for n_tilde in model.s_N
                        if model.p_NNA[n_tilde, n]
                    )
                    + sum(
                        model.v_F_Piped[s, n, t] for s in model.s_S if model.p_SNA[s, n]
                    )
                    <= model.p_sigma_NetworkNode[n]
                )
            else:
                return Constraint.Skip

            return process_constraint(constraint)

        # simple constraint rule required to prevent errors if there are no node flows
        model.NetworkCapacity = Constraint(
            model.s_N,
            model.s_T,
            rule=simple_constraint_rule(NetworkNodeCapacityRule),
            doc="Network node capacity",
        )

    # model.PipelineCapacity['R01','CP01','T01'].pprint()

    def StorageCapacityExpansionRule(model, s):
        constraint = (
            model.v_X_Capacity[s]
            == model.p_sigma_Storage[s]
            + sum(
                model.p_delta_Storage[c] * model.vb_y_Storage[s, c] for c in model.s_C
            )
            + model.v_S_StorageCapacity[s]
        )

        return process_constraint(constraint)

    model.StorageCapacityExpansion = Constraint(
        model.s_S,
        rule=StorageCapacityExpansionRule,
        doc="Storage capacity construction/expansion",
    )

    # model.StorageCapacityExpansion.pprint()

    def StorageCapacityRule(model, s, t):
        constraint = model.v_L_Storage[s, t] <= model.v_X_Capacity[s]

        return process_constraint(constraint)

    model.StorageCapacity = Constraint(
        model.s_S, model.s_T, rule=StorageCapacityRule, doc="Storage capacity"
    )

    # model.StorageCapacity.pprint()

    def DisposalCapacityExpansionRule(model, k):
        constraint = (
            model.v_D_Capacity[k]
            == model.p_sigma_Disposal[k]
            + sum(
                model.p_delta_Disposal[i] * model.vb_y_Disposal[k, i] for i in model.s_I
            )
            + model.v_S_DisposalCapacity[k]
        )

        return process_constraint(constraint)

    model.DisposalCapacityExpansion = Constraint(
        model.s_K,
        rule=DisposalCapacityExpansionRule,
        doc="Disposal capacity construction/expansion",
    )

    # model.DisposalCapacityExpansion1.pprint()

    def DisposalCapacityRule(model, k, t):
        constraint = (
            sum(model.v_F_Piped[n, k, t] for n in model.s_N if model.p_NKA[n, k])
            + sum(model.v_F_Piped[s, k, t] for s in model.s_S if model.p_SKA[s, k])
            + sum(model.v_F_Trucked[s, k, t] for s in model.s_S if model.p_SKT[s, k])
            + sum(model.v_F_Trucked[p, k, t] for p in model.s_PP if model.p_PKT[p, k])
            + sum(model.v_F_Trucked[p, k, t] for p in model.s_CP if model.p_CKT[p, k])
            + sum(model.v_F_Trucked[r, k, t] for r in model.s_R if model.p_RKT[r, k])
            <= model.v_D_Capacity[k]
        )
        return process_constraint(constraint)

    model.DisposalCapacity = Constraint(
        model.s_K, model.s_T, rule=DisposalCapacityRule, doc="Disposal capacity"
    )

    # model.DisposalCapacity.pprint()

    def TreatmentCapacityExpansionRule(model, r):
        return model.v_T_Capacity[r] == sum((model.p_sigma_Treatment[r, b] * sum(
            model.vb_y_Treatment[r, b, j] for j in model.s_J) + sum(
            model.p_delta_Treatment[b, j] * model.vb_y_Treatment[r, b, j]
            for j in model.s_J)) for b in model.s_B)
    
    
    model.TreatmentCapacityExpansion = Constraint(
        model.s_R,
        rule=TreatmentCapacityExpansionRule,
        doc="Treatment capacity construction/expansion",
    )
    # def TreatmentCapacityExpansionRule(model, r):
    #     constraint = (
    #         model.v_T_Capacity[r]
    #         == model.p_sigma_Treatment[r]
    #         + sum(
    #             model.p_delta_Treatment[j] * model.vb_y_Treatment[r, j]
    #             for j in model.s_J
    #         )
    #         + model.v_S_TreatmentCapacity[r]
    #     )

    #     return process_constraint(constraint)

    # model.TreatmentCapacityExpansion = Constraint(
    #     model.s_R,
    #     rule=TreatmentCapacityExpansionRule,
    #     doc="Treatment capacity construction/expansion",
    # )

    # model.TreatmentCapacityExpansion.pprint()

    def TreatmentCapacityRule(model, r, t):
        constraint = (
            sum(model.v_F_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r])
            + sum(model.v_F_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r])
            + sum(model.v_F_Trucked[p, r, t] for p in model.s_PP if model.p_PRT[p, r])
            + sum(model.v_F_Trucked[p, r, t] for p in model.s_CP if model.p_CRT[p, r])
            <= model.v_T_Capacity[r]
        )
        return process_constraint(constraint)

    model.TreatmentCapacity = Constraint(
        model.s_R, model.s_T, rule=TreatmentCapacityRule, doc="Treatment capacity"
    )

    # model.TreatmentCapacity.pprint()

    def TreatmentBalanceRule(model, r, t):
        constraint = (
              (
                sum(model.v_F_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r])
                + sum(model.v_F_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r])
                + sum(
                    model.v_F_Trucked[p, r, t] for p in model.s_PP if model.p_PRT[p, r]
                )
                + sum(
                    model.v_F_Trucked[p, r, t] for p in model.s_CP if model.p_CRT[p, r]
                )
            )
            == model.v_F_ResidualWater[r, t] + model.v_F_TreatedWater[r, t]
        )
        return process_constraint(constraint)
    
    model.TreatmentBalance = Constraint(
        model.s_R, model.s_T, rule=TreatmentBalanceRule, doc="Treatment center flow balance"
    )
    # def TreatmentBalanceRule(model, r, t):
    #     constraint = (
    #         model.p_epsilon_Treatment[r, model.p_W_TreatmentComponent[r]]
    #         * (
    #             sum(model.v_F_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r])
    #             + sum(model.v_F_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r])
    #             + sum(
    #                 model.v_F_Trucked[p, r, t] for p in model.s_PP if model.p_PRT[p, r]
    #             )
    #             + sum(
    #                 model.v_F_Trucked[p, r, t] for p in model.s_CP if model.p_CRT[p, r]
    #             )
    #         )
    #         == sum(model.v_F_Piped[r, p, t] for p in model.s_CP if model.p_RCA[r, p])
    #         + sum(model.v_F_Piped[r, s, t] for s in model.s_S if model.p_RSA[r, s])
    #         + model.v_F_UnusedTreatedWater[r, t]
    #     )
    #     return process_constraint(constraint)

    # model.TreatmentBalance = Constraint(
    #     model.s_R, model.s_T, rule=TreatmentBalanceRule, doc="Treatment balance"
    # )

    # model.TreatmentBalance.pprint()

    def TreatedWaterRule(model, r, t):
        constraint = (
            model.v_F_TreatedWater[r, t]
            == sum(model.v_F_Piped[r, p, t] for p in model.s_CP if model.p_RCA[r, p])
            + sum(model.v_F_Piped[r, s, t] for s in model.s_S if model.p_RSA[r, s])
            + model.v_F_WaterRemoved[r, t]
        )
        return process_constraint(constraint)
    
    model.TreatedWater = Constraint(
        model.s_R, model.s_T, rule=TreatedWaterRule,
        doc="Treated water balance"
    )


    def BeneficialReuseCapacityRule(model, o, t):

        constraint = (
            sum(model.v_F_Piped[n, o, t] for n in model.s_N if model.p_NOA[n, o])
            + sum(model.v_F_Piped[s, o, t] for s in model.s_S if model.p_SOA[s, o])
            + sum(model.v_F_Trucked[p, o, t] for p in model.s_PP if model.p_POT[p, o])
            <= model.p_sigma_Reuse[o] + model.v_S_ReuseCapacity[o]
        )

        return process_constraint(constraint)

    model.BeneficialReuseCapacity = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseCapacityRule,
        doc="Beneficial reuse capacity",
    )

    # model.BeneficialReuseCapacity.pprint()

    # COMMENT: Beneficial reuse capacity constraint has not been tested yet

    def FreshSourcingCostRule(model, f, p, t):
        if f in model.s_F and p in model.s_CP:
            if model.p_FCA[f, p]:
                constraint = (
                    model.v_C_Sourced[f, p, t]
                    == (model.v_F_Sourced[f, p, t] + model.v_F_Trucked[f, p, t])
                    * model.p_pi_Sourcing[f]
                )
            elif model.p_FCT[f, p]:
                constraint = (
                    model.v_C_Sourced[f, p, t]
                    == (model.v_F_Sourced[f, p, t] + model.v_F_Trucked[f, p, t])
                    * model.p_pi_Sourcing[f]
                )
            else:
                return Constraint.Skip

            return process_constraint(constraint)
        else:
            return Constraint.Skip

    #                    return (model.v_C_Sourced[f,p,t] == (model.v_F_Sourced[f,p,t] + model.v_F_Trucked[f,p,t])* model.p_pi_Sourcing[f])
    model.FreshSourcingCost = Constraint(
        model.s_F,
        model.s_CP,
        model.s_T,
        rule=FreshSourcingCostRule,
        doc="Fresh sourcing cost",
    )

    # model.FreshSourcingCost.pprint()

    def TotalFreshSourcingCostRule(model):
        constraint = model.v_C_TotalSourced == sum(
            sum(
                sum(model.v_C_Sourced[f, p, t] for f in model.s_F if model.p_FCA[f, p])
                for p in model.s_CP
            )
            for t in model.s_T
        )
        return process_constraint(constraint)

    model.TotalFreshSourcingCost = Constraint(
        rule=TotalFreshSourcingCostRule, doc="Total fresh sourcing cost"
    )

    # model.TotalFreshSourcingCost.pprint()

    def TotalFreshSourcingVolumeRule(model):
        constraint = model.v_F_TotalSourced == (
            sum(
                sum(
                    sum(
                        model.v_F_Sourced[f, p, t]
                        for f in model.s_F
                        if model.p_FCA[f, p]
                    )
                    for p in model.s_CP
                )
                for t in model.s_T
            )
            + sum(
                sum(
                    sum(
                        model.v_F_Trucked[f, p, t]
                        for f in model.s_F
                        if model.p_FCT[f, p]
                    )
                    for p in model.s_CP
                )
                for t in model.s_T
            )
        )

        return process_constraint(constraint)

    model.TotalFreshSourcingVolume = Constraint(
        rule=TotalFreshSourcingVolumeRule, doc="Total fresh sourcing volume"
    )

    # model.TotalFreshSourcingVolume.pprint()

    def DisposalCostRule(model, k, t):
        constraint = (
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
        return process_constraint(constraint)

    model.DisposalCost = Constraint(
        model.s_K, model.s_T, rule=DisposalCostRule, doc="Disposal cost"
    )

    # model.DisposalCost.pprint()

    def TotalDisposalCostRule(model):
        constraint = model.v_C_TotalDisposal == sum(
            sum(model.v_C_Disposal[k, t] for k in model.s_K) for t in model.s_T
        )

        return process_constraint(constraint)

    model.TotalDisposalCost = Constraint(
        rule=TotalDisposalCostRule, doc="Total disposal cost"
    )

    # model.TotalDisposalCost.pprint()

    def TotalDisposalVolumeRule(model):
        constraint = model.v_F_TotalDisposed == (
            sum(
                sum(sum(model.v_F_Piped[l, k, t] for l in model.s_L) for k in model.s_K)
                for t in model.s_T
            )
            + sum(
                sum(
                    sum(model.v_F_Trucked[l, k, t] for l in model.s_L)
                    for k in model.s_K
                )
                for t in model.s_T
            )
        )

        return process_constraint(constraint)

    model.TotalDisposalVolume = Constraint(
        rule=TotalDisposalVolumeRule, doc="Total disposal volume"
    )

    # model.TotalDisposalVolume.pprint()

    def TreatmentCostRule(model, r, t):
        constraint = (
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
        return process_constraint(constraint)

    model.TreatmentCost = Constraint(
        model.s_R, model.s_T, rule=TreatmentCostRule, doc="Treatment cost"
    )

    # model.TreatmentCost.pprint()

    def TotalTreatmentCostRule(model):
        constraint = model.v_C_TotalTreatment == sum(
            sum(model.v_C_Treatment[r, t] for r in model.s_R) for t in model.s_T
        )

        return process_constraint(constraint)

    model.TotalTreatmentCost = Constraint(
        rule=TotalTreatmentCostRule, doc="Total treatment cost"
    )

    # model.TotalTreatmentCost.pprint()

    def CompletionsReuseCostRule(
        model,
        p,
        t,
    ):
        constraint = model.v_C_Reuse[p, t] == (
            (
                sum(model.v_F_Piped[n, p, t] for n in model.s_N if model.p_NCA[n, p])
                + sum(
                    model.v_F_Piped[p_tilde, p, t]
                    for p_tilde in model.s_PP
                    if model.p_PCA[p_tilde, p]
                )
                + sum(
                    model.v_F_Piped[p_tilde, p, t]
                    for p_tilde in model.s_CP
                    if model.p_CCA[p_tilde, p]
                )
                + sum(model.v_F_Piped[s, p, t] for s in model.s_S if model.p_SCA[s, p])
                + sum(model.v_F_Piped[r, p, t] for r in model.s_R if model.p_RCA[r, p])
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

        return process_constraint(constraint)

    model.CompletionsReuseCost = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsReuseCostRule,
        doc="Reuse completions cost",
    )

    # model.CompletionsReuseCost.pprint()

    def TotalCompletionsReuseCostRule(model):
        constraint = model.v_C_TotalReuse == sum(
            sum(model.v_C_Reuse[p, t] for p in model.s_CP) for t in model.s_T
        )

        return process_constraint(constraint)

    model.TotalCompletionsReuseCost = Constraint(
        rule=TotalCompletionsReuseCostRule, doc="Total completions reuse cost"
    )

    def TotalReuseVolumeRule(model):
        constraint = model.v_F_TotalReused == (
            sum(
                sum(
                    sum(
                        model.v_F_Piped[n, p, t] for n in model.s_N if model.p_NCA[n, p]
                    )
                    + sum(
                        model.v_F_Piped[p_tilde, p, t]
                        for p_tilde in model.s_PP
                        if model.p_PCA[p_tilde, p]
                    )
                    + sum(
                        model.v_F_Piped[p_tilde, p, t]
                        for p_tilde in model.s_CP
                        if model.p_CCA[p_tilde, p]
                    )
                    + sum(
                        model.v_F_Piped[s, p, t] for s in model.s_S if model.p_SCA[s, p]
                    )
                    + sum(
                        model.v_F_Piped[r, p, t] for r in model.s_R if model.p_RCA[r, p]
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
                        model.v_F_Trucked[s, p, t]
                        for s in model.s_S
                        if model.p_SCT[s, p]
                    )
                    for p in model.s_CP
                )
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalReuseVolume = Constraint(
        rule=TotalReuseVolumeRule, doc="Total reuse volume"
    )

    # model.TotalCompletionsReuseCost.pprint()

    def PipingCostRule(model, l, l_tilde, t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_CP:
            if model.p_CCA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Sourced[l, l_tilde, t]
                    * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.PipingCost = Constraint(
        model.s_L, model.s_L, model.s_T, rule=PipingCostRule, doc="Piping cost"
    )

    # model.PipingCost.pprint()

    def TotalPipingCostRule(model):
        constraint = model.v_C_TotalPiping == (
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
                        model.v_C_Piped[p, p_tilde, t]
                        for p in model.s_CP
                        if model.p_CCA[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
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
                        model.v_C_Piped[r, p, t] for r in model.s_R if model.p_RCA[r, p]
                    )
                    for p in model.s_CP
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
                for t in model.s_T
            )
        )

        return process_constraint(constraint)

    model.TotalPipingCost = Constraint(
        rule=TotalPipingCostRule, doc="Total piping cost"
    )

    # model.TotalPipingCost.pprint()

    def StorageDepositCostRule(model, s, t):
        constraint = model.v_C_Storage[s, t] == (
            (
                sum(model.v_F_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s])
                + sum(model.v_F_Piped[r, s, t] for r in model.s_R if model.p_RSA[r, s])
                + sum(
                    model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s]
                )
                + sum(
                    model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s]
                )
            )
            * model.p_pi_Storage[s]
        )
        return process_constraint(constraint)

    model.StorageDepositCost = Constraint(
        model.s_S, model.s_T, rule=StorageDepositCostRule, doc="Storage deposit cost"
    )

    # model.StorageDepositCost.pprint()

    def TotalStorageCostRule(model):
        constraint = model.v_C_TotalStorage == sum(
            sum(model.v_C_Storage[s, t] for s in model.s_S) for t in model.s_T
        )

        return process_constraint(constraint)

    model.TotalStorageCost = Constraint(
        rule=TotalStorageCostRule, doc="Total storage deposit cost"
    )

    # model.TotalStorageCost.pprint()

    def StorageWithdrawalCreditRule(model, s, t):
        constraint = model.v_R_Storage[s, t] == (
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

        return process_constraint(constraint)

    model.StorageWithdrawalCredit = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageWithdrawalCreditRule,
        doc="Storage withdrawal credit",
    )

    # model.StorageWithdrawalCredit.pprint()

    def TotalStorageWithdrawalCreditRule(model):
        constraint = model.v_R_TotalStorage == sum(
            sum(model.v_R_Storage[s, t] for s in model.s_S) for t in model.s_T
        )
        return process_constraint(constraint)

    model.TotalStorageWithdrawalCredit = Constraint(
        rule=TotalStorageWithdrawalCreditRule, doc="Total storage withdrawal credit"
    )

    # model.TotalStorageWithdrawalCredit.pprint()

    def TruckingCostRule(model, l, l_tilde, t):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_K:
            if model.p_PKT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_S:
            if model.p_PST[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_R:
            if model.p_PRT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_O:
            if model.p_POT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_K:
            if model.p_CKT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_S:
            if model.p_CST[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_R:
            if model.p_CRT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_CP:
            if model.p_CCT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKT[l, l_tilde]:
                constraint = (
                    model.v_C_Trucked[l, l_tilde, t]
                    == model.v_F_Trucked[l, l_tilde, t]
                    * 1
                    / model.p_delta_Truck
                    * model.p_tau_Trucking[l, l_tilde]
                    * model.p_pi_Trucking[l]
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.TruckingCost = Constraint(
        model.s_L, model.s_L, model.s_T, rule=TruckingCostRule, doc="Trucking cost"
    )

    # model.TruckingCost.pprint()

    def TotalTruckingCostRule(model):
        constraint = model.v_C_TotalTrucking == (
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
                        model.v_C_Trucked[p, p_tilde, t]
                        for p in model.s_CP
                        if model.p_CCT[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
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
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalTruckingCost = Constraint(
        rule=TotalTruckingCostRule, doc="Total trucking cost"
    )

    # model.TotalTruckingCost.pprint()

    def TotalTruckingVolumeRule(model):
        constraint = model.v_F_TotalTrucked == (
            sum(
                sum(
                    sum(
                        model.v_F_Trucked[p, p_tilde, t]
                        for p in model.s_PP
                        if model.p_PCT[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
                )
                + sum(
                    sum(
                        model.v_F_Trucked[p, k, t]
                        for p in model.s_PP
                        if model.p_PKT[p, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_F_Trucked[p, s, t]
                        for p in model.s_PP
                        if model.p_PST[p, s]
                    )
                    for s in model.s_S
                )
                + sum(
                    sum(
                        model.v_F_Trucked[p, r, t]
                        for p in model.s_PP
                        if model.p_PRT[p, r]
                    )
                    for r in model.s_R
                )
                + sum(
                    sum(
                        model.v_F_Trucked[p, o, t]
                        for p in model.s_PP
                        if model.p_POT[p, o]
                    )
                    for o in model.s_O
                )
                + sum(
                    sum(
                        model.v_F_Trucked[p, k, t]
                        for p in model.s_CP
                        if model.p_CKT[p, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_F_Trucked[p, s, t]
                        for p in model.s_CP
                        if model.p_CST[p, s]
                    )
                    for s in model.s_S
                )
                + sum(
                    sum(
                        model.v_F_Trucked[p, r, t]
                        for p in model.s_CP
                        if model.p_CRT[p, r]
                    )
                    for r in model.s_R
                )
                + sum(
                    sum(
                        model.v_F_Trucked[p, p_tilde, t]
                        for p in model.s_CP
                        if model.p_CCT[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
                )
                + sum(
                    sum(
                        model.v_F_Trucked[s, p, t]
                        for s in model.s_S
                        if model.p_SCT[s, p]
                    )
                    for p in model.s_CP
                )
                + sum(
                    sum(
                        model.v_F_Trucked[s, k, t]
                        for s in model.s_S
                        if model.p_SKT[s, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_F_Trucked[r, k, t]
                        for r in model.s_R
                        if model.p_RKT[r, k]
                    )
                    for k in model.s_K
                )
                + sum(
                    sum(
                        model.v_F_Trucked[f, p, t]
                        for f in model.s_F
                        if model.p_FCT[f, p]
                    )
                    for p in model.s_CP
                )
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalTruckingVolume = Constraint(
        rule=TotalTruckingVolumeRule, doc="Total trucking volume"
    )

    def DisposalExpansionCapExRule(model):
        constraint = model.v_C_DisposalCapEx == sum(
            sum(
                model.vb_y_Disposal[k, i]
                * model.p_kappa_Disposal[k, i]
                * model.p_delta_Disposal[i]
                for i in model.s_I
            )
            for k in model.s_K
        )
        return process_constraint(constraint)

    model.DisposalExpansionCapEx = Constraint(
        rule=DisposalExpansionCapExRule,
        doc="Disposal construction or capacity expansion cost",
    )

    # model.DisposalExpansionCapEx.pprint()

    def StorageExpansionCapExRule(model):
        constraint = model.v_C_StorageCapEx == sum(
            sum(
                model.vb_y_Storage[s, c]
                * model.p_kappa_Storage[s, c]
                * model.p_delta_Storage[c]
                for s in model.s_S
            )
            for c in model.s_C
        )
        return process_constraint(constraint)

    model.StorageExpansionCapEx = Constraint(
        rule=StorageExpansionCapExRule,
        doc="Storage construction or capacity expansion cost",
    )

    # model.StorageExpansionCapEx.pprint()

    def TreatmentExpansionCapExRule(model):
        return model.v_C_TreatmentCapEx == sum(
            sum(
                sum(
                    model.vb_y_Treatment[r, b, j]
                    * model.p_kappa_Treatment[r, b, j]
                    * model.p_delta_Treatment[b, j]
                    for r in model.s_R
                    ) for j in model.s_J
                ) for b in model.s_B
            )
    
    model.TreatmentExpansionCapEx = Constraint(
        rule=TreatmentExpansionCapExRule,
        doc="Treatment construction or capacity expansion cost",
    )

    # def TreatmentExpansionCapExRule(model):
    #     constraint = model.v_C_TreatmentCapEx == sum(
    #         sum(
    #             model.vb_y_Treatment[r, j]
    #             * model.p_kappa_Treatment[r, j]
    #             * model.p_delta_Treatment[j]
    #             for r in model.s_R
    #         )
    #         for j in model.s_J
    #     )
    #     return process_constraint(constraint)

    # model.TreatmentExpansionCapEx = Constraint(
    #     rule=TreatmentExpansionCapExRule,
    #     doc="Treatment construction or capacity expansion cost",
    # )

    # model.TreatmentExpansionCapEx.pprint()

    def PipelineExpansionCapExDistanceBasedRule(model):
        constraint = model.v_C_PipelineCapEx == (
            sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[p, p_tilde, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[p, p_tilde]
                        for p in model.s_PP
                        if model.p_PCA[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[p, n, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[p, n]
                        for p in model.s_PP
                        if model.p_PNA[p, n]
                    )
                    for n in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[p, p_tilde, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[p, p_tilde]
                        for p in model.s_PP
                        if model.p_PPA[p, p_tilde]
                    )
                    for p_tilde in model.s_PP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[p, n, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[p, n]
                        for p in model.s_CP
                        if model.p_CNA[p, n]
                    )
                    for n in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, n_tilde, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[n, n_tilde]
                        for n in model.s_N
                        if model.p_NNA[n, n_tilde]
                    )
                    for n_tilde in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, p, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[n, p]
                        for n in model.s_N
                        if model.p_NCA[n, p]
                    )
                    for p in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, k, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[n, k]
                        for n in model.s_N
                        if model.p_NKA[n, k]
                    )
                    for k in model.s_K
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, s, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[n, s]
                        for n in model.s_N
                        if model.p_NSA[n, s]
                    )
                    for s in model.s_S
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, r, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[n, r]
                        for n in model.s_N
                        if model.p_NRA[n, r]
                    )
                    for r in model.s_R
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, o, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[n, o]
                        for n in model.s_N
                        if model.p_NOA[n, o]
                    )
                    for o in model.s_O
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[f, p, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[f, p]
                        for f in model.s_F
                        if model.p_FCA[f, p]
                    )
                    for p in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[r, n, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[r, n]
                        for r in model.s_R
                        if model.p_RNA[r, n]
                    )
                    for n in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[r, p, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[r, p]
                        for r in model.s_R
                        if model.p_RCA[r, p]
                    )
                    for p in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[r, k, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[r, k]
                        for r in model.s_R
                        if model.p_RKA[r, k]
                    )
                    for k in model.s_K
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, n, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[s, n]
                        for s in model.s_S
                        if model.p_SNA[s, n]
                    )
                    for n in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, p, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[s, p]
                        for s in model.s_S
                        if model.p_SCA[s, p]
                    )
                    for p in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, k, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[s, k]
                        for s in model.s_S
                        if model.p_SKA[s, k]
                    )
                    for k in model.s_K
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, r, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[s, r]
                        for s in model.s_S
                        if model.p_SRA[s, r]
                    )
                    for r in model.s_R
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, o, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[s, o]
                        for s in model.s_S
                        if model.p_SOA[s, o]
                    )
                    for o in model.s_O
                )
                for d in model.s_D
            )
        )

        return process_constraint(constraint)

    def PipelineExpansionCapExCapacityBasedRule(model):
        constraint = model.v_C_PipelineCapEx == (
            sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[p, p_tilde, d]
                        * model.p_kappa_Pipeline[p, p_tilde, d]
                        * model.p_delta_Pipeline[d]
                        for p in model.s_PP
                        if model.p_PCA[p, p_tilde]
                    )
                    for p_tilde in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[p, n, d]
                        * model.p_kappa_Pipeline[p, n, d]
                        * model.p_delta_Pipeline[d]
                        for p in model.s_PP
                        if model.p_PNA[p, n]
                    )
                    for n in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[p, p_tilde, d]
                        * model.p_kappa_Pipeline[p, p_tilde, d]
                        * model.p_delta_Pipeline[d]
                        for p in model.s_PP
                        if model.p_PPA[p, p_tilde]
                    )
                    for p_tilde in model.s_PP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[p, n, d]
                        * model.p_kappa_Pipeline[p, n, d]
                        * model.p_delta_Pipeline[d]
                        for p in model.s_CP
                        if model.p_CNA[p, n]
                    )
                    for n in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, n_tilde, d]
                        * model.p_kappa_Pipeline[n, n_tilde, d]
                        * model.p_delta_Pipeline[d]
                        for n in model.s_N
                        if model.p_NNA[n, n_tilde]
                    )
                    for n_tilde in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, p, d]
                        * model.p_kappa_Pipeline[n, p, d]
                        * model.p_delta_Pipeline[d]
                        for n in model.s_N
                        if model.p_NCA[n, p]
                    )
                    for p in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, k, d]
                        * model.p_kappa_Pipeline[n, k, d]
                        * model.p_delta_Pipeline[d]
                        for n in model.s_N
                        if model.p_NKA[n, k]
                    )
                    for k in model.s_K
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, s, d]
                        * model.p_kappa_Pipeline[n, s, d]
                        * model.p_delta_Pipeline[d]
                        for n in model.s_N
                        if model.p_NSA[n, s]
                    )
                    for s in model.s_S
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, r, d]
                        * model.p_kappa_Pipeline[n, r, d]
                        * model.p_delta_Pipeline[d]
                        for n in model.s_N
                        if model.p_NRA[n, r]
                    )
                    for r in model.s_R
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[n, o, d]
                        * model.p_kappa_Pipeline[n, o, d]
                        * model.p_delta_Pipeline[d]
                        for n in model.s_N
                        if model.p_NOA[n, o]
                    )
                    for o in model.s_O
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[f, p, d]
                        * model.p_kappa_Pipeline[f, p, d]
                        * model.p_delta_Pipeline[d]
                        for f in model.s_F
                        if model.p_FCA[f, p]
                    )
                    for p in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[r, n, d]
                        * model.p_kappa_Pipeline[r, n, d]
                        * model.p_delta_Pipeline[d]
                        for r in model.s_R
                        if model.p_RNA[r, n]
                    )
                    for n in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[r, p, d]
                        * model.p_kappa_Pipeline[r, p, d]
                        * model.p_delta_Pipeline[d]
                        for r in model.s_R
                        if model.p_RCA[r, p]
                    )
                    for p in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[r, k, d]
                        * model.p_kappa_Pipeline[r, k, d]
                        * model.p_delta_Pipeline[d]
                        for r in model.s_R
                        if model.p_RKA[r, k]
                    )
                    for k in model.s_K
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, n, d]
                        * model.p_kappa_Pipeline[s, n, d]
                        * model.p_delta_Pipeline[d]
                        for s in model.s_S
                        if model.p_SNA[s, n]
                    )
                    for n in model.s_N
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, p, d]
                        * model.p_kappa_Pipeline[s, p, d]
                        * model.p_delta_Pipeline[d]
                        for s in model.s_S
                        if model.p_SCA[s, p]
                    )
                    for p in model.s_CP
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, k, d]
                        * model.p_kappa_Pipeline[s, k, d]
                        * model.p_delta_Pipeline[d]
                        for s in model.s_S
                        if model.p_SKA[s, k]
                    )
                    for k in model.s_K
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, r, d]
                        * model.p_kappa_Pipeline[s, r, d]
                        * model.p_delta_Pipeline[d]
                        for s in model.s_S
                        if model.p_SRA[s, r]
                    )
                    for r in model.s_R
                )
                for d in model.s_D
            )
            + sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[s, o, d]
                        * model.p_kappa_Pipeline[s, o, d]
                        * model.p_delta_Pipeline[d]
                        for s in model.s_S
                        if model.p_SOA[s, o]
                    )
                    for o in model.s_O
                )
                for d in model.s_D
            )
        )

        return process_constraint(constraint)

    if model.config.pipeline_cost == PipelineCost.distance_based:
        model.PipelineExpansionCapEx = Constraint(
            rule=PipelineExpansionCapExDistanceBasedRule,
            doc="Pipeline construction or capacity expansion cost",
        )
    elif model.config.pipeline_cost == PipelineCost.capacity_based:
        model.PipelineExpansionCapEx = Constraint(
            rule=PipelineExpansionCapExCapacityBasedRule,
            doc="Pipeline construction or capacity expansion cost",
        )

    def SlackCostsRule(model):
        constraint = model.v_C_Slack == (
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
                    * model.p_psi_PipelineCapacity
                    for p in model.s_PP
                    if model.p_PCA[p, p_tilde]
                )
                for p_tilde in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[p, p_tilde]
                    * model.p_psi_PipelineCapacity
                    for p in model.s_CP
                    if model.p_CCA[p, p_tilde]
                )
                for p_tilde in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[p, n] * model.p_psi_PipelineCapacity
                    for p in model.s_PP
                    if model.p_PNA[p, n]
                )
                for n in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[p, p_tilde]
                    * model.p_psi_PipelineCapacity
                    for p in model.s_PP
                    if model.p_PPA[p, p_tilde]
                )
                for p_tilde in model.s_PP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[p, n] * model.p_psi_PipelineCapacity
                    for p in model.s_CP
                    if model.p_CNA[p, n]
                )
                for n in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, n_tilde]
                    * model.p_psi_PipelineCapacity
                    for n in model.s_N
                    if model.p_NNA[n, n_tilde]
                )
                for n_tilde in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, p] * model.p_psi_PipelineCapacity
                    for n in model.s_N
                    if model.p_NCA[n, p]
                )
                for p in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, k] * model.p_psi_PipelineCapacity
                    for n in model.s_N
                    if model.p_NKA[n, k]
                )
                for k in model.s_K
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, s] * model.p_psi_PipelineCapacity
                    for n in model.s_N
                    if model.p_NSA[n, s]
                )
                for s in model.s_S
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, r] * model.p_psi_PipelineCapacity
                    for n in model.s_N
                    if model.p_NRA[n, r]
                )
                for r in model.s_R
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[n, o] * model.p_psi_PipelineCapacity
                    for n in model.s_N
                    if model.p_NOA[n, o]
                )
                for o in model.s_O
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[f, p] * model.p_psi_PipelineCapacity
                    for f in model.s_F
                    if model.p_FCA[f, p]
                )
                for p in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[r, n] * model.p_psi_PipelineCapacity
                    for r in model.s_R
                    if model.p_RNA[r, n]
                )
                for n in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[r, p] * model.p_psi_PipelineCapacity
                    for r in model.s_R
                    if model.p_RCA[r, p]
                )
                for p in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[r, k] * model.p_psi_PipelineCapacity
                    for r in model.s_R
                    if model.p_RKA[r, k]
                )
                for k in model.s_K
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, n] * model.p_psi_PipelineCapacity
                    for s in model.s_S
                    if model.p_SNA[s, n]
                )
                for n in model.s_N
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, p] * model.p_psi_PipelineCapacity
                    for s in model.s_S
                    if model.p_SCA[s, p]
                )
                for p in model.s_CP
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, k] * model.p_psi_PipelineCapacity
                    for s in model.s_S
                    if model.p_SKA[s, k]
                )
                for k in model.s_K
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, r] * model.p_psi_PipelineCapacity
                    for s in model.s_S
                    if model.p_SRA[s, r]
                )
                for r in model.s_R
            )
            + sum(
                sum(
                    model.v_S_PipelineCapacity[s, o] * model.p_psi_PipelineCapacity
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
        return process_constraint(constraint)

    model.SlackCosts = Constraint(rule=SlackCostsRule, doc="Slack costs")

    # model.SlackCosts.pprint()

    def LogicConstraintDisposalRule(model, k):
        constraint = sum(model.vb_y_Disposal[k, i] for i in model.s_I) == 1
        return process_constraint(constraint)

    model.LogicConstraintDisposal = Constraint(
        model.s_K, rule=LogicConstraintDisposalRule, doc="Logic constraint disposal"
    )

    # model.LogicConstraintDisposal.pprint()

    def LogicConstraintStorageRule(model, s):
        constraint = sum(model.vb_y_Storage[s, c] for c in model.s_C) == 1
        return process_constraint(constraint)

    model.LogicConstraintStorage = Constraint(
        model.s_S, rule=LogicConstraintStorageRule, doc="Logic constraint storage"
    )

    # model.LogicConstraintStorage.pprint()

    def LogicConstraintTreatmentRule(model, r):
        constraint = (
            sum(
                sum(
                    model.vb_y_Treatment[r, b, j] for j in model.s_J
                    )
                for b in model.s_B
                ) == 1
            )
        return process_constraint(constraint)
    
    model.LogicConstraintTreatmentAssignment = Constraint(
        model.s_R, rule=LogicConstraintTreatmentRule,
        doc="Treatment technology assignment"
    )

    def LogicConstraintTreatmentRule2(model, r, t):
        constraint = (
            (
                sum(model.v_F_Piped[r, p, t]
                    for p in model.s_CP if model.p_RCA[r, p])
                + sum(model.v_F_Piped[r, s, t]
                      for s in model.s_S if model.p_RSA[r, s])
            ) <= 1e8 * (
                1 - sum(model.vb_y_Treatment[r, "DS", j]
                     for j in model.s_J
                     )
             )
            )
        return process_constraint(constraint)
    
    model.LogicConstraintDesalinationFlow = Constraint(
        model.s_R, model.s_T,
        rule=LogicConstraintTreatmentRule2,
        doc="Logic constraint for flow after desalination"
    )
    
    def LogicConstraintTreatmentRule3(model, r, t):
        constraint = (
            model.v_F_WaterRemoved[r, t] <=
            1e8 * sum(model.vb_y_Treatment[r, "DS", j] for j in model.s_J)
            )
        return process_constraint(constraint)
    
    model.LogicConstraintNoDesalinationFlow = Constraint(
        model.s_R, model.s_T,
        rule=LogicConstraintTreatmentRule3,
        doc="Logic constraint for flow if not desalination"
    )
    
    # def LogicConstraintTreatmentRule4(model, r, t):
    #     constraint = (
    #         model.v_F_WaterRemoved[r, t] <=
    #         1e8 * sum(model.vb_y_Treatment[r, "EV", j] for j in model.s_J)
    #         )
    #     return process_constraint(constraint)
    
    # model.LogicConstraintNoDesalinationFlow = Constraint(
    #     model.s_R, model.s_T,
    #     rule=LogicConstraintTreatmentRule4,
    #     doc="Logic constraint for flow if evaporation"
    # )

    # TODO: make this more general by checking if there is water at t = 1
    # TODO: generalize to not set evaporation at all storage sites 
    def LogicConstraintTreatmentRule5(model, s, t):
        if t == model.s_T.first():
            constraint = (
                model.v_F_StorageEvaporationStream[s, t] ==
                0
                )
        else:
            constraint = (
                model.v_F_StorageEvaporationStream[s, t] ==
                model.p_omega_EvaporationRate
                * sum(
                    sum(
                        model.vb_y_Treatment[r, "EV", j]
                        for j in model.s_J
                        ) for r in model.s_R
                )
                )
        return process_constraint(constraint)
    
    model.LogicConstraintEvaporationFlow = Constraint(
        model.s_S, model.s_T,
        rule=LogicConstraintTreatmentRule5,
        doc="Logic constraint for flow if evaporation"
    )

    # def LogicConstraintTreatmentRule(model, r):
    #     constraint = sum(model.vb_y_Treatment[r, j] for j in model.s_J) == 1

    #     return process_constraint(constraint)

    # model.LogicConstraintTreatment = Constraint(
    #     model.s_R, rule=LogicConstraintTreatmentRule, doc="Logic constraint treatment"
    # )

    # model.LogicConstraintTreatment.pprint()

    def LogicConstraintPipelineRule(model, l, l_tilde):
        if l in model.s_PP and l_tilde in model.s_CP:
            if model.p_PCA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_N:
            if model.p_PNA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_PP and l_tilde in model.s_PP:
            if model.p_PPA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_CP and l_tilde in model.s_N:
            if model.p_CNA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_N:
            if model.p_NNA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_CP:
            if model.p_NCA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_K:
            if model.p_NKA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_S:
            if model.p_NSA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_R:
            if model.p_NRA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_N and l_tilde in model.s_O:
            if model.p_NOA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_F and l_tilde in model.s_CP:
            if model.p_FCA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_N:
            if model.p_RNA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_CP:
            if model.p_RCA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_R and l_tilde in model.s_K:
            if model.p_RKA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_N:
            if model.p_SNA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_CP:
            if model.p_SCA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_K:
            if model.p_SKA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_R:
            if model.p_SRA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        elif l in model.s_S and l_tilde in model.s_O:
            if model.p_SOA[l, l_tilde]:
                constraint = (
                    sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.LogicConstraintPipeline = Constraint(
        model.s_L,
        model.s_L,
        rule=LogicConstraintPipelineRule,
        doc="Logic constraint pipelines",
    )

    def ReuseDestinationDeliveriesRule(model, p, t):
        constraint = model.v_F_ReuseDestination[p, t] == sum(
            model.v_F_Piped[l, p, t] + model.v_F_Trucked[l, p, t]
            for l in model.s_L
            if (l not in model.s_F)
        )
        return process_constraint(constraint)

    model.ReuseDestinationDeliveries = Constraint(
        model.s_CP,
        model.s_T,
        rule=ReuseDestinationDeliveriesRule,
        doc="Reuse destinations volume",
    )

    # model.ReuseDestinationDeliveries.pprint()

    def DisposalDestinationDeliveriesRule(model, k, t):
        constraint = model.v_F_DisposalDestination[k, t] == sum(
            model.v_F_Piped[l, k, t] + model.v_F_Trucked[l, k, t] for l in model.s_L
        )

        return process_constraint(constraint)

    model.DisposalDestinationDeliveries = Constraint(
        model.s_K,
        model.s_T,
        rule=DisposalDestinationDeliveriesRule,
        doc="Disposal destinations volume",
    )

    # model.DisposalDestinationDeliveries.pprint()

    def BeneficialReuseDeliveriesRule(model, o, t):
        constraint = model.v_F_BeneficialReuseDestination[o, t] == sum(
            model.v_F_Piped[n, o, t] for n in model.s_N if model.p_NOA[n, o]
        ) + sum(model.v_F_Piped[s, o, t] for s in model.s_S if model.p_SOA[s, o]) + sum(
            model.v_F_Trucked[p, o, t] for p in model.s_PP if model.p_POT[p, o]
        )
        return process_constraint(constraint)

    model.BeneficialReuseDeliveries = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseDeliveriesRule,
        doc="Beneficial reuse destinations volume",
    )

    def CompletionsWaterDeliveriesRule(model, p, t):
        constraint = model.v_F_CompletionsDestination[p, t] == (
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
            + sum(model.v_F_Piped[r, p, t] for r in model.s_R if model.p_RCA[r, p])
            + sum(model.v_F_Sourced[f, p, t] for f in model.s_F if model.p_FCA[f, p])
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
            + sum(model.v_F_Trucked[s, p, t] for s in model.s_S if model.p_SCT[s, p])
            + sum(model.v_F_Trucked[f, p, t] for f in model.s_F if model.p_FCT[f, p])
            - model.v_F_PadStorageIn[p, t]
        )

        return process_constraint(constraint)

    model.CompletionsWaterDeliveries = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsWaterDeliveriesRule,
        doc="Completions water volume",
    )

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

    model.objective = Objective(
        expr=model.v_Z, sense=minimize, doc="Objective function"
    )

    return model


def water_quality(model):
    # region Fix solved Strategic Model variables
    for var in model.component_objects(Var):
        for index in var:
            # Check if the variable is indexed
            if index is None:
                # Check if the value can reasonably be assumed to be non-zero
                if abs(var.value) > 0.0000001:
                    var.fix()
                # Otherwise, fix to 0
                else:
                    var.fix(0)
            elif index is not None:
                # Check if the value can reasonably be assumed to be non-zero
                if var[index].value and abs(var[index].value) > 0.0000001:
                    var[index].fix()
                # Otherwise, fix to 0
                else:
                    var[index].fix(0)
    # endregion

    # Create block for calculating quality at each location in the model
    model.quality = Block()

    # region Add sets, parameters and constraints

    # Create a set for Completions Pad storage by appending the storage label to each item in the CompletionsPads Set
    storage_label = "-storage"
    model.df_sets["CompletionsPadsStorage"] = [
        p + storage_label for p in model.df_sets["CompletionsPads"]
    ]
    model.quality.s_CP_Storage = Set(
        initialize=model.df_sets["CompletionsPadsStorage"],
        doc="Completions Pad Storage Tanks",
    )

    # Create a set for water quality at Completions Pads intermediate flows (i.e. the blended trucked and piped water to pad)
    intermediate_label = "-intermediate"
    model.df_sets["CompletionsPadsIntermediate"] = [
        p + intermediate_label for p in model.df_sets["CompletionsPads"]
    ]
    model.quality.s_CP_Intermediate = Set(
        initialize=model.df_sets["CompletionsPadsIntermediate"],
        doc="Completions Pad Intermediate Flows",
    )

    # Create a set of locations to track water quality over
    model.quality.s_WQL = Set(
        initialize=(
            model.s_L | model.quality.s_CP_Storage | model.quality.s_CP_Intermediate
        ),
        doc="Locations with tracked water quality ",
    )

    # Quality at pad
    model.quality.p_nu_pad = Param(
        model.s_P,
        model.s_W,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters["PadWaterQuality"].items()
        },
        units=model.model_units["concentration"],
        doc="Water Quality at pad [concentration]",
    )
    # Quality of Sourced Water
    model.quality.p_nu_freshwater = Param(
        model.s_F,
        model.s_W,
        default=0,
        initialize=pyunits.convert_value(
            0,
            from_units=model.user_units["concentration"],
            to_units=model.model_units["concentration"],
        ),
        units=model.model_units["concentration"],
        doc="Water Quality of freshwater [concentration]",
    )
    # Initial water quality at storage site
    model.quality.p_xi_StorageSite = Param(
        model.s_S,
        model.s_W,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters["StorageInitialWaterQuality"].items()
        },
        units=model.model_units["concentration"],
        doc="Initial Water Quality at storage site [concentration]",
    )
    # Initial water quality at completions pad storage tank
    model.quality.p_xi_PadStorage = Param(
        model.s_CP,
        model.s_W,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters[
                "PadStorageInitialWaterQuality"
            ].items()
        },
        units=model.model_units["concentration"],
        doc="Initial Water Quality at storage site [concentration]",
    )
    # Add variable to track water quality at each location over time
    model.quality.v_Q = Var(
        model.quality.s_WQL,
        model.s_W,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["concentration"],
        doc="Water quality at location [concentration]",
    )
    # v_X is solely used to make sure model has an objective value
    model.quality.v_X = Var(
        within=Reals,
        units=model.model_units["concentration"],
        doc="Water quality objective value ",
    )
    # endregion

    # region Disposal
    # Material Balance
    def DisposalWaterQualityRule(b, k, w, t):
        constraint = (
            sum(
                b.parent_block().v_F_Piped[n, k, t] * b.v_Q[n, w, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NKA[n, k]
            )
            + sum(
                b.parent_block().v_F_Piped[s, k, t] * b.v_Q[s, w, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SKA[s, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[s, k, t] * b.v_Q[s, w, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SKT[s, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, k, t] * b.p_nu_pad[p, w]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PKT[p, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, k, t] * b.p_nu_pad[p, w]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CKT[p, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[r, k, t] * b.v_Q[r, w, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_RKT[r, k]
            )
            == b.v_Q[k, w, t] * b.parent_block().v_F_DisposalDestination[k, t]
        )
        return process_constraint(constraint)

    model.quality.DisposalWaterQuality = Constraint(
        model.s_K,
        model.s_W,
        model.s_T,
        rule=DisposalWaterQualityRule,
        doc="Disposal water quality rule",
    )
    # endregion

    # region Storage
    def StorageSiteWaterQualityRule(b, s, w, t):
        if t == b.parent_block().s_T.first():
            constraint = b.parent_block().p_lambda_Storage[s] * b.p_xi_StorageSite[
                s, w
            ] + sum(
                b.parent_block().v_F_Piped[n, s, t] * b.v_Q[n, w, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NSA[n, s]
            ) + sum(
                b.parent_block().v_F_Piped[r, s, t] * b.v_Q[r, w, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_RSA[r, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, w]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PST[p, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, w]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CST[p, s]
            ) == b.v_Q[
                s, w, t
            ] * (
                b.parent_block().v_L_Storage[s, t]
                + sum(
                    b.parent_block().v_F_Piped[s, n, t]
                    for n in b.parent_block().s_N
                    if b.parent_block().p_SNA[s, n]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, p, t]
                    for p in b.parent_block().s_CP
                    if b.parent_block().p_SCA[s, p]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, k, t]
                    for k in b.parent_block().s_K
                    if b.parent_block().p_SKA[s, k]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, r, t]
                    for r in b.parent_block().s_R
                    if b.parent_block().p_SRA[s, r]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, o, t]
                    for o in b.parent_block().s_O
                    if b.parent_block().p_SOA[s, o]
                )
                + sum(
                    b.parent_block().v_F_Trucked[s, p, t]
                    for p in b.parent_block().s_CP
                    if b.parent_block().p_SCT[s, p]
                )
                + sum(
                    b.parent_block().v_F_Trucked[s, k, t]
                    for k in b.parent_block().s_K
                    if b.parent_block().p_SKT[s, k]
                )
            )
        else:
            constraint = b.parent_block().v_L_Storage[
                s, b.parent_block().s_T.prev(t)
            ] * b.v_Q[s, w, b.parent_block().s_T.prev(t)] + sum(
                b.parent_block().v_F_Piped[n, s, t] * b.v_Q[n, w, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NSA[n, s]
            ) + sum(
                b.parent_block().v_F_Piped[r, s, t] * b.v_Q[r, w, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_RSA[r, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, w]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PST[p, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, w]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CST[p, s]
            ) == b.v_Q[
                s, w, t
            ] * (
                b.parent_block().v_L_Storage[s, t]
                + sum(
                    b.parent_block().v_F_Piped[s, n, t]
                    for n in b.parent_block().s_N
                    if b.parent_block().p_SNA[s, n]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, p, t]
                    for p in b.parent_block().s_CP
                    if b.parent_block().p_SCA[s, p]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, k, t]
                    for k in b.parent_block().s_K
                    if b.parent_block().p_SKA[s, k]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, r, t]
                    for r in b.parent_block().s_R
                    if b.parent_block().p_SRA[s, r]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, o, t]
                    for o in b.parent_block().s_O
                    if b.parent_block().p_SOA[s, o]
                )
                + sum(
                    b.parent_block().v_F_Trucked[s, p, t]
                    for p in b.parent_block().s_CP
                    if b.parent_block().p_SCT[s, p]
                )
                + sum(
                    b.parent_block().v_F_Trucked[s, k, t]
                    for k in b.parent_block().s_K
                    if b.parent_block().p_SKT[s, k]
                )
            )
        return process_constraint(constraint)

    model.quality.StorageSiteWaterQuality = Constraint(
        model.s_S,
        model.s_W,
        model.s_T,
        rule=StorageSiteWaterQualityRule,
        doc="Storage site water quality rule",
    )
    # endregion

    # region Treatment
    def TreatmentWaterQualityRule(b, r, w, t):
        constraint = b.parent_block().p_epsilon_Treatment[r, w] * (
            sum(
                b.parent_block().v_F_Piped[n, r, t] * b.v_Q[n, w, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NRA[n, r]
            )
            + sum(
                b.parent_block().v_F_Piped[s, r, t] * b.v_Q[s, w, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SRA[s, r]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, r, t] * b.p_nu_pad[p, w]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PRT[p, r]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, r, t] * b.p_nu_pad[p, w]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CRT[p, r]
            )
        ) == b.v_Q[r, w, t] * (
            sum(
                b.parent_block().v_F_Piped[r, p, t]
                for p in b.parent_block().s_CP
                if b.parent_block().p_RCA[r, p]
            )
            + sum(
                b.parent_block().v_F_Piped[r, s, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_RSA[r, s]
            )
            # + b.parent_block().v_F_UnusedTreatedWater[r, t]
        )
        return process_constraint(constraint)

    model.quality.TreatmentWaterQuality = Constraint(
        model.s_R,
        model.s_W,
        model.s_T,
        rule=TreatmentWaterQualityRule,
        doc="Treatment water quality",
    )
    # endregion

    # region Network
    def NetworkNodeWaterQualityRule(b, n, w, t):
        constraint = sum(
            b.parent_block().v_F_Piped[p, n, t] * b.p_nu_pad[p, w]
            for p in b.parent_block().s_PP
            if b.parent_block().p_PNA[p, n]
        ) + sum(
            b.parent_block().v_F_Piped[p, n, t] * b.p_nu_pad[p, w]
            for p in b.parent_block().s_CP
            if b.parent_block().p_CNA[p, n]
        ) + sum(
            b.parent_block().v_F_Piped[s, n, t] * b.v_Q[s, w, t]
            for s in b.parent_block().s_S
            if b.parent_block().p_SNA[s, n]
        ) + sum(
            b.parent_block().v_F_Piped[n_tilde, n, t] * b.v_Q[n_tilde, w, t]
            for n_tilde in b.parent_block().s_N
            if b.parent_block().p_NNA[n_tilde, n]
        ) == b.v_Q[
            n, w, t
        ] * (
            sum(
                b.parent_block().v_F_Piped[n, n_tilde, t]
                for n_tilde in b.parent_block().s_N
                if b.parent_block().p_NNA[n, n_tilde]
            )
            + sum(
                b.parent_block().v_F_Piped[n, p, t]
                for p in b.parent_block().s_CP
                if b.parent_block().p_NCA[n, p]
            )
            + sum(
                b.parent_block().v_F_Piped[n, k, t]
                for k in b.parent_block().s_K
                if b.parent_block().p_NKA[n, k]
            )
            + sum(
                b.parent_block().v_F_Piped[n, r, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_NRA[n, r]
            )
            + sum(
                b.parent_block().v_F_Piped[n, s, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_NSA[n, s]
            )
            + sum(
                b.parent_block().v_F_Piped[n, o, t]
                for o in b.parent_block().s_O
                if b.parent_block().p_NOA[n, o]
            )
        )
        return process_constraint(constraint)

    model.quality.NetworkWaterQuality = Constraint(
        model.s_N,
        model.s_W,
        model.s_T,
        rule=NetworkNodeWaterQualityRule,
        doc="Network water quality",
    )
    # endregion

    # region Beneficial Reuse
    def BeneficialReuseWaterQuality(b, o, w, t):
        constraint = (
            sum(
                b.parent_block().v_F_Piped[n, o, t] * b.v_Q[n, w, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NOA[n, o]
            )
            + sum(
                b.parent_block().v_F_Piped[s, o, t] * b.v_Q[s, w, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SOA[s, o]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, o, t] * b.p_nu_pad[p, w]
                for p in b.parent_block().s_PP
                if b.parent_block().p_POT[p, o]
            )
            == b.v_Q[o, w, t] * b.parent_block().v_F_BeneficialReuseDestination[o, t]
        )
        return process_constraint(constraint)

    model.quality.BeneficialReuseWaterQuality = Constraint(
        model.s_O,
        model.s_W,
        model.s_T,
        rule=BeneficialReuseWaterQuality,
        doc="Beneficial reuse capacity",
    )
    # endregion

    # region Completions Pad

    # Water that is Piped and Trucked to a completions pad is mixed and split into two output streams.
    # Stream (1) goes to the completions pad and stream (2) is input to the completions storage.
    # This is the intermediate step.
    # Finally, water that meets completions demand comes from two inputs.
    # The first input is output stream (1) from the intermediate step.
    # The second is outgoing flow from the storage tank.

    def CompletionsPadIntermediateWaterQuality(b, p, w, t):
        constraint = sum(
            b.parent_block().v_F_Piped[n, p, t] * b.v_Q[n, w, t]
            for n in b.parent_block().s_N
            if b.parent_block().p_NCA[n, p]
        ) + sum(
            b.parent_block().v_F_Piped[p_tilde, p, t] * b.v_Q[p_tilde, w, t]
            for p_tilde in b.parent_block().s_PP
            if b.parent_block().p_PCA[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Piped[s, p, t] * b.v_Q[s, w, t]
            for s in b.parent_block().s_S
            if b.parent_block().p_SCA[s, p]
        ) + sum(
            b.parent_block().v_F_Piped[p_tilde, p, t] * b.v_Q[p_tilde, w, t]
            for p_tilde in b.parent_block().s_CP
            if b.parent_block().p_CCA[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Piped[r, p, t] * b.v_Q[r, w, t]
            for r in b.parent_block().s_R
            if b.parent_block().p_RCA[r, p]
        ) + sum(
            b.parent_block().v_F_Sourced[f, p, t] * b.p_nu_freshwater[f, w]
            for f in b.parent_block().s_F
            if b.parent_block().p_FCA[f, p]
        ) + sum(
            b.parent_block().v_F_Trucked[p_tilde, p, t] * b.v_Q[p_tilde, w, t]
            for p_tilde in b.parent_block().s_PP
            if b.parent_block().p_PCT[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Trucked[p_tilde, p, t] * b.v_Q[p_tilde, w, t]
            for p_tilde in b.parent_block().s_CP
            if b.parent_block().p_CCT[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Trucked[s, p, t] * b.v_Q[s, w, t]
            for s in b.parent_block().s_S
            if b.parent_block().p_SCT[s, p]
        ) + sum(
            b.parent_block().v_F_Trucked[f, p, t] * b.p_nu_freshwater[f, w]
            for f in b.parent_block().s_F
            if b.parent_block().p_FCT[f, p]
        ) == b.v_Q[
            p + intermediate_label, w, t
        ] * (
            b.parent_block().v_F_PadStorageIn[p, t]
            + b.parent_block().v_F_CompletionsDestination[p, t]
        )
        return process_constraint(constraint)

    model.quality.CompletionsPadIntermediateWaterQuality = Constraint(
        model.s_CP,
        model.s_W,
        model.s_T,
        rule=CompletionsPadIntermediateWaterQuality,
        doc="Completions pad water quality",
    )

    def CompletionsPadWaterQuality(b, p, w, t):
        constraint = (
            b.parent_block().v_F_PadStorageOut[p, t] * b.v_Q[p + storage_label, w, t]
            + b.parent_block().v_F_CompletionsDestination[p, t]
            * b.v_Q[p + intermediate_label, w, t]
            == b.v_Q[p, w, t] * b.parent_block().p_gamma_Completions[p, t]
        )
        return process_constraint(constraint)

    model.quality.CompletionsPadWaterQuality = Constraint(
        model.s_CP,
        model.s_W,
        model.s_T,
        rule=CompletionsPadWaterQuality,
        doc="Completions pad water quality",
    )
    # endregion

    # region Completion Pad Storage
    def CompletionsPadStorageWaterQuality(b, p, w, t):
        if t == b.parent_block().s_T.first():
            constraint = b.p_xi_PadStorage[p, w] * b.parent_block().p_lambda_PadStorage[
                p
            ] + b.v_Q[p + intermediate_label, w, t] * b.parent_block().v_F_PadStorageIn[
                p, t
            ] == b.v_Q[
                p + storage_label, w, t
            ] * (
                b.parent_block().v_L_PadStorage[p, t]
                + b.parent_block().v_F_PadStorageOut[p, t]
            )
        else:
            constraint = b.v_Q[
                p + storage_label, w, b.parent_block().s_T.prev(t)
            ] * b.parent_block().v_L_PadStorage[
                p, b.parent_block().s_T.prev(t)
            ] + b.v_Q[
                p + intermediate_label, w, t
            ] * b.parent_block().v_F_PadStorageIn[
                p, t
            ] == b.v_Q[
                p + storage_label, w, t
            ] * (
                b.parent_block().v_L_PadStorage[p, t]
                + b.parent_block().v_F_PadStorageOut[p, t]
            )
        return process_constraint(constraint)

    model.quality.CompletionsPadStorageWaterQuality = Constraint(
        model.s_CP,
        model.s_W,
        model.s_T,
        rule=CompletionsPadStorageWaterQuality,
        doc="Completions pad storage water quality",
    )
    # endregion

    # Define Objective
    def ObjectiveFunctionRule(b):
        return b.v_X == sum(
            sum(
                sum(b.v_Q[p, w, t] for p in b.parent_block().s_P)
                for w in b.parent_block().s_W
            )
            for t in b.parent_block().s_T
        )

    model.quality.ObjectiveFunction = Constraint(
        rule=ObjectiveFunctionRule, doc="Objective function water quality"
    )

    model.quality.objective = Objective(
        expr=model.quality.v_X, sense=minimize, doc="Objective function"
    )

    return model


def process_constraint(constraint):
    # Check if the constraint contains a variable
    if list(identify_variables(constraint)):
        return constraint
    # Skip constraint if empty
    else:
        return Constraint.Skip


def postprocess_water_quality_calculation(model, opt):
    # Add water quality formulation to input solved model
    water_quality_model = water_quality(model)

    # Calculate water quality. The following conditional is used to avoid errors when
    # using Gurobi solver
    try:
        opt.solve(water_quality_model.quality, tee=True, save_results=False)
    except ValueError:
        opt.solve(water_quality_model.quality, tee=True)

    return water_quality_model


def scale_model(model, scaling_factor=None):

    if scaling_factor is None:
        scaling_factor = 1000000

    model.scaling_factor = Suffix(direction=Suffix.EXPORT)

    # Scaling variables
    model.scaling_factor[model.v_Z] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Disposal] = 1 / scaling_factor
    model.scaling_factor[model.v_C_DisposalCapEx] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Piped] = 1 / scaling_factor
    model.scaling_factor[model.v_C_PipelineCapEx] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Reuse] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Slack] = 1 / (scaling_factor * 100)
    model.scaling_factor[model.v_C_Sourced] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Storage] = 1 / scaling_factor
    model.scaling_factor[model.v_C_StorageCapEx] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalDisposal] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalPiping] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalStorage] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalSourced] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalTreatment] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalTrucking] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Treatment] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TreatmentCapEx] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Trucked] = 1 / scaling_factor
    model.scaling_factor[model.v_D_Capacity] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Capacity] = 1 / scaling_factor
    model.scaling_factor[model.v_F_DisposalDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_PadStorageIn] = 1 / scaling_factor
    model.scaling_factor[model.v_F_PadStorageOut] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Piped] = 1 / scaling_factor
    model.scaling_factor[model.v_F_ReuseDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_WaterRemoved] = 1 / scaling_factor
    model.scaling_factor[model.v_F_BeneficialReuseDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_CompletionsDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Sourced] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalDisposed] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalReused] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalSourced] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalTrucked] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Trucked] = 1 / scaling_factor
    model.scaling_factor[model.v_L_PadStorage] = 1 / scaling_factor
    model.scaling_factor[model.v_L_Storage] = 1 / scaling_factor
    model.scaling_factor[model.v_R_Storage] = 1 / scaling_factor
    model.scaling_factor[model.v_R_TotalStorage] = 1 / scaling_factor
    model.scaling_factor[model.v_S_DisposalCapacity] = 1
    model.scaling_factor[model.v_S_Flowback] = 1
    model.scaling_factor[model.v_S_FracDemand] = 1
    model.scaling_factor[model.v_S_PipelineCapacity] = 1
    model.scaling_factor[model.v_S_Production] = 1
    model.scaling_factor[model.v_S_ReuseCapacity] = 1
    model.scaling_factor[model.v_S_TreatmentCapacity] = 1
    model.scaling_factor[model.v_S_StorageCapacity] = 1
    model.scaling_factor[model.v_T_Capacity] = 1 / scaling_factor
    model.scaling_factor[model.v_X_Capacity] = 1 / scaling_factor

    # Scaling constraints
    if model.config.objective == Objectives.cost:
        model.scaling_factor[model.CostObjectiveFunction] = 1 / scaling_factor
    elif model.config.objective == Objectives.reuse:
        model.scaling_factor[model.ReuseObjectiveFunction] = 1 / scaling_factor

    model.scaling_factor[model.BeneficialReuseCapacity] = 1 / scaling_factor
    # This constraints contains only binary variables
    model.scaling_factor[model.BidirectionalFlow1] = 1
    model.scaling_factor[model.BidirectionalFlow2] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadDemandBalance] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadStorageBalance] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadStorageCapacity] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadSupplyBalance] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadTruckOffloadingCapacity] = (
        1 / scaling_factor
    )
    model.scaling_factor[model.CompletionsReuseCost] = 1 / scaling_factor
    model.scaling_factor[model.DisposalCapacity] = 1 / scaling_factor
    model.scaling_factor[model.DisposalCapacityExpansion] = 1 / scaling_factor
    model.scaling_factor[model.DisposalCost] = 1 / scaling_factor
    model.scaling_factor[model.DisposalDestinationDeliveries] = 1 / scaling_factor
    model.scaling_factor[model.DisposalExpansionCapEx] = 1 / scaling_factor
    model.scaling_factor[model.FreshwaterSourcingCapacity] = 1 / scaling_factor
    model.scaling_factor[model.FreshSourcingCost] = 1 / scaling_factor
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintDisposal] = 1
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintPipeline] = 1
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintStorage] = 1
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintTreatmentAssignment] = 1
    model.scaling_factor[model.NetworkBalance] = 1 / scaling_factor
    model.scaling_factor[model.PipelineCapacity] = 1 / scaling_factor
    model.scaling_factor[model.PipelineCapacityExpansion] = 1 / scaling_factor
    model.scaling_factor[model.PipelineExpansionCapEx] = 1 / scaling_factor
    model.scaling_factor[model.PipingCost] = 1 / scaling_factor
    model.scaling_factor[model.ProductionPadSupplyBalance] = 1 / scaling_factor
    model.scaling_factor[model.ReuseDestinationDeliveries] = 1 / scaling_factor
    model.scaling_factor[model.SlackCosts] = 1 / (scaling_factor**2)
    model.scaling_factor[model.BeneficialReuseDeliveries] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsWaterDeliveries] = 1 / scaling_factor
    model.scaling_factor[model.StorageCapacity] = 1 / scaling_factor
    model.scaling_factor[model.StorageCapacityExpansion] = 1 / scaling_factor
    model.scaling_factor[model.StorageDepositCost] = 1 / scaling_factor
    model.scaling_factor[model.StorageExpansionCapEx] = 1 / scaling_factor
    model.scaling_factor[model.StorageSiteBalance] = 1 / scaling_factor
    model.scaling_factor[model.StorageSiteProcessingCapacity] = 1 / scaling_factor
    model.scaling_factor[model.StorageSiteTruckOffloadingCapacity] = 1 / scaling_factor
    model.scaling_factor[model.StorageWithdrawalCredit] = 1 / scaling_factor
    model.scaling_factor[model.TerminalCompletionsPadStorageLevel] = 1 / scaling_factor
    model.scaling_factor[model.TerminalStorageLevel] = 1 / scaling_factor
    model.scaling_factor[model.TotalCompletionsReuseCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalDisposalCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalDisposalVolume] = 1 / scaling_factor
    model.scaling_factor[model.TotalFreshSourcingCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalFreshSourcingVolume] = 1 / scaling_factor
    model.scaling_factor[model.TotalPipingCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalReuseVolume] = 1 / scaling_factor
    model.scaling_factor[model.TotalStorageCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalStorageWithdrawalCredit] = 1 / scaling_factor
    model.scaling_factor[model.TotalTreatmentCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalTruckingCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalTruckingVolume] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentBalance] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCapacity] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCapacityExpansion] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCost] = 1 / scaling_factor
    model.scaling_factor[model.TruckingCost] = 1 / (scaling_factor * 100)
    model.scaling_factor[model.TreatmentExpansionCapEx] = 1 / scaling_factor

    if model.config.node_capacity == IncludeNodeCapacity.true:
        model.scaling_factor[model.NetworkCapacity] = 1 / scaling_factor

    scaled_model = TransformationFactory("core.scale_model").create_using(model)

    return scaled_model


def _preprocess_data(model):
    """
    This module pre-processess data to fit the optimization format.
    In this module the following data is preprocessed:
    - Pipeline Diameters [diameter] are converted to flow rate model [volume/time]
    - Pipeline Expension Cost is converted to model [currency/volume]
    parameter_list = [list of tabs that contain parameters]
    """
    if model.config.pipeline_capacity == PipelineCapacity.calculated:
        # Pipeline Capacity
        # Pipeline diameter is converted to pipeline capacity (volume/time) using
        # Hazen-Williams equation.
        # (https://en.wikipedia.org/wiki/Hazen%E2%80%93Williams_equation)
        # Required inputs are:
        # - pipeline diameter [inch]
        # - pipe roughness []
        # - max head loss

        # retrieve roughness and max head loss
        roughness = model.df_parameters["Hydraulics"]["roughness"]
        max_head_loss = model.df_parameters["Hydraulics"]["max_head_loss"]

        model.df_parameters["PipelineCapacityIncrements_Calculated"] = {}
        for key in model.df_parameters["PipelineDiameterValues"]:
            diameter_inches = pyunits.convert_value(
                model.df_parameters["PipelineDiameterValues"][key],
                from_units=model.user_units["diameter"],
                to_units=pyunits.inch,
            )
            flow_rate = (
                (1 / 10.67) ** (1 / 1.852)
                * roughness
                * (max_head_loss**0.54)
                * (diameter_inches * 0.0254) ** 2.63
            )

            # convert to volume/time:
            days_in_period = model.decision_period / pyunits.days
            # Make variable unitless
            days_in_period = pyunits.convert(
                days_in_period, to_units=pyunits.days / pyunits.days
            )
            flow_rate *= 6.28981 * (3600 * 24 * days_in_period)

            # add to parameter df.
            model.df_parameters["PipelineCapacityIncrements_Calculated"][
                key
            ] = flow_rate

    # Annualization rate
    # The annualization rate is used using a discount rate and the lifetime
    # expectancy of assets. It's calculated using the formula as described
    # on the following website:
    # http://www.energycommunity.org/webhelppro/Expressions/AnnualizedCost.htm

    discount_rate = model.df_parameters["Economics"]["discount_rate"]
    life = model.df_parameters["Economics"]["CAPEX_lifetime"]

    if life == 0:
        model.df_parameters["AnnualizationRate"] = 1
    elif discount_rate == 0:
        model.df_parameters["AnnualizationRate"] = 1 / life
    else:
        model.df_parameters["AnnualizationRate"] = discount_rate / (
            1 - (1 + discount_rate) ** -life
        )


def solve_model(model, options=None):

    if options is None:
        options = {
            "deactivate_slacks": True,
            "scale_model": True,
            "scaling_factor": 1000000,
            "running_time": 60,
            "gap": 0,
            "water_quality": False,
        }
    # initialize pyomo solver
    opt = get_solver("gurobi_direct", "gurobi", "cbc")
    # Note: if using the small_strategic_case_study and cbc, allow at least 5 minutes
    set_timeout(opt, timeout_s=options["running_time"])
    opt.options["mipgap"] = options["gap"]
    opt.options["NumericFocus"] = 1

    if options["deactivate_slacks"] is True:
        model.v_C_Slack.fix(0)
        model.v_S_FracDemand.fix(0)
        model.v_S_Production.fix(0)
        model.v_S_Flowback.fix(0)
        model.v_S_PipelineCapacity.fix(0)
        model.v_S_StorageCapacity.fix(0)
        model.v_S_DisposalCapacity.fix(0)
        model.v_S_TreatmentCapacity.fix(0)
        model.v_S_ReuseCapacity.fix(0)

    if options["scale_model"] is True:
        # Scale model
        scaled_model = scale_model(model, scaling_factor=options["scaling_factor"])

        # solve mathematical model
        print("\n")
        print("*" * 50)
        print(" " * 15, "Solving scaled model")
        print("*" * 50)
        results = opt.solve(scaled_model, tee=True)
    else:
        # solve mathematical model
        print("\n")
        print("*" * 50)
        print(" " * 15, "Solving model")
        print("*" * 50)
        results = opt.solve(model, tee=True)

    # Check termination condition
    if results.solver.termination_condition != TerminationCondition.infeasible:
        if options["scale_model"] is True:
            TransformationFactory("core.scale_model").propagate_solution(
                scaled_model, model
            )

    else:
        print(
            "WARNING: Model is infeasible. Adding Slack variables to avoid infeasibilities\n, \
            however this is an indication that the input data should be revised"
        )

        if options["scale_model"] is True:
            scaled_model.scaled_v_C_Slack.unfix()
            scaled_model.scaled_v_S_FracDemand.unfix()
            scaled_model.scaled_v_S_Production.unfix()
            scaled_model.scaled_v_S_Flowback.unfix()
            scaled_model.scaled_v_S_PipelineCapacity.unfix()
            scaled_model.scaled_v_S_StorageCapacity.unfix()
            scaled_model.scaled_v_S_DisposalCapacity.unfix()
            scaled_model.scaled_v_S_TreatmentCapacity.unfix()
            scaled_model.scaled_v_S_ReuseCapacity.unfix()

            # solve mathematical model
            print("\n")
            print("*" * 50)
            print(" " * 15, "Solving scaled model")
            print("*" * 50)
            results = opt.solve(scaled_model, tee=True)
            TransformationFactory("core.scale_model").propagate_solution(
                scaled_model, model
            )
        else:

            model.v_C_Slack.unfix()
            model.v_S_FracDemand.unfix()
            model.v_S_Production.unfix()
            model.v_S_Flowback.unfix()
            model.v_S_PipelineCapacity.unfix()
            model.v_S_StorageCapacity.unfix()
            model.v_S_DisposalCapacity.unfix()
            model.v_S_TreatmentCapacity.unfix()
            model.v_S_ReuseCapacity.unfix()

            # solve mathematical model
            print("\n")
            print("*" * 50)
            print(" " * 15, "Solving model")
            print("*" * 50)
            results = opt.solve(model, tee=True)

    if options["water_quality"] is True:
        model = postprocess_water_quality_calculation(model, opt)

    results.write()
    return results
