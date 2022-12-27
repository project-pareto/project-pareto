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

import numpy as np
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
    units as pyunits,
)
from pareto.utilities.get_data import get_data
from importlib import resources
import pyomo.environ
from pyomo.core.base.constraint import simple_constraint_rule
from pyomo.core.expr.current import identify_variables

# import gurobipy
from pyomo.common.config import ConfigBlock, ConfigValue, In, Bool
from enum import Enum

from pareto.utilities.solvers import get_solver


class ProdTank(Enum):
    individual = 0
    equalized = 1


class WaterQuality(Enum):
    false = 0
    post_process = 1
    discrete = 2


# create config dictionary
CONFIG = ConfigBlock()
CONFIG.declare(
    "has_pipeline_constraints",
    ConfigValue(
        default=True,
        domain=Bool,
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
CONFIG.declare(
    "water_quality",
    ConfigValue(
        default=WaterQuality.post_process,
        domain=In(WaterQuality),
        description="Water quality",
        doc="""Selection to include water quality
        ***default*** - WaterQuality.continuous
        **Valid Values:** - {
        **WaterQuality.False** - Exclude water quality from model,
        **WaterQuality.post_process** - Include water quality as post process
        **WaterQuality.discrete** - Include water quality as discrete values in model
        }""",
    ),
)


# return the units container used for strategic model
# this is needed for the testing_strategic_model.py for checking units consistency
def get_operational_model_unit_container():
    return pyunits


def create_model(df_sets, df_parameters, default={}):
    """
    create operational model
    Args: list with sets and parameters
    Return: mathematical model
    """
    model = ConcreteModel()
    # import config dictionary
    model.config = CONFIG(default)
    model.type = "operational"
    model.df_sets = df_sets
    model.df_parameters = df_parameters
    model.proprietary_data = df_parameters["proprietary_data"][0]

    try:
        # Check that currency is set to USD
        print("Setting currency to:", pyunits.USD)
    # Exception if USD is not already set and throws Attribute Error
    except AttributeError:
        # Currency base units are not inherently defined by default
        pyunits.load_definitions_from_strings(["USD = [currency]"])

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

    # Define sets #
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
    model.s_W = Set(
        initialize=df_sets["WaterQualityComponents"], doc="Water Quality Components"
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
    model.s_D = Set(initialize=["D0"], doc="Pipeline diameters")
    model.s_C = Set(initialize=["C0"], doc="Storage capacities")
    model.s_I = Set(initialize=["I0"], doc="Injection (i.e. disposal) capacities")

    # Define continuous variables #
    model.v_Objective = Var(
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
        doc="Water put into completions" " pad storage [volume/time]",
    )
    model.v_F_PadStorageOut = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Water from completions pad storage" " used for fracturing [volume/time]",
    )
    model.v_F_UnusedTreatedWater = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Water leftover from the treatment process [volume/time]",
    )
    if model.config.production_tanks == ProdTank.individual:
        model.v_F_Drain = Var(
            model.s_P,
            model.s_A,
            model.s_T,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water drained from" " production tank [volume/time]",
        )
        model.v_L_ProdTank = Var(
            model.s_P,
            model.s_A,
            model.s_T,
            within=NonNegativeReals,
            units=model.model_units["volume"],
            doc="Water level in production tank [volume]",
        )
    elif model.config.production_tanks == ProdTank.equalized:
        model.v_F_Drain = Var(
            model.s_P,
            model.s_T,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water drained from" " production tank [volume/time]",
        )
        model.v_L_ProdTank = Var(
            model.s_P,
            model.s_T,
            within=NonNegativeReals,
            units=model.model_units["volume"],
            doc="Water level in production tank [volume]",
        )
    else:
        raise Exception("storage type not supported")
    model.v_L_PadStorage = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume"],
        doc="Water level in completions pad storage [volume]",
    )
    model.v_B_Production = Var(
        model.s_P,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Produced water for transport from pad [volume/time]",
    )
    model.v_L_Storage = Var(
        model.s_S,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Water level at storage site [volume]",
    )
    model.v_C_Piped = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of piping produced water from location l to location l [currency/time]",
    )
    model.v_C_Trucked = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of trucking produced water from location l to location l [currency/time]",
    )
    model.v_C_Sourced = Var(
        model.s_F,
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of sourcing fresh water from source f to completion pad p [currency/time]",
    )
    model.v_C_Disposal = Var(
        model.s_K,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of injecting produced water at disposal site [currency/time]",
    )
    model.v_C_Treatment = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of treating produced water at treatment site [currency/time]",
    )
    model.v_C_Reuse = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of reusing produced water at completions site [currency/time]",
    )
    model.v_C_Storage = Var(
        model.s_S,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of storing produced water at storage site [currency/time]",
    )
    model.v_C_PadStorage = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Cost of storing produced water at completions pad storage [currency]",
    )
    model.v_R_Storage = Var(
        model.s_S,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency_volume"],
        doc="Credit for retrieving stored produced water from storage site [currency/volume]",
    )
    model.v_F_TotalSourced = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume freshwater sourced [volume]",
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
    model.v_C_TotalPadStorage = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of storing produced water at completions site [currency]",
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
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to completions pad [volume/time]",
    )
    model.v_F_DisposalDestination = Var(
        model.s_K,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to disposal site [volume/time]",
    )
    model.v_F_TreatmentDestination = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to treatment site [volume/time]",
    )
    model.v_F_BeneficialReuseDestination = Var(
        model.s_O,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to Beneficial Reuse Site [volume/time]",
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
    model.v_F_Capacity = Var(
        model.s_L,
        model.s_L,
        within=NonNegativeReals,
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
    model.v_S_FracDemand = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Slack variable to meet the completions demand [volume/time]",
    )
    model.v_S_Production = Var(
        model.s_PP,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Slack variable to process the produced water production [volume/time]",
    )
    model.v_S_Flowback = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Slack variable to process flowback water production [volume/time]",
    )
    model.v_S_PipelineCapacity = Var(
        model.s_L,
        model.s_L,
        within=NonNegativeReals,
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
    # Define binary variables #
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
    model.vb_z_PadStorage = Var(
        model.s_CP, model.s_T, within=Binary, doc="Completions pad storage use"
    )
    model.vb_y_Truck = Var(
        model.s_L,
        model.s_L,
        model.s_T,
        within=Binary,
        doc="Trucking between two locations",
    )

    # Define model parameters #
    model.p_PCA = Param(
        model.s_PP,
        model.s_CP,
        default=0,
        initialize={},
        doc="Valid production-to-completions pipeline arcs [-]",
    )
    model.p_PNA = Param(
        model.s_PP,
        model.s_N,
        default=0,
        initialize={},
        doc="Valid production-to-node pipeline arcs [-]",
    )
    model.p_PPA = Param(
        model.s_PP,
        model.s_PP,
        default=0,
        initialize={},
        doc="Valid production-to-production pipeline arcs [-]",
    )
    model.p_CNA = Param(
        model.s_CP,
        model.s_N,
        default=0,
        initialize={},
        doc="Valid completion-to-node pipeline arcs [-]",
    )
    model.p_CCA = Param(
        model.s_CP,
        model.s_CP,
        default=0,
        initialize={},
        doc="Valid completion-to-completion pipeline arcs [-]",
    )
    model.p_NNA = Param(
        model.s_N,
        model.s_N,
        default=0,
        initialize={},
        doc="Valid node-to-node pipeline arcs [-]",
    )
    model.p_NCA = Param(
        model.s_N,
        model.s_CP,
        default=0,
        initialize={},
        doc="Valid node-to-completions pipeline arcs [-]",
    )
    model.p_NKA = Param(
        model.s_N,
        model.s_K,
        default=0,
        initialize={},
        doc="Valid node-to-disposal pipeline arcs [-]",
    )
    model.p_NSA = Param(
        model.s_N,
        model.s_S,
        default=0,
        initialize={},
        doc="Valid node-to-storage pipeline arcs [-]",
    )
    model.p_NRA = Param(
        model.s_N,
        model.s_R,
        default=0,
        initialize={},
        doc="Valid node-to-treatment pipeline arcs [-]",
    )
    model.p_NOA = Param(
        model.s_N,
        model.s_O,
        default=0,
        initialize={},
        doc="Valid node-to-reuse pipeline arcs [-]",
    )
    model.p_RCA = Param(
        model.s_R,
        model.s_CP,
        default=0,
        initialize=df_parameters["RCA"],
        doc="Valid treatment-to-completions pipeline arcs [-]",
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
        initialize={},
        doc="Valid treatment-to-node pipeline arcs [-]",
    )
    model.p_RKA = Param(
        model.s_R,
        model.s_K,
        default=0,
        initialize={},
        doc="Valid treatment-to-disposal pipeline arcs [-]",
    )
    model.p_SNA = Param(
        model.s_S,
        model.s_N,
        default=0,
        initialize={},
        doc="Valid storage-to-node pipeline arcs [-]",
    )
    model.p_SCA = Param(
        model.s_S,
        model.s_CP,
        default=0,
        initialize={},
        doc="Valid storage-to-completions pipeline arcs [-]",
    )
    model.p_SKA = Param(
        model.s_S,
        model.s_K,
        default=0,
        initialize={},
        doc="Valid storage-to-disposal pipeline arcs [-]",
    )
    model.p_SRA = Param(
        model.s_S,
        model.s_R,
        default=0,
        initialize={},
        doc="Valid storage-to-treatment pipeline arcs [-]",
    )
    model.p_SOA = Param(
        model.s_S,
        model.s_O,
        default=0,
        initialize={},
        doc="Valid storage-to-reuse pipeline arcs [-]",
    )
    df_parameters["LLP"] = {
        **df_parameters["RCA"],
        **df_parameters["FCA"],
    }
    model.p_LLP = Param(
        model.s_L,
        model.s_L,
        default=0,
        initialize=df_parameters["LLP"],
        doc="Valid location-to-location piping arcs [-]",
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
        initialize={},
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
        initialize={},
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
        initialize={},
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
        initialize={},
        doc="Valid storage-to-completions trucking arcs [-]",
    )
    model.p_SKT = Param(
        model.s_S,
        model.s_K,
        default=0,
        initialize={},
        doc="Valid storage-to-disposal trucking arcs [-]",
    )
    model.p_RKT = Param(
        model.s_R,
        model.s_K,
        default=0,
        initialize={},
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

    model.s_LLT = Set(
        initialize=list(df_parameters["LLT"].keys()),
        doc="Location-to-location piping arcs",
    )
    model.s_LLP = Set(
        initialize=list(df_parameters["LLP"].keys()),
        doc="Location-to-location trucking arcs",
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

    # TODO: For EXISTING/INITAL pipeline capacity (l,l_tilde)=(l_tilde=l); needs implemented!
    PipelineCapacityIncrementsTable = {("D0"): 0}

    DisposalCapacityIncrementsTable = {("I0"): 0}

    StorageDisposalCapacityIncrementsTable = {("C0"): 0}

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
    if model.config.production_tanks == ProdTank.individual:
        model.p_beta_Production = Param(
            model.s_P,
            model.s_A,
            model.s_T,
            default=0,
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["volume_time"],
                    to_units=model.model_units["volume_time"],
                )
                for key, value in model.df_parameters["ProductionRates"].items()
            },
            units=model.model_units["volume_time"],
            doc="Produced water supply forecast [volume/time]",
        )
        model.p_sigma_ProdTank = Param(
            model.s_P,
            model.s_A,
            default=pyunits.convert_value(
                500,
                from_units=pyunits.oil_bbl,
                to_units=model.model_units["volume"],
            ),
            units=model.model_units["volume"],
            doc="Production tank capacity [volume]",
        )
        model.p_lambda_ProdTank = Param(
            model.s_P,
            model.s_A,
            default=0,
            initialize={},
            units=model.model_units["volume"],
            doc="Initial water level in " "production tank [volume]",
        )
    elif model.config.production_tanks == ProdTank.equalized:
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
        model.p_sigma_ProdTank = Param(
            model.s_P,
            default=pyunits.convert_value(
                500,
                from_units=pyunits.oil_bbl,
                to_units=model.model_units["volume"],
            ),
            units=model.model_units["volume"],
            initialize=df_parameters["ProductionTankCapacity"],
            doc="Combined capacity equalized " "production tanks [volume]",
        )
        model.p_lambda_ProdTank = Param(
            model.s_P,
            default=0,
            initialize={},
            units=model.model_units["volume"],
            doc="Initial water level in " "equalized production tanks [volume]",
        )
    else:
        raise Exception("storage type not supported")

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
        doc="Flowback supply forecast for a completions pad [volume/time]",
    )
    model.p_sigma_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=0,
        initialize={},
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
            for key, value in model.df_parameters["DisposalCapacity"].items()
        },
        units=model.model_units["volume_time"],
        doc="Initial disposal capacity at disposal sites [volume/time]",
    )
    model.p_sigma_Storage = Param(
        model.s_S,
        default=0,
        initialize={},
        units=model.model_units["volume"],
        doc="Initial storage capacity at storage site [volume]",
    )
    model.p_sigma_PadStorage = Param(
        model.s_CP,
        model.s_T,
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
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["TreatmentCapacity"].items()
        },
        units=model.model_units["volume_time"],
        doc="Initial treatment capacity at treatment site [volume/time]",
    )
    model.p_sigma_Reuse = Param(
        model.s_O,
        default=0,
        initialize={},
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
        initialize={},
        units=model.model_units["volume_time"],
        doc="Truck offloading capacity per pad [volume/time]",
        mutable=True,
    )
    model.p_sigma_MinTruckFlow = Param(
        default=0,
        initialize=pyunits.convert_value(
            model.df_parameters["MinTruckFlow"],
            from_units=model.user_units["volume_time"],
            to_units=model.model_units["volume_time"],
        ),
        units=model.model_units["volume_time"],
        doc="Minimum truck capacity [volume_time]",
    )
    model.p_sigma_MaxTruckFlow = Param(
        default=0,
        initialize=pyunits.convert_value(
            model.df_parameters["MaxTruckFlow"],
            from_units=model.user_units["volume_time"],
            to_units=model.model_units["volume_time"],
        ),
        units=model.model_units["volume_time"],
        doc="Maximum truck capacity [volume_time]",
    )
    model.p_sigma_ProcessingPad = Param(
        model.s_P,
        default=9999999,
        initialize={},
        units=model.model_units["volume_time"],
        doc="Processing (e.g. clarification) capacity per pad [volume/time]",
        mutable=True,
    )
    model.p_sigma_ProcessingStorage = Param(
        model.s_S,
        default=9999999,
        initialize={},
        units=model.model_units["volume_time"],
        doc="Processing (e.g. clarification) capacity per storage site [volume/time]",
        mutable=True,
    )
    model.p_epsilon_Treatment = Param(
        model.s_R,
        model.s_W,
        default=1.0,
        initialize=df_parameters["TreatmentEfficiency"],
        doc="Treatment efficiency [%]",
    )
    # COMMENT: Remove pipeline/disposal/storage capacity expansion increment parameters
    model.p_delta_Pipeline = Param(
        model.s_D,
        default=pyunits.convert_value(
            10000,
            from_units=pyunits.oil_bbl / pyunits.day,
            to_units=model.model_units["volume_time"],
        ),
        initialize=PipelineCapacityIncrementsTable,
        units=model.model_units["volume_time"],
        doc="Pipeline capacity installation/expansion increments [volume/time]",
    )
    model.p_delta_Disposal = Param(
        model.s_I,
        default=pyunits.convert_value(
            10000,
            from_units=pyunits.oil_bbl / pyunits.day,
            to_units=model.model_units["volume_time"],
        ),
        initialize=DisposalCapacityIncrementsTable,
        units=model.model_units["volume_time"],
        doc="Disposal capacity installation/expansion increments [volume/time]",
    )
    model.p_delta_Storage = Param(
        model.s_C,
        default=pyunits.convert_value(
            10000,
            from_units=pyunits.oil_bbl,
            to_units=model.model_units["volume"],
        ),
        initialize=StorageDisposalCapacityIncrementsTable,
        units=model.model_units["volume"],
        doc="Storage capacity installation/expansion increments [volume]",
    )
    model.p_delta_Truck = Param(
        default=pyunits.convert_value(
            110, from_units=pyunits.oil_bbl, to_units=model.model_units["volume"]
        ),
        units=model.model_units["volume"],
        doc="Truck capacity [volume]",
    )
    # COMMENT: Remove disposal/storage/pipeline lead time parameters
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
    model.p_theta_PadStorage = Param(
        model.s_CP,
        default=0,
        units=model.model_units["volume"],
        doc="Terminal storage level at completions site [volume]",
    )
    model.p_lambda_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=9999,
        units=model.model_units["distance"],
        doc="Pipeline segment length [distance]",
    )
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
            for key, value in {}
        },
        units=model.model_units["currency_volume"],
        doc="Storage deposit operational cost [currency/volume]",
    )
    model.p_pi_PadStorage = Param(
        model.s_CP,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency"],
                to_units=model.model_units["currency"],
            )
            for key, value in model.df_parameters["PadStorageCost"].items()
        },
        units=model.model_units["currency"],
        doc="Completions pad storage operational cost if used [currency]",
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
            for key, value in {}
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
    # COMMENT: For this parameter (p_pi_trucking) only currency units are defined, as the hourly rate is canceled out with the
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
    # Define objective function #
    def ObjectiveFunctionRule(model):
        return model.v_Objective == (
            model.v_C_TotalSourced
            + model.v_C_TotalDisposal
            + model.v_C_TotalTreatment
            + model.v_C_TotalReuse
            + model.v_C_TotalPiping
            + model.v_C_TotalStorage
            + model.v_C_TotalPadStorage
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

    # Define constraints #
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
            + sum(model.v_F_Piped[r, p, t] for r in model.s_R if model.p_RCA[r, p])
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

    def CompletionsPadStorageCapacityRule(model, p, t):
        return (
            model.v_L_PadStorage[p, t]
            <= model.vb_z_PadStorage[p, t] * model.p_sigma_PadStorage[p, t]
        )

    model.CompletionsPadStorageCapacity = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadStorageCapacityRule,
        doc="Completions pad storage capacity",
    )

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

    def NetworkNodeBalanceRule(model, n, t):
        return sum(
            model.v_F_Piped[p, n, t] for p in model.s_PP if model.p_PNA[p, n]
        ) + sum(
            model.v_F_Piped[p, n, t] for p in model.s_CP if model.p_CNA[p, n]
        ) + sum(
            model.v_F_Piped[s, n, t] for s in model.s_S if model.p_SNA[s, n]
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

    def StorageCapacityRule(model, s, t):
        return model.v_L_Storage[s, t] <= model.v_X_Capacity[s]

    model.StorageCapacity = Constraint(
        model.s_S, model.s_T, rule=StorageCapacityRule, doc="Storage capacity"
    )

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

    def TreatmentBalanceRule(model, r, t):
        return (
            model.p_epsilon_Treatment[r, "TDS"]
            * (
                sum(model.v_F_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r])
                + sum(model.v_F_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r])
                + sum(
                    model.v_F_Trucked[p, r, t] for p in model.s_PP if model.p_PRT[p, r]
                )
                + sum(
                    model.v_F_Trucked[p, r, t] for p in model.s_CP if model.p_CRT[p, r]
                )
            )
            == sum(model.v_F_Piped[r, p, t] for p in model.s_CP if model.p_RCA[r, p])
            + model.v_F_UnusedTreatedWater[r, t]
        )

    model.TreatmentBalance = Constraint(
        model.s_R,
        model.s_T,
        rule=simple_constraint_rule(TreatmentBalanceRule),
        doc="Treatment balance",
    )

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

    def TotalFreshSourcingCostRule(model):
        return model.v_C_TotalSourced == sum(
            sum(sum(model.v_C_Sourced[f, p, t] for f in model.s_F) for p in model.s_CP)
            for t in model.s_T
        )

    model.TotalFreshSourcingCost = Constraint(
        rule=TotalFreshSourcingCostRule, doc="Total fresh sourcing cost"
    )

    def TotalFreshSourcingVolumeRule(model):
        return model.v_F_TotalSourced == sum(
            sum(
                sum(model.v_F_Sourced[f, p, t] for f in model.s_F if model.p_FCA[f, p])
                for p in model.s_CP
            )
            for t in model.s_T
        ) + sum(
            sum(
                sum(model.v_F_Trucked[f, p, t] for f in model.s_F if model.p_FCT[f, p])
                for p in model.s_CP
            )
            for t in model.s_T
        )

    model.TotalFreshSourcingVolume = Constraint(
        rule=TotalFreshSourcingVolumeRule, doc="Total fresh sourcing volume"
    )

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

    def TotalDisposalCostRule(model):
        return model.v_C_TotalDisposal == sum(
            sum(model.v_C_Disposal[k, t] for k in model.s_K) for t in model.s_T
        )

    model.TotalDisposalCost = Constraint(
        rule=TotalDisposalCostRule, doc="Total disposal cost"
    )

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

    def TotalTreatmentCostRule(model):
        return model.v_C_TotalTreatment == sum(
            sum(model.v_C_Treatment[r, t] for r in model.s_R) for t in model.s_T
        )

    model.TotalTreatmentCost = Constraint(
        rule=TotalTreatmentCostRule, doc="Total treatment cost"
    )

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
                + sum(model.v_F_Piped[r, p, t] for r in model.s_R if model.p_RCA[r, p])
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

    def TotalCompletionsReuseCostRule(model):
        return model.v_C_TotalReuse == sum(
            sum(model.v_C_Reuse[p, t] for p in model.s_CP) for t in model.s_T
        )

    model.TotalCompletionsReuseCost = Constraint(
        rule=TotalCompletionsReuseCostRule, doc="Total completions reuse cost"
    )

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

    def StorageDepositCostRule(model, s, t):
        return model.v_C_Storage[s, t] == (
            (
                sum(model.v_F_Piped[n, s, t] for n in model.s_N if model.p_NSA[n, s])
                + sum(
                    model.v_F_Trucked[p, s, t] for p in model.s_PP if model.p_PST[p, s]
                )
                + sum(
                    model.v_F_Trucked[p, s, t] for p in model.s_CP if model.p_CST[p, s]
                )
            )
            * model.p_pi_Storage[s]
        )

    model.StorageDepositCost = Constraint(
        model.s_S, model.s_T, rule=StorageDepositCostRule, doc="Storage deposit cost"
    )

    def TotalStorageCostRule(model):
        return model.v_C_TotalStorage == sum(
            sum(model.v_C_Storage[s, t] for s in model.s_S) for t in model.s_T
        )

    model.TotalStorageCost = Constraint(
        rule=TotalStorageCostRule, doc="Total storage deposit cost"
    )

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

    def TotalStorageWithdrawalCreditRule(model):
        return model.v_R_TotalStorage == sum(
            sum(model.v_R_Storage[s, t] for s in model.s_S) for t in model.s_T
        )

    model.TotalStorageWithdrawalCredit = Constraint(
        rule=TotalStorageWithdrawalCreditRule, doc="Total storage withdrawal credit"
    )

    def PadStorageCostRule(model, p, t):
        return (
            model.v_C_PadStorage[p, t]
            == model.vb_z_PadStorage[p, t] * model.p_pi_PadStorage[p, t]
        )

    model.PadStorageCost = Constraint(
        model.s_CP,
        model.s_T,
        rule=PadStorageCostRule,
        doc="Completions pad storage cost",
    )

    def TotalPadStorageCostRule(model):
        return model.v_C_TotalPadStorage == sum(
            sum(model.v_C_PadStorage[p, t] for p in model.s_CP) for t in model.s_T
        )

    model.TotalPadStorageCost = Constraint(
        rule=TotalPadStorageCostRule, doc="Total completions pad storage cost"
    )

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
                    * model.p_psi_PipelineCapacity
                    for p in model.s_PP
                    if model.p_PCA[p, p_tilde]
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

    model.SlackCosts = Constraint(rule=SlackCostsRule, doc="Slack costs")

    def ReuseDestinationDeliveriesRule(model, p, t):
        return model.v_F_ReuseDestination[p, t] == sum(
            model.v_F_Piped[n, p, t] for n in model.s_N if model.p_NCA[n, p]
        ) + sum(
            model.v_F_Piped[p_tilde, p, t]
            for p_tilde in model.s_PP
            if model.p_PCA[p_tilde, p]
        ) + sum(
            model.v_F_Piped[r, p, t] for r in model.s_R if model.p_RCA[r, p]
        ) + sum(
            model.v_F_Piped[s, p, t] for s in model.s_S if model.p_SCA[s, p]
        ) + sum(
            model.v_F_Piped[p_tilde, p, t]
            for p_tilde in model.s_CP
            if model.p_CCA[p_tilde, p]
        ) + sum(
            model.v_F_Trucked[p_tilde, p, t]
            for p_tilde in model.s_CP
            if model.p_CCT[p_tilde, p]
        ) + sum(
            model.v_F_Trucked[p_tilde, p, t]
            for p_tilde in model.s_PP
            if model.p_PCT[p_tilde, p]
        ) + sum(
            model.v_F_Trucked[s, p, t] for s in model.s_S if model.p_SCT[s, p]
        )

    model.ReuseDestinationDeliveries = Constraint(
        model.s_CP,
        model.s_T,
        rule=ReuseDestinationDeliveriesRule,
        doc="Reuse destinations volume",
    )

    def DisposalDestinationDeliveriesRule(model, k, t):
        return model.v_F_DisposalDestination[k, t] == sum(
            model.v_F_Piped[n, k, t] for n in model.s_N if model.p_NKA[n, k]
        ) + sum(model.v_F_Piped[s, k, t] for s in model.s_S if model.p_SKA[s, k]) + sum(
            model.v_F_Piped[r, k, t] for r in model.s_R if model.p_RKA[r, k]
        ) + sum(
            model.v_F_Trucked[s, k, t] for s in model.s_S if model.p_SKT[s, k]
        ) + sum(
            model.v_F_Trucked[p, k, t] for p in model.s_PP if model.p_PKT[p, k]
        ) + sum(
            model.v_F_Trucked[p, k, t] for p in model.s_CP if model.p_CKT[p, k]
        ) + sum(
            model.v_F_Trucked[r, k, t] for r in model.s_R if model.p_RKT[r, k]
        )

    model.DisposalDestinationDeliveries = Constraint(
        model.s_K,
        model.s_T,
        rule=DisposalDestinationDeliveriesRule,
        doc="Disposal destinations volume",
    )

    def TreatmentDestinationDeliveriesRule(model, r, t):
        return model.v_F_TreatmentDestination[r, t] == sum(
            model.v_F_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r]
        ) + sum(model.v_F_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r]) + sum(
            model.v_F_Trucked[p, r, t] for p in model.s_PP if model.p_PRT[p, r]
        ) + sum(
            model.v_F_Trucked[s, r, t] for s in model.s_CP if model.p_CRT[s, r]
        )

    model.TreatmentDestinationDeliveries = Constraint(
        model.s_R,
        model.s_T,
        rule=TreatmentDestinationDeliveriesRule,
        doc="Treatment destinations volume",
    )

    def BeneficialReuseDeliveriesRule(model, o, t):
        return model.v_F_BeneficialReuseDestination[o, t] == sum(
            model.v_F_Piped[n, o, t] for n in model.s_N if model.p_NOA[n, o]
        ) + sum(model.v_F_Piped[s, o, t] for s in model.s_S if model.p_SOA[s, o]) + sum(
            model.v_F_Trucked[p, o, t] for p in model.s_PP if model.p_POT[p, o]
        )

    model.BeneficialReuseDeliveries = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseDeliveriesRule,
        doc="Beneficial reuse destinations volume",
    )

    # Define Objective and Solve Statement #

    model.objective = Objective(
        expr=model.v_Objective, sense=minimize, doc="Objective function"
    )

    if model.config.water_quality is WaterQuality.discrete:
        model = water_quality_discrete(model, df_parameters, df_sets)

    return model


def water_quality(model, df_sets, df_parameters):
    # Introduce parameter nu for water quality at each pad
    model.p_nu = Param(
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
        doc="Water Quality at pad [mg/L]",
    )

    model.p_xi = Param(
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
        doc="Initial Water Quality at storage site [mg/L]",
    )
    # Introduce variable Q to track water quality at each location over time
    model.v_Q = Var(
        model.s_L,
        model.s_W,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["concentration"],
        doc="Water quality at location [mg/L]",
    )

    # Material Balance
    def DisposalWaterQualityRule(model, k, w, t):
        return (
            sum(
                model.v_F_Piped[n, k, t] * model.v_Q[n, w, t]
                for n in model.s_N
                if model.p_NKA[n, k]
            )
            + sum(
                model.v_F_Piped[s, k, t] * model.v_Q[s, w, t]
                for s in model.s_S
                if model.p_SKA[s, k]
            )
            + sum(
                model.v_F_Piped[r, k, t] * model.v_Q[r, w, t]
                for r in model.s_R
                if model.p_RKA[r, k]
            )
            + sum(
                model.v_F_Trucked[s, k, t] * model.v_Q[s, w, t]
                for s in model.s_S
                if model.p_SKT[s, k]
            )
            + sum(
                model.v_F_Trucked[p, k, t] * model.v_Q[p, w, t]
                for p in model.s_PP
                if model.p_PKT[p, k]
            )
            + sum(
                model.v_F_Trucked[p, k, t] * model.v_Q[p, w, t]
                for p in model.s_CP
                if model.p_CKT[p, k]
            )
            + sum(
                model.v_F_Trucked[r, k, t] * model.v_Q[r, w, t]
                for r in model.s_R
                if model.p_RKT[r, k]
            )
            == model.v_Q[k, w, t] * model.v_F_DisposalDestination[k, t]
        )

    model.DisposalWaterQuality = Constraint(
        model.s_K,
        model.s_W,
        model.s_T,
        rule=DisposalWaterQualityRule,
        doc="Disposal water quality rule",
    )

    def StorageSiteWaterQualityRule(model, s, w, t):
        if t == model.s_T.first():
            return model.p_lambda_Storage[s] * model.p_xi[s, w] + sum(
                model.v_F_Piped[n, s, t] * model.v_Q[n, w, t]
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * model.v_Q[p, w, t]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * model.v_Q[p, w, t]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) == model.v_Q[
                s, w, t
            ] * (
                model.v_L_Storage[s, t]
                + sum(model.v_F_Piped[s, n, t] for n in model.s_N if model.p_SNA[s, n])
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
        else:
            return model.v_L_Storage[s, model.s_T.prev(t)] * model.v_Q[
                s, w, model.s_T.prev(t)
            ] + sum(
                model.v_F_Piped[n, s, t] * model.v_Q[n, w, t]
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * model.v_Q[p, w, t]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * model.v_Q[p, w, t]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) == model.v_Q[
                s, w, t
            ] * (
                model.v_L_Storage[s, t]
                + sum(model.v_F_Piped[s, n, t] for n in model.s_N if model.p_SNA[s, n])
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

    model.StorageSiteWaterQuality = Constraint(
        model.s_S,
        model.s_W,
        model.s_T,
        rule=StorageSiteWaterQualityRule,
        doc="Storage site water quality rule",
    )
    # Treatment Facility
    def TreatmentWaterQualityRule(model, r, w, t):
        return model.p_epsilon_Treatment[r, w] * (
            sum(
                model.v_F_Piped[n, r, t] * model.v_Q[n, w, t]
                for n in model.s_N
                if model.p_NRA[n, r]
            )
            + sum(
                model.v_F_Piped[s, r, t] * model.v_Q[s, w, t]
                for s in model.s_S
                if model.p_SRA[s, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * model.v_Q[p, w, t]
                for p in model.s_PP
                if model.p_PRT[p, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * model.v_Q[p, w, t]
                for p in model.s_CP
                if model.p_CRT[p, r]
            )
        ) == model.v_Q[r, w, t] * (
            sum(model.v_F_Piped[r, p, t] for p in model.s_CP if model.p_RCA[r, p])
            + model.v_F_UnusedTreatedWater[r, t]
        )

    model.TreatmentWaterQuality = Constraint(
        model.s_R,
        model.s_W,
        model.s_T,
        rule=simple_constraint_rule(TreatmentWaterQualityRule),
        doc="Treatment water quality",
    )

    def NetworkNodeWaterQualityRule(model, n, w, t):
        return sum(
            model.v_F_Piped[p, n, t] * model.v_Q[p, w, t]
            for p in model.s_PP
            if model.p_PNA[p, n]
        ) + sum(
            model.v_F_Piped[p, n, t] * model.v_Q[p, w, t]
            for p in model.s_CP
            if model.p_CNA[p, n]
        ) + sum(
            model.v_F_Piped[s, n, t] * model.v_Q[s, w, t]
            for s in model.s_S
            if model.p_SNA[s, n]
        ) + sum(
            model.v_F_Piped[n_tilde, n, t] * model.v_Q[n_tilde, w, t]
            for n_tilde in model.s_N
            if model.p_NNA[n_tilde, n]
        ) == model.v_Q[
            n, w, t
        ] * (
            sum(
                model.v_F_Piped[n, n_tilde, t]
                for n_tilde in model.s_N
                if model.p_NNA[n, n_tilde]
            )
            + sum(model.v_F_Piped[n, p, t] for p in model.s_CP if model.p_NCA[n, p])
            + sum(model.v_F_Piped[n, k, t] for k in model.s_K if model.p_NKA[n, k])
            + sum(model.v_F_Piped[n, r, t] for r in model.s_R if model.p_NRA[n, r])
            + sum(model.v_F_Piped[n, s, t] for s in model.s_S if model.p_NSA[n, s])
            + sum(model.v_F_Piped[n, o, t] for o in model.s_O if model.p_NOA[n, o])
        )

    model.NetworkWaterQuality = Constraint(
        model.s_N,
        model.s_W,
        model.s_T,
        rule=NetworkNodeWaterQualityRule,
        doc="Network water quality",
    )

    def BeneficialReuseWaterQuality(model, o, w, t):
        return (
            sum(
                model.v_F_Piped[n, o, t] * model.v_Q[n, w, t]
                for n in model.s_N
                if model.p_NOA[n, o]
            )
            + sum(
                model.v_F_Piped[s, o, t] * model.v_Q[s, w, t]
                for s in model.s_S
                if model.p_SOA[s, o]
            )
            + sum(
                model.v_F_Trucked[p, o, t] * model.v_Q[p, w, t]
                for p in model.s_PP
                if model.p_POT[p, o]
            )
            == model.v_Q[o, w, t] * model.v_F_BeneficialReuseDestination[o, t]
        )

    model.BeneficialReuseWaterQuality = Constraint(
        model.s_O,
        model.s_W,
        model.s_T,
        rule=BeneficialReuseWaterQuality,
        doc="Beneficial reuse capacity",
    )

    # Fix variables
    # Fix variables: produced water flows, binary
    model.v_F_Piped.fix()
    model.v_F_Trucked.fix()
    model.v_F_Sourced.fix()
    model.v_F_PadStorageIn.fix()
    model.v_F_PadStorageOut.fix()
    model.v_L_Storage.fix()
    model.v_F_UnusedTreatedWater.fix()
    model.v_F_DisposalDestination.fix()
    model.v_F_BeneficialReuseDestination.fix()

    # Use p_nu to fix v_Q for pads
    for p in model.s_P:
        for w in model.s_W:
            for t in model.s_T:
                model.v_Q[p, w, t].fix(model.p_nu[p, w])

    return model


def postprocess_water_quality_calculation(model, df_sets, df_parameters, opt):
    # Add water quality formulation to input solved model
    water_quality_model = water_quality(model, df_sets, df_parameters)
    # Calculate water quality
    opt.solve(water_quality_model, tee=True)

    return water_quality_model


def discretize_water_quality(df_parameters, df_sets, discrete_qualities) -> dict:
    discrete_quality = dict()

    for quality_component in df_sets["WaterQualityComponents"]:
        # Find the minimum and maximum quality for the quality component
        qualities_for_component_for_pad = [
            value
            for key, value in df_parameters["PadWaterQuality"].items()
            if key[1] == quality_component
        ]
        qualities_for_component_for_storage = [
            value
            for key, value in df_parameters["StorageInitialWaterQuality"].items()
            if key[1] == quality_component
        ]
        qualities_for_component = (
            qualities_for_component_for_pad + qualities_for_component_for_storage
        )
        min_quality = min(qualities_for_component)
        max_quality = max(qualities_for_component)
        # Discretize linear between the min and max quality based on the number of discrete qualities.
        for i, value in enumerate(
            np.linspace(min_quality, max_quality, len(discrete_qualities))
        ):
            discrete_quality[(quality_component, discrete_qualities[i])] = value
    return discrete_quality


def discrete_water_quality_list(steps=6) -> list:
    discrete_qualities = []
    # Create list ["Q0", "Q1", ... , "QN"] qualities based on the number of steps.
    for i in range(0, steps):
        discrete_qualities.append("Q{0}".format(i))
    return discrete_qualities


def water_quality_discrete(model, df_parameters, df_sets):
    # region Add sets, parameters and constraints

    # Quality at pad
    model.p_nu_pad = Param(
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
        doc="Water Quality at pad [mg/L]",
    )
    # Quality of Sourced Water
    model.p_nu_freshwater = Param(
        model.s_F,
        model.s_W,
        default=0,
        initialize=pyunits.convert_value(
            0,
            from_units=model.user_units["concentration"],
            to_units=model.model_units["concentration"],
        ),
        units=model.model_units["concentration"],
        doc="Water Quality of freshwater [mg/L]",
    )

    StorageInitialWaterQuality_convert_to_model = {
        key: pyunits.convert_value(
            value,
            from_units=model.user_units["concentration"],
            to_units=model.model_units["concentration"],
        )
        for key, value in model.df_parameters["StorageInitialWaterQuality"].items()
        if value
    }
    # Initial water quality at storage site
    model.p_xi_StorageSite = Param(
        model.s_S,
        model.s_W,
        default=max(StorageInitialWaterQuality_convert_to_model.values()) * 100
        if StorageInitialWaterQuality_convert_to_model
        else pyunits.convert_value(
            0,
            from_units=model.user_units["concentration"],
            to_units=model.model_units["concentration"],
        ),
        initialize=StorageInitialWaterQuality_convert_to_model,
        units=model.model_units["concentration"],
        doc="Initial Water Quality at storage site [mg/L]",
    )

    # region discretization

    # Create list of discretized qualities
    discrete_quality_list = discrete_water_quality_list(6)

    # Create set with the list of discretized qualities
    model.s_Q = Set(initialize=discrete_quality_list, doc="Discrete water qualities")

    # Initialize values for each discrete quality
    model.p_discrete_quality = Param(
        model.s_W,
        model.s_Q,
        initialize=discretize_water_quality(
            df_parameters, df_sets, discrete_quality_list
        ),
        units=model.model_units["concentration"],
        doc="Discretization of water components",
    )

    # For the discretization we need a upperbound for the maximum number of trucks for each truck flow
    model.p_max_number_of_trucks = Param(
        initialize=100,
        doc="Max number of trucks. Needed for upperbound on v_F_Trucked",
    )

    # Create sets for location to location arcs where the quality for the from location is variable.
    # This excludes the production pads and fresh water sources because the quality is known.
    model.s_NonPLP = Set(
        initialize=[
            NonFromPPipelines
            for NonFromPPipelines in model.s_LLP
            if not NonFromPPipelines[0] in (model.s_P | model.s_F)
        ],
        doc="location-to-location with discrete quality piping arcs",
    )
    model.s_NonPLT = Set(
        initialize=[
            NonFromPTrucks
            for NonFromPTrucks in model.s_LLT
            if not NonFromPTrucks[0] in (model.s_P | model.s_F)
        ],
        doc="location-to-location with discrete quality trucking arcs",
    )

    # All locations where the quality is variable. This excludes the production pads and fresh water sources
    model.s_QL = Set(
        initialize=(model.s_K | model.s_S | model.s_R | model.s_O | model.s_N),
        doc="Locations with discrete quality",
    )

    def SetZToMax(model, l, t, w, q):
        # Set initial value for discrete quality to max value. This is for setting initial solution.
        if q == discrete_quality_list[-1]:
            return 1
        return 0

    model.v_DQ = Var(
        model.s_QL,
        model.s_T,
        model.s_W,
        model.s_Q,
        within=Binary,
        initialize=SetZToMax,
        doc="Discrete quality at location ql at time t for component w",
    )

    model.OnlyOneDiscreteQualityPerLocation = Constraint(
        model.s_QL,
        model.s_T,
        model.s_W,
        rule=lambda model, l, t, w: sum(model.v_DQ[l, t, w, q] for q in model.s_Q) == 1,
        doc="Only one discrete quality can be chosen",
    )

    def DiscretizePipeFlowQuality(model):
        model.v_F_DiscretePiped = Var(
            model.s_NonPLP,
            model.s_T,
            model.s_W,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            initialize=0,
            doc="Produced water quantity piped from location l to location l for each quality component w and discretized quality q [volume/time]",
        )

        model.DiscreteMaxPipeFlow = Constraint(
            model.s_NonPLP,
            model.s_T,
            model.s_W,
            model.s_Q,
            rule=lambda model, l1, l2, t, w, q: model.v_F_DiscretePiped[l1, l2, t, w, q]
            <= (model.p_sigma_Pipeline[l1, l2] + max(model.p_delta_Pipeline.values()))
            * model.v_DQ[l1, t, w, q],
            doc="Only one flow can be non-zero for quality component w and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowPiped = Constraint(
            model.s_NonPLP,
            model.s_T,
            model.s_W,
            rule=lambda model, l1, l2, t, w: sum(
                model.v_F_DiscretePiped[l1, l2, t, w, q] for q in model.s_Q
            )
            == model.v_F_Piped[l1, l2, t],
            doc="Sum for each flow for component w equals the produced water quantity piped from location l to location l ",
        )

    def DiscretizeTruckedFlowQuality(model):

        model.v_F_DiscreteTrucked = Var(
            model.s_NonPLT,
            model.s_T,
            model.s_W,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            initialize=0,
            doc="Produced water quantity trucked from location l to location l for each quality component w and discretized quality q [volume/time]",
        )
        model.DiscreteMaxTruckedFlow = Constraint(
            model.s_NonPLT,
            model.s_T,
            model.s_W,
            model.s_Q,
            rule=lambda model, l1, l2, t, w, q: model.v_F_DiscreteTrucked[
                l1, l2, t, w, q
            ]
            <= (model.p_delta_Truck * model.p_max_number_of_trucks)
            * model.v_DQ[l1, t, w, q],
            doc="Only one flow can be non-zero for quality component w and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowTrucked = Constraint(
            model.s_NonPLT,
            model.s_T,
            model.s_W,
            rule=lambda model, l1, l2, t, w: sum(
                model.v_F_DiscreteTrucked[l1, l2, t, w, q] for q in model.s_Q
            )
            == model.v_F_Trucked[l1, l2, t],
            doc="Sum for each flow for component w equals the produced water quantity trucked from location l to location l  ",
        )

    def DiscretizeDisposalDestinationQuality(model):

        model.v_F_DiscreteDisposalDestination = Var(
            model.s_K,
            model.s_T,
            model.s_W,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at disposal k for each quality component w and discretized quality q [volume/time]",
        )

        model.DiscreteMaxDisposalDestination = Constraint(
            model.s_K,
            model.s_T,
            model.s_W,
            model.s_Q,
            rule=lambda model, k, t, w, q: model.v_F_DiscreteDisposalDestination[
                k, t, w, q
            ]
            <= (model.p_sigma_Disposal[k] + max(model.p_delta_Disposal.values()))
            * model.v_DQ[k, t, w, q],
            doc="Only one quantity at disposal can be non-zero for quality component w and all discretized quality q",
        )

        model.SumDiscreteDisposalDestinationIsDisposalDestination = Constraint(
            model.s_K,
            model.s_T,
            model.s_W,
            rule=lambda model, k, t, w: sum(
                model.v_F_DiscreteDisposalDestination[k, t, w, q] for q in model.s_Q
            )
            == model.v_F_DisposalDestination[k, t],
            doc="The sum of discretized quality q for disposal destination k equals the disposal destination k",
        )

    def DiscretizeOutStorageQuality(model):
        model.v_F_DiscreteFlowOutStorage = Var(
            model.s_S,
            model.s_T,
            model.s_W,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity out of storage site s for each quality component w and discretized quality q [volume/time]",
        )

        model.DiscreteMaxOutStorageFlow = Constraint(
            model.s_S,
            model.s_T,
            model.s_W,
            model.s_Q,
            rule=lambda model, s, t, w, q: model.v_F_DiscreteFlowOutStorage[s, t, w, q]
            <= (
                model.p_sigma_Storage[s]
                + sum(
                    model.p_sigma_Pipeline[s, n] + max(model.p_delta_Pipeline.values())
                    for n in model.s_N
                    if model.p_SNA[s, n]
                )
                + sum(
                    model.p_sigma_Pipeline[s, p] + max(model.p_delta_Pipeline.values())
                    for p in model.s_CP
                    if model.p_SCA[s, p]
                )
                + sum(
                    model.p_sigma_Pipeline[s, k] + max(model.p_delta_Pipeline.values())
                    for k in model.s_K
                    if model.p_SKA[s, k]
                )
                + sum(
                    model.p_sigma_Pipeline[s, r] + max(model.p_delta_Pipeline.values())
                    for r in model.s_R
                    if model.p_SRA[s, r]
                )
                + sum(
                    model.p_sigma_Pipeline[s, o] + max(model.p_delta_Pipeline.values())
                    for o in model.s_O
                    if model.p_SOA[s, o]
                )
                + sum(
                    (model.p_delta_Truck * model.p_max_number_of_trucks)
                    for p in model.s_CP
                    if model.p_SCT[s, p]
                )
                + sum(
                    (model.p_delta_Truck * model.p_max_number_of_trucks)
                    for k in model.s_K
                    if model.p_SKT[s, k]
                )
            )
            * model.v_DQ[s, t, w, q],
            doc="Only one outflow for storage site s can be non-zero for quality component w and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowOutStorage = Constraint(
            model.s_S,
            model.s_T,
            model.s_W,
            rule=lambda model, s, t, w: sum(
                model.v_F_DiscreteFlowOutStorage[s, t, w, q] for q in model.s_Q
            )
            == (
                model.v_L_Storage[s, t]
                + sum(model.v_F_Piped[s, n, t] for n in model.s_N if model.p_SNA[s, n])
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
            ),
            doc="The sum of discretized outflows at storage site s equals the total outflow for storage site s",
        )

    def DiscretizeStorageQuality(model):
        model.v_L_DiscreteStorage = Var(
            model.s_S,
            model.s_T,
            model.s_W,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume"],
            doc="Produced water quantity at storage site s for each quality component w and discretized quality q [volume]",
        )

        model.DiscreteMaxStorage = Constraint(
            model.s_S,
            model.s_T,
            model.s_W,
            model.s_Q,
            rule=lambda model, s, t, w, q: model.v_L_DiscreteStorage[s, t, w, q]
            <= model.p_sigma_Storage[s] * model.v_DQ[s, t, w, q],
            doc="Only one quantity for storage site s can be non-zero for quality component w and all discretized quality q",
        )

        model.SumDiscreteStorageIsStorage = Constraint(
            model.s_S,
            model.s_T,
            model.s_W,
            rule=lambda model, s, t, w: sum(
                model.v_L_DiscreteStorage[s, t, w, q] for q in model.s_Q
            )
            == model.v_L_Storage[s, t],
            doc="The sum of discretized quantities at storage site s equals the total quantity for storage site s",
        )

    def DiscretizeTreatmentQuality(model):
        model.v_F_DiscreteFlowTreatment = Var(
            model.s_R,
            model.s_T,
            model.s_W,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at treatment site r for each quality component w and discretized quality q [volume/time]",
        )

        model.DiscreteMaxTreatmentFlow = Constraint(
            model.s_R,
            model.s_T,
            model.s_W,
            model.s_Q,
            rule=lambda model, r, t, w, q: model.v_F_DiscreteFlowTreatment[r, t, w, q]
            <= model.p_sigma_Treatment[r] * model.v_DQ[r, t, w, q],
            doc="Only one quantity for treatment site r can be non-zero for quality component w and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowTreatment = Constraint(
            model.s_R,
            model.s_T,
            model.s_W,
            rule=lambda model, r, t, w: sum(
                model.v_F_DiscreteFlowTreatment[r, t, w, q] for q in model.s_Q
            )
            == (
                sum(model.v_F_Piped[r, p, t] for p in model.s_CP if model.p_RCA[r, p])
                + sum(model.v_F_Piped[r, s, t] for s in model.s_S if model.p_RSA[r, s])
                + model.v_F_UnusedTreatedWater[r, t]
            ),
            doc="The sum of discretized quantities at treatment site r equals the total quantity for treatment site r",
        )

    def DiscretizeFlowOutNodeQuality(model):
        model.v_F_DiscreteFlowOutNode = Var(
            model.s_N,
            model.s_T,
            model.s_W,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity out of node n for each quality component w and discretized quality q [volume/time]",
        )

        model.DiscreteMaxOutNodeFlow = Constraint(
            model.s_N,
            model.s_T,
            model.s_W,
            model.s_Q,
            rule=lambda model, n, t, w, q: model.v_F_DiscreteFlowOutNode[n, t, w, q]
            <= (
                sum(
                    model.p_sigma_Pipeline[n, n_tilde]
                    + max(model.p_delta_Pipeline.values())
                    for n_tilde in model.s_N
                    if model.p_NNA[n, n_tilde]
                )
                + sum(
                    model.p_sigma_Pipeline[n, p] + max(model.p_delta_Pipeline.values())
                    for p in model.s_CP
                    if model.p_NCA[n, p]
                )
                + sum(
                    model.p_sigma_Pipeline[n, k] + max(model.p_delta_Pipeline.values())
                    for k in model.s_K
                    if model.p_NKA[n, k]
                )
                + sum(
                    model.p_sigma_Pipeline[n, r] + max(model.p_delta_Pipeline.values())
                    for r in model.s_R
                    if model.p_NRA[n, r]
                )
                + sum(
                    model.p_sigma_Pipeline[n, s] + max(model.p_delta_Pipeline.values())
                    for s in model.s_S
                    if model.p_NSA[n, s]
                )
                + sum(
                    model.p_sigma_Pipeline[n, o] + max(model.p_delta_Pipeline.values())
                    for o in model.s_O
                    if model.p_NOA[n, o]
                )
            )
            * model.v_DQ[n, t, w, q],
            doc="Only one outflow for node n can be non-zero for quality component w and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowOutNode = Constraint(
            model.s_N,
            model.s_T,
            model.s_W,
            rule=lambda model, n, t, w: sum(
                model.v_F_DiscreteFlowOutNode[n, t, w, q] for q in model.s_Q
            )
            == (
                sum(
                    model.v_F_Piped[n, n_tilde, t]
                    for n_tilde in model.s_N
                    if model.p_NNA[n, n_tilde]
                )
                + sum(model.v_F_Piped[n, p, t] for p in model.s_CP if model.p_NCA[n, p])
                + sum(model.v_F_Piped[n, k, t] for k in model.s_K if model.p_NKA[n, k])
                + sum(model.v_F_Piped[n, r, t] for r in model.s_R if model.p_NRA[n, r])
                + sum(model.v_F_Piped[n, s, t] for s in model.s_S if model.p_NSA[n, s])
                + sum(model.v_F_Piped[n, o, t] for o in model.s_O if model.p_NOA[n, o])
            ),
            doc="The sum of discretized outflows at node n equals the total outflow for node n",
        )

    def DiscretizeBeneficialReuseQuality(model):
        model.v_F_DiscreteBeneficialReuseDestination = Var(
            model.s_O,
            model.s_T,
            model.s_W,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at beneficial reuse destination o for each quality component w and discretized quality q [volume/time]",
        )

        model.DiscreteMaxBeneficialReuseFlow = Constraint(
            model.s_O,
            model.s_T,
            model.s_W,
            model.s_Q,
            rule=lambda model, o, t, w, q: model.v_F_DiscreteBeneficialReuseDestination[
                o, t, w, q
            ]
            <= (
                sum(
                    model.p_sigma_Pipeline[n, o] + max(model.p_delta_Pipeline.values())
                    for n in model.s_N
                    if model.p_NOA[n, o]
                )
                + sum(
                    model.p_sigma_Pipeline[s, o] + max(model.p_delta_Pipeline.values())
                    for s in model.s_S
                    if model.p_SOA[s, o]
                )
                + sum(
                    (model.p_delta_Truck * model.p_max_number_of_trucks)
                    for p in model.s_PP
                    if model.p_POT[p, o]
                )
            )
            * model.v_DQ[o, t, w, q],
            doc="Only one quantity for beneficial reuse destination o can be non-zero for quality component w and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowBeneficialReuse = Constraint(
            model.s_O,
            model.s_T,
            model.s_W,
            rule=lambda model, o, t, w: sum(
                model.v_F_DiscreteBeneficialReuseDestination[o, t, w, q]
                for q in model.s_Q
            )
            == model.v_F_BeneficialReuseDestination[o, t],
            doc="The sum of discretized quantities at beneficial reuse destination o equals the total quantity for beneficial reuse destination o",
        )

    # Create all discretization variables and constraints
    DiscretizePipeFlowQuality(model)
    DiscretizeTruckedFlowQuality(model)
    DiscretizeDisposalDestinationQuality(model)
    DiscretizeOutStorageQuality(model)
    DiscretizeStorageQuality(model)
    DiscretizeTreatmentQuality(model)
    DiscretizeFlowOutNodeQuality(model)
    DiscretizeBeneficialReuseQuality(model)

    # region Disposal
    # Material Balance
    def DisposalWaterQualityRule(b, k, w, t):
        return sum(
            sum(
                model.v_F_DiscretePiped[n, k, t, w, q] * model.p_discrete_quality[w, q]
                for q in model.s_Q
            )
            for n in model.s_N
            if model.p_NKA[n, k]
        ) + sum(
            model.v_F_Piped[s, k, t] * model.p_xi[s, w]
            for s in model.s_S
            if model.p_SKA[s, k]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[r, k, t, w, q] * model.p_discrete_quality[w, q]
                for q in model.s_Q
            )
            for r in model.s_R
            if model.p_RKA[r, k]
        ) + sum(
            model.v_F_Trucked[s, k, t] * model.p_xi[s, w]
            for s in model.s_S
            if model.p_SKT[s, k]
        ) + sum(
            model.v_F_Trucked[p, k, t] * b.p_nu_pad[p, w]
            for p in model.s_PP
            if model.p_PKT[p, k]
        ) + sum(
            model.v_F_Trucked[p, k, t] * b.p_nu_pad[p, w]
            for p in model.s_CP
            if model.p_CKT[p, k]
        ) + sum(
            sum(
                model.v_F_DiscreteTrucked[r, k, t, w, q]
                * model.p_discrete_quality[w, q]
                for q in model.s_Q
            )
            for r in model.s_R
            if model.p_RKT[r, k]
        ) <= sum(
            model.v_F_DiscreteDisposalDestination[k, t, w, q]
            * model.p_discrete_quality[w, q]
            for q in model.s_Q
        )

    model.DisposalWaterQuality = Constraint(
        model.s_K,
        model.s_W,
        model.s_T,
        rule=DisposalWaterQualityRule,
        doc="Disposal water quality rule",
    )
    # endregion

    # region Storage
    def StorageSiteWaterQualityRule(b, s, w, t):
        if t == model.s_T.first():
            return model.p_lambda_Storage[s] * b.p_xi_StorageSite[s, w] + sum(
                sum(
                    model.v_F_DiscretePiped[n, s, t, w, q]
                    * model.p_discrete_quality[w, q]
                    for q in model.s_Q
                )
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, w]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, w]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) <= sum(
                model.v_F_DiscreteFlowOutStorage[s, t, w, q]
                * model.p_discrete_quality[w, q]
                for q in model.s_Q
            )
        else:
            return sum(
                model.v_L_DiscreteStorage[s, model.s_T.prev(t), w, q]
                * model.p_discrete_quality[w, q]
                for q in model.s_Q
            ) + sum(
                sum(
                    model.v_F_DiscretePiped[n, s, t, w, q]
                    * model.p_discrete_quality[w, q]
                    for q in model.s_Q
                )
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, w]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, w]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) <= sum(
                model.v_F_DiscreteFlowOutStorage[s, t, w, q]
                * model.p_discrete_quality[w, q]
                for q in model.s_Q
            )

    model.StorageSiteWaterQuality = Constraint(
        model.s_S,
        model.s_W,
        model.s_T,
        rule=StorageSiteWaterQualityRule,
        doc="Storage site water quality rule",
    )
    # endregion

    # region Treatment
    def TreatmentWaterQualityRule(b, r, w, t):
        return model.p_epsilon_Treatment[r, w] * (
            sum(
                sum(
                    model.v_F_DiscretePiped[n, r, t, w, q]
                    * model.p_discrete_quality[w, q]
                    for q in model.s_Q
                )
                for n in model.s_N
                if model.p_NRA[n, r]
            )
            + sum(
                sum(
                    model.v_F_DiscretePiped[s, r, t, w, q]
                    * model.p_discrete_quality[w, q]
                    for q in model.s_Q
                )
                for s in model.s_S
                if model.p_SRA[s, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * b.p_nu_pad[p, w]
                for p in model.s_PP
                if model.p_PRT[p, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * b.p_nu_pad[p, w]
                for p in model.s_CP
                if model.p_CRT[p, r]
            )
        ) <= sum(
            model.v_F_DiscreteFlowTreatment[r, t, w, q] * model.p_discrete_quality[w, q]
            for q in model.s_Q
        )

    model.TreatmentWaterQuality = Constraint(
        model.s_R,
        model.s_W,
        model.s_T,
        rule=TreatmentWaterQualityRule,
        doc="Treatment water quality",
    )
    # endregion

    # region Network """
    def NetworkNodeWaterQualityRule(b, n, w, t):
        return sum(
            model.v_F_Piped[p, n, t] * b.p_nu_pad[p, w]
            for p in model.s_PP
            if model.p_PNA[p, n]
        ) + sum(
            model.v_F_Piped[p, n, t] * b.p_nu_pad[p, w]
            for p in model.s_CP
            if model.p_CNA[p, n]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[s, n, t, w, q] * model.p_discrete_quality[w, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SNA[s, n]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[n_tilde, n, t, w, q]
                * model.p_discrete_quality[w, q]
                for q in model.s_Q
            )
            for n_tilde in model.s_N
            if model.p_NNA[n_tilde, n]
        ) <= sum(
            model.v_F_DiscreteFlowOutNode[n, t, w, q] * model.p_discrete_quality[w, q]
            for q in model.s_Q
        )

    model.NetworkWaterQuality = Constraint(
        model.s_N,
        model.s_W,
        model.s_T,
        rule=NetworkNodeWaterQualityRule,
        doc="Network water quality",
    )
    # endregion

    # region Beneficial Reuse
    def BeneficialReuseWaterQuality(b, o, w, t):
        return sum(
            sum(
                model.v_F_DiscretePiped[n, o, t, w, q] * model.p_discrete_quality[w, q]
                for q in model.s_Q
            )
            for n in model.s_N
            if model.p_NOA[n, o]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[s, o, t, w, q] * model.p_discrete_quality[w, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SOA[s, o]
        ) + sum(
            model.v_F_Trucked[p, o, t] * b.p_nu_pad[p, w]
            for p in model.s_PP
            if model.p_POT[p, o]
        ) <= sum(
            model.v_F_DiscreteBeneficialReuseDestination[o, t, w, q]
            * model.p_discrete_quality[w, q]
            for q in model.s_Q
        )

    model.BeneficialReuseWaterQuality = Constraint(
        model.s_O,
        model.s_W,
        model.s_T,
        rule=BeneficialReuseWaterQuality,
        doc="Beneficial reuse capacity",
    )
    # endregion

    return model
