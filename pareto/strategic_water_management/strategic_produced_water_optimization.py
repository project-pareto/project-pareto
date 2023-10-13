#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2023 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################
# Title: STRATEGIC Produced Water Optimization Model

# Import
import math
from cmath import nan
import numpy as np
import os
import pandas as pd
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
    SolverFactory,
)

from pyomo.core.base.constraint import simple_constraint_rule
from pyomo.core.expr.current import identify_variables

# from gurobipy import *
from pyomo.common.config import ConfigBlock, ConfigValue, In, Bool
from enum import Enum, IntEnum

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


class WaterQuality(Enum):
    false = 0
    post_process = 1
    discrete = 2


class Hydraulics(Enum):
    false = 0
    post_process = 1
    co_optimize = 2


class RemovalEfficiencyMethod(Enum):
    load_based = 0
    concentration_based = 1


# Inherit from IntEnum so that these values can be used in comparisons
class TreatmentStreams(IntEnum):
    treated_stream = 1
    residual_stream = 2


class InfrastructureTiming(Enum):
    false = 0
    true = 1


# create config dictionary
CONFIG = ConfigBlock()
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
    "hydraulics",
    ConfigValue(
        default=Hydraulics.false,
        domain=In(Hydraulics),
        description="add hydraulics constraints",
        doc="""option to include pipeline hydraulics in the model either during or post optimization
        ***default*** - Hydraulics.false
        **Valid Values:** - {
        **Hydraulics.false** - does not add hydraulics feature
        **Hydraulics.post_process** - adds economic parameters for flow based on elevation changes and computes pressures at each node post-optimization,
        **Hydraulics.co_optimize** - re-solves the problem using an MINLP formulation to simulatenuosly optimize pressures and flows,
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
        default=True,
        domain=Bool,
        description="Node Capacity",
        doc="""Selection to include Node Capacity
        ***default*** - True
        **Valid Values:** - {
        **True** - Include network node capacity constraints,
        **False** - Exclude network node capacity constraints
        }""",
    ),
)

# return the units container used for strategic model
# this is needed for the testing_strategic_model.py for checking units consistency
def get_strategic_model_unit_container():
    return pyunits


CONFIG.declare(
    "water_quality",
    ConfigValue(
        default=WaterQuality.post_process,
        domain=In(WaterQuality),
        description="Water quality",
        doc="""Selection to include water quality
        ***default*** - WaterQuality.post_process
        **Valid Values:** - {
        **WaterQuality.false** - Exclude water quality from model,
        **WaterQuality.post_process** - Include water quality as post process
        **WaterQuality.discrete** - Include water quality as discrete values in model
        }""",
    ),
)


CONFIG.declare(
    "removal_efficiency_method",
    ConfigValue(
        default=RemovalEfficiencyMethod.concentration_based,
        domain=In(RemovalEfficiencyMethod),
        description="Removal efficiency calculation method",
        doc="""Method for calculating removal efficiency (load or concentration based).
        ***default*** - RemovalEfficiencyMethod.concentration_based
        **Valid Values:** - {
        **RemovalEfficiencyMethod.load_based** - use contaminant load (flow times concentration) to calculate removal efficiency,
        **RemovalEfficiencyMethod.concentration_based** - use contaminant concentration to calculate removal efficiency
        }""",
    ),
)

CONFIG.declare(
    "infrastructure_timing",
    ConfigValue(
        default=InfrastructureTiming.false,
        domain=In(InfrastructureTiming),
        description="Infrastructure timing",
        doc="""Selection to include infrastructure timing.
        ***default*** - InfrastructureTiming.false
        **Valid Values:** - {
        **InfrastructureTiming.false** - Exclude infrastructure timing from model,
        **InfrastructureTiming.true** - Include infrastructure timing in model
        }""",
    ),
)


def create_model(df_sets, df_parameters, default={}):
    model = ConcreteModel()

    # import config dictionary
    model.config = CONFIG(default)
    model.type = "strategic"
    model.df_sets = df_sets
    model.df_parameters = df_parameters

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

    model.model_units = {
        "volume": pyunits.koil_bbl,
        "distance": pyunits.mile,
        "diameter": pyunits.inch,
        "concentration": pyunits.kg / pyunits.liter,
        "currency": pyunits.kUSD,
        "pressure": pyunits.kpascal,
        "elevation": pyunits.meter,
        "time": model.decision_period,
    }
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

    # Units that are most helpful for troubleshooting
    model.unscaled_model_display_units = {
        "volume": pyunits.oil_bbl,
        "distance": pyunits.mile,
        "diameter": pyunits.inch,
        "concentration": pyunits.mg / pyunits.liter,
        "currency": pyunits.USD,
        "pressure": pyunits.pascal,
        "elevation": pyunits.meter,
        "time": model.decision_period,
    }

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

    # Define sets #

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
    model.s_QC = Set(
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

    model.s_WT = Set(
        initialize=model.df_sets["TreatmentTechnologies"], doc="Treatment Technologies"
    )

    piping_arc_types = [
        "PCA",
        "PNA",
        "PPA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NSA",
        "NRA",
        "NOA",
        "FCA",
        "RNA",
        "RCA",
        "RKA",
        "RSA",
        "SNA",
        "SCA",
        "SKA",
        "SRA",
        "SOA",
        "ROA",
    ]

    # Build dictionary of all specified piping arcs
    model.df_parameters["LLA"] = {}
    for arctype in piping_arc_types:
        if arctype in model.df_parameters:
            model.df_parameters["LLA"].update(model.df_parameters[arctype])
    model.s_LLA = Set(
        initialize=list(model.df_parameters["LLA"].keys()), doc="Valid Piping Arcs"
    )

    trucking_arc_types = [
        "PCT",
        "PKT",
        "PST",
        "PRT",
        "POT",
        "FCT",
        "CKT",
        "CST",
        "CRT",
        "CCT",
        "SCT",
        "SKT",
        "SOT",
        "RKT",
        "RST",
        "ROT",
    ]

    # Build dictionary of all specified trucking arcs
    model.df_parameters["LLT"] = {}
    for arctype in trucking_arc_types:
        if arctype in model.df_parameters:
            model.df_parameters["LLT"].update(model.df_parameters[arctype])
    model.s_LLT = Set(
        initialize=list(model.df_parameters["LLT"].keys()), doc="Valid Trucking Arcs"
    )

    # Define continuous variables #

    model.v_Z = Var(
        within=Reals,
        units=model.model_units["currency"],
        doc="Objective function variable [currency]",
    )
    model.v_F_Piped = Var(
        model.s_LLA,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Produced water quantity piped from location l to location l [volume/time]",
    )
    model.v_F_Trucked = Var(
        model.s_LLT,
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
    model.v_F_StorageEvaporationStream = Var(
        model.s_S,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Water at storage lost to evaporation [bbl/week]",
    )

    model.v_F_TreatmentFeed = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Flow of feed to a treatment site [volume/time]",
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
        doc="Total volume of produced water reused at completions [volume]",
    )
    model.v_F_TotalBeneficialReuse = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume of water beneficially reused [volume]",
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
    model.v_R_BeneficialReuse = Var(
        model.s_O,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Credit for sending water to beneficial reuse [currency/time]",
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
    model.v_R_TotalBeneficialReuse = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total credit for sending water to beneficial reuse [currency]",
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
        doc="Total deliveries to Beneficial Reuse Option [volume/time]",
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
    model.p_chi_OutsideCompletionsPad = Param(
        model.s_CP,
        initialize=model.df_parameters["CompletionsPadOutsideSystem"],
        doc="Binary parameter designating the Completion Pads that are outside the system",
    )
    model.p_chi_DesalinationTechnology = Param(
        model.s_WT,
        initialize=model.df_parameters["DesalinationTechnologies"],
        doc="Binary parameter designating the treatment technologies for Desalination",
    )
    model.p_chi_DesalinationSites = Param(
        model.s_R,
        initialize=model.df_parameters["DesalinationSites"],
        doc="Binary parameter designating which treatment sites are for desalination (1) and which are not (0)",
    )

    # If p_chi_DesalinationSites was not specified for one or more r, raise an
    # Exception
    missing_desal_sites = []
    for r in model.s_R:
        if r not in model.p_chi_DesalinationSites:
            missing_desal_sites.append(r)
    if missing_desal_sites:
        raise Exception(
            'The parameter chi_DesalinationSites (spreadsheet tab "DesalinationSites") must be specified for every treatment site (missing: '
            + ", ".join(missing_desal_sites)
            + ")"
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
    model.v_S_BeneficialReuseCapacity = Var(
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
        model.s_WT,
        model.s_J,
        within=Binary,
        initialize=0,
        doc="New or additional treatment capacity installed at treatment site with specific treatment capacity and treatment technology",
    )
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
    model.vb_y_BeneficialReuse = Var(
        model.s_O,
        model.s_T,
        within=Binary,
        initialize=0,
        doc="Beneficial reuse option selection",
    )

    # Pre-process Data #
    _preprocess_data(model)

    # Define set parameters #
    def init_arc_param(arctype):
        # If arctype is a key in the dictionary model.df_parameters, return the
        # value of that entry from the dictionary. Otherwise, return an empty
        # dictionary.
        return model.df_parameters.get(arctype, {})

    model.p_PCA = Param(
        model.s_PP,
        model.s_CP,
        default=0,
        initialize=init_arc_param("PCA"),
        doc="Valid production-to-completions pipeline arcs [-]",
    )
    model.p_PNA = Param(
        model.s_PP,
        model.s_N,
        default=0,
        initialize=init_arc_param("PNA"),
        doc="Valid production-to-node pipeline arcs [-]",
    )
    model.p_PPA = Param(
        model.s_PP,
        model.s_PP,
        default=0,
        initialize=init_arc_param("PPA"),
        doc="Valid production-to-production pipeline arcs [-]",
    )
    model.p_CNA = Param(
        model.s_CP,
        model.s_N,
        default=0,
        initialize=init_arc_param("CNA"),
        doc="Valid completion-to-node pipeline arcs [-]",
    )
    model.p_CCA = Param(
        model.s_CP,
        model.s_CP,
        default=0,
        initialize=init_arc_param("CCA"),
        doc="Valid completions-to-completions pipelin arcs [-]",
    )
    model.p_NNA = Param(
        model.s_N,
        model.s_N,
        default=0,
        initialize=init_arc_param("NNA"),
        doc="Valid node-to-node pipeline arcs [-]",
    )
    model.p_NCA = Param(
        model.s_N,
        model.s_CP,
        default=0,
        initialize=init_arc_param("NCA"),
        doc="Valid node-to-completions pipeline arcs [-]",
    )
    model.p_NKA = Param(
        model.s_N,
        model.s_K,
        default=0,
        initialize=init_arc_param("NKA"),
        doc="Valid node-to-disposal pipeline arcs [-]",
    )
    model.p_NSA = Param(
        model.s_N,
        model.s_S,
        default=0,
        initialize=init_arc_param("NSA"),
        doc="Valid node-to-storage pipeline arcs [-]",
    )
    model.p_NRA = Param(
        model.s_N,
        model.s_R,
        default=0,
        initialize=init_arc_param("NRA"),
        doc="Valid node-to-treatment pipeline arcs [-]",
    )
    model.p_NOA = Param(
        model.s_N,
        model.s_O,
        default=0,
        initialize=init_arc_param("NOA"),
        doc="Valid node-to-reuse pipeline arcs [-]",
    )
    model.p_FCA = Param(
        model.s_F,
        model.s_CP,
        default=0,
        initialize=init_arc_param("FCA"),
        doc="Valid freshwater-to-completions pipeline arcs [-]",
    )
    model.p_RNA = Param(
        model.s_R,
        model.s_N,
        default=0,
        initialize=init_arc_param("RNA"),
        doc="Valid treatment-to-node pipeline arcs [-]",
    )
    model.p_RCA = Param(
        model.s_R,
        model.s_CP,
        default=0,
        initialize=init_arc_param("RCA"),
        doc="Valid treatment-to-completions layflat arcs [-]",
    )
    model.p_RKA = Param(
        model.s_R,
        model.s_K,
        default=0,
        initialize=init_arc_param("RKA"),
        doc="Valid treatment-to-disposal pipeline arcs [-]",
    )
    model.p_RSA = Param(
        model.s_R,
        model.s_S,
        default=0,
        initialize=init_arc_param("RSA"),
        doc="Valid treatment-to-storage pipeline arcs [-]",
    )
    model.p_SNA = Param(
        model.s_S,
        model.s_N,
        default=0,
        initialize=init_arc_param("SNA"),
        doc="Valid storage-to-node pipeline arcs [-]",
    )
    model.p_SCA = Param(
        model.s_S,
        model.s_CP,
        default=0,
        initialize=init_arc_param("SCA"),
        doc="Valid storage-to-completions pipeline arcs [-]",
    )
    model.p_SKA = Param(
        model.s_S,
        model.s_K,
        default=0,
        initialize=init_arc_param("SKA"),
        doc="Valid storage-to-disposal pipeline arcs [-]",
    )
    model.p_SRA = Param(
        model.s_S,
        model.s_R,
        default=0,
        initialize=init_arc_param("SRA"),
        doc="Valid storage-to-treatment pipeline arcs [-]",
    )
    model.p_SOA = Param(
        model.s_S,
        model.s_O,
        default=0,
        initialize=init_arc_param("SOA"),
        doc="Valid storage-to-reuse pipeline arcs [-]",
    )
    model.p_ROA = Param(
        model.s_R,
        model.s_O,
        default=0,
        initialize=init_arc_param("ROA"),
        doc="Valid treatment-to-reuse pipeline arcs [-]",
    )
    model.p_PCT = Param(
        model.s_PP,
        model.s_CP,
        default=0,
        initialize=init_arc_param("PCT"),
        doc="Valid production-to-completions trucking arcs [-]",
    )
    model.p_PKT = Param(
        model.s_PP,
        model.s_K,
        default=0,
        initialize=init_arc_param("PKT"),
        doc="Valid production-to-disposal trucking arcs [-]",
    )
    model.p_PST = Param(
        model.s_PP,
        model.s_S,
        default=0,
        initialize=init_arc_param("PST"),
        doc="Valid production-to-storage trucking arcs [-]",
    )
    model.p_PRT = Param(
        model.s_PP,
        model.s_R,
        default=0,
        initialize=init_arc_param("PRT"),
        doc="Valid production-to-treatment trucking arcs [-]",
    )
    model.p_POT = Param(
        model.s_PP,
        model.s_O,
        default=0,
        initialize=init_arc_param("POT"),
        doc="Valid production-to-reuse trucking arcs [-]",
    )
    model.p_FCT = Param(
        model.s_F,
        model.s_CP,
        default=0,
        initialize=init_arc_param("FCT"),
        doc="Valid freshwater-to-completions trucking arcs [-]",
    )
    model.p_CKT = Param(
        model.s_CP,
        model.s_K,
        default=0,
        initialize=init_arc_param("CKT"),
        doc="Valid completions-to-disposal trucking arcs [-]",
    )
    model.p_CST = Param(
        model.s_CP,
        model.s_S,
        default=0,
        initialize=init_arc_param("CST"),
        doc="Valid completions-to-storage trucking arcs [-]",
    )
    model.p_CRT = Param(
        model.s_CP,
        model.s_R,
        default=0,
        initialize=init_arc_param("CRT"),
        doc="Valid completions-to-treatment trucking arcs [-]",
    )
    model.p_CCT = Param(
        model.s_CP,
        model.s_CP,
        default=0,
        initialize=init_arc_param("CCT"),
        doc="Valid completion-to-completion trucking arcs [-]",
    )
    model.p_SCT = Param(
        model.s_S,
        model.s_CP,
        default=0,
        initialize=init_arc_param("SCT"),
        doc="Valid storage-to-completions trucking arcs [-]",
    )
    model.p_SKT = Param(
        model.s_S,
        model.s_K,
        default=0,
        initialize=init_arc_param("SKT"),
        doc="Valid storage-to-disposal trucking arcs [-]",
    )
    model.p_SOT = Param(
        model.s_S,
        model.s_O,
        default=0,
        initialize=init_arc_param("SOT"),
        doc="Valid storage-to-reuse trucking arcs [-]",
    )
    model.p_RKT = Param(
        model.s_R,
        model.s_K,
        default=0,
        initialize=init_arc_param("RKT"),
        doc="Valid treatment-to-disposal trucking arcs [-]",
    )
    model.p_RST = Param(
        model.s_R,
        model.s_S,
        default=0,
        initialize=init_arc_param("RST"),
        doc="Valid treatment-to-storage trucking arcs [-]",
    )
    model.p_ROT = Param(
        model.s_R,
        model.s_O,
        default=0,
        initialize=init_arc_param("ROT"),
        doc="Valid treatment-to-reuse trucking arcs [-]",
    )

    # Define set parameters #

    # TODO: Implement - For EXISTING/INITAL pipeline capacity (l,l_tilde)=(l_tilde=l);

    PipelineCapacityIncrementsTable = {("D0"): 0}

    DisposalCapacityIncrementsTable = {("I0"): 0}

    StorageDisposalCapacityIncrementsTable = {("C0"): 0}

    DisposalCapExTable = {("K02", "I0"): 0}

    model.p_alpha_AnnualizationRate = Param(
        default=1,
        initialize=model.df_parameters["AnnualizationRate"],
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
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
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
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
        doc="Flowback supply forecast for a completions pad [volume/time]",
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
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
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
        model.s_WT,
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
    model.p_sigma_BeneficialReuseMinimum = Param(
        model.s_O,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["ReuseMinimum"].items()
        },
        units=model.model_units["volume_time"],
        doc="Minimum flow that must be sent to beneficial reuse option [volume/time]",
    )
    model.p_sigma_BeneficialReuse = Param(
        model.s_O,
        model.s_T,
        # Use a negative number for default so later we can detect for which indexes the user did/did not provide a parameter value
        default=-1,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["ReuseCapacity"].items()
        },
        units=model.model_units["volume_time"],
        doc="Capacity of beneficial reuse option [volume/time]",
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
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
    )

    model.p_sigma_OffloadingPad = Param(
        model.s_P,
        default=pyunits.convert_value(
            9999,
            from_units=pyunits.koil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
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
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
    )
    model.p_sigma_OffloadingStorage = Param(
        model.s_S,
        default=pyunits.convert_value(
            9999,
            from_units=pyunits.koil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in {}
        },
        units=model.model_units["volume_time"],
        doc="Truck offloading capacity per pad [volume/time]",
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
    )
    model.p_sigma_ProcessingPad = Param(
        model.s_P,
        default=pyunits.convert_value(
            9999,
            from_units=pyunits.koil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in {}
        },
        units=model.model_units["volume_time"],
        doc="Processing (e.g. clarification) capacity per pad [volume/time]",
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
    )
    model.p_sigma_ProcessingStorage = Param(
        model.s_S,
        default=pyunits.convert_value(
            9999,
            from_units=pyunits.koil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in {}
        },
        units=model.model_units["volume_time"],
        doc="Processing (e.g. clarification) capacity per storage site [volume/time]",
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
    )
    if model.config.node_capacity == True:
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
        model.s_WT,
        default=1.0,
        initialize=model.df_parameters["TreatmentEfficiency"],
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
        doc="Treatment efficiency [%]",
    )

    model.p_epsilon_TreatmentRemoval = Param(
        model.s_R,
        model.s_WT,
        model.s_QC,
        default=0,
        initialize=model.df_parameters["RemovalEfficiency"],
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
        doc="Removal efficiency [%]",
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
        model.s_WT,
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
    # It is expected that the units for p_tau_trucking are hours, which usually differs from the time units used
    # for flow rates, e.g., day, week, month. Therefore, for the sake of simplicity, no units are defined for p_tau_trucking,
    # as the hr units will cancel out with the units in model.p_pi_Trucking which is the hourly cost of trucking.
    model.p_tau_Trucking = Param(
        model.s_L,
        model.s_L,
        default=12,
        initialize=model.df_parameters["TruckingTime"],
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
        doc="Drive time between locations [hr]",
    )
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
        model.s_WT,
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

    model.p_tau_TreatmentExpansionLeadTime = Param(
        model.s_R,
        model.s_WT,
        model.s_J,
        default=0,
        # input units are already model units (decision period), so do not need to be converted
        initialize=model.df_parameters["TreatmentExpansionLeadTime"],
        units=model.model_units["time"],
        doc="Treatment construction/expansion lead time for selected site, treatment type, and size [time]",
    )

    model.p_tau_DisposalExpansionLeadTime = Param(
        model.s_K,
        model.s_I,
        default=0,
        # input units are already model units (decision period), so do not need to be converted
        initialize=model.df_parameters["DisposalExpansionLeadTime"],
        units=model.model_units["time"],
        doc="Disposal construction/expansion lead time for selected site and size [time]",
    )

    model.p_tau_StorageExpansionLeadTime = Param(
        model.s_S,
        model.s_C,
        default=0,
        # input units are already model units (decision period), so do not need to be converted
        initialize=model.df_parameters["StorageExpansionLeadTime"],
        units=model.model_units["time"],
        doc="Storage construction/expansion lead time for selected site and size [time]",
    )

    if model.config.pipeline_cost == PipelineCost.distance_based:
        model.p_tau_PipelineExpansionLeadTime = Param(
            default=0,
            # distance units need to be converted
            initialize=pyunits.convert_value(
                model.df_parameters["PipelineExpansionLeadTime_Dist"][
                    "pipeline_expansion_lead_time"
                ],
                from_units=model.model_units["time"] / model.user_units["distance"],
                to_units=model.model_units["time"] / model.model_units["distance"],
            ),
            units=model.model_units["time"] / model.model_units["distance"],
            doc="Pipeline construction/expansion lead time [time/distance]",
        )
    elif model.config.pipeline_cost == PipelineCost.capacity_based:
        model.p_tau_PipelineExpansionLeadTime = Param(
            model.s_L,
            model.s_L,
            model.s_D,
            default=0,
            # input units are already model units (decision period), so do not need to be converted
            initialize=model.df_parameters["PipelineExpansionLeadTime_Capac"],
            units=model.model_units["time"],
            doc="Pipeline construction/expansion lead time [time]",
        )
    model.p_omega_EvaporationRate = Param(
        default=pyunits.convert_value(
            3000,
            from_units=pyunits.oil_bbl / pyunits.day,
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
        model.s_WT,
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
    model.p_rho_BeneficialReuse = Param(
        model.s_O,
        default=pyunits.convert_value(
            0.0,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in model.df_parameters["BeneficialReuseCredit"].items()
        },
        units=model.model_units["currency_volume"],
        doc="Credit for sending water to beneficial reuse [currency/volume]",
    )
    _df_parameters = {}
    if model.config.hydraulics != Hydraulics.false:
        # Elevation parameter is only used in the hydraulics module and is not needed in the basic version
        model.p_zeta_Elevation = Param(
            model.s_L,
            default=100,
            domain=NonNegativeReals,
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["elevation"],
                    to_units=model.model_units["elevation"],
                )
                for key, value in model.df_parameters["Elevation"].items()
            },
            units=pyunits.meter,
            doc="Elevation of each node in the network",
        )
    if model.config.hydraulics == Hydraulics.post_process:
        # In the post-process based hydraulics model an economics-based penalty is added
        # to moderate flow through pipelines based on the elevation change.
        max_elevation = max([val for val in model.df_parameters["Elevation"].values()])
        min_elevation = min([val for val in model.df_parameters["Elevation"].values()])
        max_elevation_change = max_elevation - min_elevation
        # Set economic penalties for pipeline operational Cost based on the elevation changes
        for k1 in model.s_L:
            for k2 in model.s_L:
                if (k1, k2) in model.s_LLA:
                    elevation_delta = value(model.p_zeta_Elevation[k1]) - value(
                        model.p_zeta_Elevation[k2]
                    )
                    _df_parameters[(k1, k2)] = max(
                        0,
                        (
                            model.df_parameters["PipelineOperationalCost"][(k1, k2)]
                            - (
                                0.01
                                * max(
                                    [
                                        val
                                        for val in model.df_parameters[
                                            "PipelineOperationalCost"
                                        ].values()
                                    ]
                                )
                                * elevation_delta
                                / max_elevation_change
                            )
                        ),
                    )
    else:
        _df_parameters = model.df_parameters["PipelineOperationalCost"]

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
            for key, value in _df_parameters.items()
        },
        units=model.model_units["currency_volume"],
        doc="Pipeline operational cost [currency/volume]",
    )
    TruckingHourlyCost_convert_to_model = {
        key: pyunits.convert_value(
            value,
            from_units=model.user_units["currency"],
            to_units=model.model_units["currency"],
        )
        for key, value in model.df_parameters["TruckingHourlyCost"].items()
    }
    # COMMENT: For this parameter only currency units are defined, as the hourly rate is canceled out with the
    # trucking time units from parameter p_Tau_Trucking. This is to avoid adding an extra unit for time which may
    # be confusing
    model.p_pi_Trucking = Param(
        model.s_L,
        default=max(TruckingHourlyCost_convert_to_model.values()) * 100
        if TruckingHourlyCost_convert_to_model
        else pyunits.convert_value(
            15000,
            from_units=pyunits.USD,
            to_units=model.model_units["currency"],
        ),
        initialize=TruckingHourlyCost_convert_to_model,
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
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.koil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        units=model.model_units["volume_time"],
        doc="Big-M flow parameter [volume/time]",
    )

    model.p_M_Concentration = Param(
        default=100,
        units=model.model_units["concentration"],
        doc="Big-M concentration parameter [concentration]",
    )

    model.p_M_Flow_Conc = Param(
        initialize=model.p_M_Concentration * model.p_M_Flow,
        units=model.model_units["concentration"] * model.model_units["volume_time"],
        doc="Big-M flow-concentration parameter [concentration * volume_time]",
    )

    model.p_psi_FracDemand = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_Production = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_Flowback = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_PipelineCapacity = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_StorageCapacity = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / pyunits.koil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        units=model.model_units["currency_volume"],
        doc="Slack cost parameter [currency/volume]",
    )
    model.p_psi_DisposalCapacity = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_TreatmentCapacity = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )
    model.p_psi_BeneficialReuseCapacity = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/volume/time]",
    )

    model.p_chi_DisposalExpansionAllowed = Param(
        model.s_K,
        default=0,
        # If initial capacity > 0, then DisposalExpansionAllowed is 0
        initialize={
            key: 0 if value and value > 0 else 1
            for key, value in model.df_parameters["InitialDisposalCapacity"].items()
        },
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
        doc="Indicates if Expansion is allowed at site k",
    )

    model.p_epsilon_DisposalOperatingCapacity = Param(
        model.s_K,
        model.s_T,
        default=0,
        initialize=model.df_parameters["DisposalOperatingCapacity"],
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
        doc="Operating capacity of disposal site [%]",
    )

    # Define cost objective function #

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
                - model.v_R_TotalBeneficialReuse
            )

        model.CostObjectiveFunction = Constraint(
            rule=CostObjectiveFunctionRule, doc="Cost objective function"
        )

    # Define reuse objective function #

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
                - model.v_R_TotalBeneficialReuse
            )

        model.ReuseObjectiveFunction = Constraint(
            rule=ReuseObjectiveFunctionRule, doc="Reuse objective function"
        )

    else:
        raise Exception("objective not supported")

    # Define constraints #

    def CompletionsPadDemandBalanceRule(model, p, t):
        # If completions pad is outside the system, the completions demand is not required to be met
        if model.p_chi_OutsideCompletionsPad[p] == 1:
            constraint = model.p_gamma_Completions[p, t] >= (
                sum(
                    model.v_F_Piped[l, p, t]
                    for l in (model.s_L - model.s_F)
                    if (l, p) in model.s_LLA
                )
                + sum(
                    model.v_F_Sourced[f, p, t]
                    for f in model.s_F
                    if (f, p) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, p, t]
                    for l in model.s_L
                    if (l, p) in model.s_LLT
                )
                + model.v_F_PadStorageOut[p, t]
                - model.v_F_PadStorageIn[p, t]
                + model.v_S_FracDemand[p, t]
            )
        # If the completions pad is inside the system, demand must be met
        else:
            constraint = model.p_gamma_Completions[p, t] == (
                sum(
                    model.v_F_Piped[l, p, t]
                    for l in (model.s_L - model.s_F)
                    if (l, p) in model.s_LLA
                )
                + sum(
                    model.v_F_Sourced[f, p, t]
                    for f in model.s_F
                    if (f, p) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, p, t]
                    for l in model.s_L
                    if (l, p) in model.s_LLT
                )
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

    def CompletionsPadStorageBalanceRule(model, p, t):
        if t == model.s_T.first():
            constraint = model.v_L_PadStorage[p, t] == model.p_lambda_PadStorage[p] + (
                (model.v_F_PadStorageIn[p, t] - model.v_F_PadStorageOut[p, t])
            )
        else:
            constraint = model.v_L_PadStorage[p, t] == model.v_L_PadStorage[
                p, model.s_T.prev(t)
            ] + ((model.v_F_PadStorageIn[p, t] - model.v_F_PadStorageOut[p, t]))

        return process_constraint(constraint)

    model.CompletionsPadStorageBalance = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadStorageBalanceRule,
        doc="Completions pad storage balance",
    )

    def CompletionsPadStorageCapacityRule(model, p, t):
        constraint = model.v_L_PadStorage[p, t] <= model.p_sigma_PadStorage[p]

        return process_constraint(constraint)

    model.CompletionsPadStorageCapacity = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadStorageCapacityRule,
        doc="Completions pad storage capacity",
    )

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

    def CompletionsPadTruckOffloadingCapacityRule(model, p, t):

        constraint = (
            sum(model.v_F_Trucked[l, p, t] for l in model.s_L if (l, p) in model.s_LLT)
            <= model.p_sigma_OffloadingPad[p]
        )

        return process_constraint(constraint)

    model.CompletionsPadTruckOffloadingCapacity = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadTruckOffloadingCapacityRule,
        doc="Completions pad truck offloading capacity",
    )

    def StorageSiteTruckOffloadingCapacityRule(model, s, t):
        constraint = (
            sum(model.v_F_Trucked[l, s, t] for l in model.s_L if (l, s) in model.s_LLT)
            <= model.p_sigma_OffloadingStorage[s]
        )

        return process_constraint(constraint)

    model.StorageSiteTruckOffloadingCapacity = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageSiteTruckOffloadingCapacityRule,
        doc="Storage site truck offloading capacity",
    )

    def StorageSiteProcessingCapacityRule(model, s, t):
        constraint = (
            sum(model.v_F_Piped[l, s, t] for l in model.s_L if (l, s) in model.s_LLA)
            + sum(
                model.v_F_Trucked[l, s, t] for l in model.s_L if (l, s) in model.s_LLT
            )
            <= model.p_sigma_ProcessingStorage[s]
        )

        return process_constraint(constraint)

    model.StorageSiteProcessingCapacity = Constraint(
        model.s_S,
        model.s_T,
        rule=StorageSiteProcessingCapacityRule,
        doc="Storage site processing capacity",
    )

    def ProductionPadSupplyBalanceRule(model, p, t):
        constraint = (
            model.p_beta_Production[p, t]
            == sum(model.v_F_Piped[p, l, t] for l in model.s_L if (p, l) in model.s_LLA)
            + sum(
                model.v_F_Trucked[p, l, t] for l in model.s_L if (p, l) in model.s_LLT
            )
            + model.v_S_Production[p, t]
        )
        return process_constraint(constraint)

    model.ProductionPadSupplyBalance = Constraint(
        model.s_PP,
        model.s_T,
        rule=ProductionPadSupplyBalanceRule,
        doc="Production pad supply balance",
    )

    def CompletionsPadSupplyBalanceRule(model, p, t):
        constraint = (
            model.p_beta_Flowback[p, t]
            == sum(model.v_F_Piped[p, l, t] for l in model.s_L if (p, l) in model.s_LLA)
            + sum(
                model.v_F_Trucked[p, l, t] for l in model.s_L if (p, l) in model.s_LLT
            )
            + model.v_S_Flowback[p, t]
        )

        return process_constraint(constraint)

    model.CompletionsPadSupplyBalance = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsPadSupplyBalanceRule,
        doc="Completions pad supply balance (i.e. flowback balance",
    )

    def NetworkNodeBalanceRule(model, n, t):
        constraint = sum(
            model.v_F_Piped[l, n, t] for l in model.s_L if (l, n) in model.s_LLA
        ) == sum(model.v_F_Piped[n, l, t] for l in model.s_L if (n, l) in model.s_LLA)

        return process_constraint(constraint)

    model.NetworkBalance = Constraint(
        model.s_N, model.s_T, rule=NetworkNodeBalanceRule, doc="Network node balance"
    )

    def BidirectionalFlowRule1(model, l, l_tilde, t):
        if (l, l_tilde) in model.s_LLA:
            constraint = (
                model.vb_y_Flow[l, l_tilde, t] + model.vb_y_Flow[l_tilde, l, t] == 1
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.BidirectionalFlow1 = Constraint(
        (model.s_L - model.s_F - model.s_O),
        (model.s_L - model.s_F),
        model.s_T,
        rule=BidirectionalFlowRule1,
        doc="Bi-directional flow",
    )

    def BidirectionalFlowRule2(model, l, l_tilde, t):
        if (l, l_tilde) in model.s_LLA:
            constraint = (
                model.v_F_Piped[l, l_tilde, t]
                <= model.vb_y_Flow[l, l_tilde, t] * model.p_M_Flow
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.BidirectionalFlow2 = Constraint(
        (model.s_L - model.s_F - model.s_O),
        (model.s_L - model.s_F),
        model.s_T,
        rule=BidirectionalFlowRule2,
        doc="Bi-directional flow",
    )

    def StorageSiteBalanceRule(model, s, t):
        if t == model.s_T.first():
            constraint = model.v_L_Storage[s, t] == model.p_lambda_Storage[s] + (
                sum(
                    model.v_F_Piped[l, s, t] for l in model.s_L if (l, s) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, s, t]
                    for l in model.s_L
                    if (l, s) in model.s_LLT
                )
                - sum(
                    model.v_F_Piped[s, l, t] for l in model.s_L if (s, l) in model.s_LLA
                )
                - sum(
                    model.v_F_Trucked[s, l, t]
                    for l in model.s_L
                    if (s, l) in model.s_LLT
                )
                - model.v_F_StorageEvaporationStream[s, t]
            )
        else:
            constraint = model.v_L_Storage[s, t] == model.v_L_Storage[
                s, model.s_T.prev(t)
            ] + (
                sum(
                    model.v_F_Piped[l, s, t] for l in model.s_L if (l, s) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, s, t]
                    for l in model.s_L
                    if (l, s) in model.s_LLT
                )
                - sum(
                    model.v_F_Piped[s, l, t] for l in model.s_L if (s, l) in model.s_LLA
                )
                - sum(
                    model.v_F_Trucked[s, l, t]
                    for l in model.s_L
                    if (s, l) in model.s_LLT
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

    def PipelineCapacityExpansionRule(model, l, l_tilde):
        if (l, l_tilde) in model.s_LLA:
            if (l_tilde, l) in model.s_LLA:
                # i.e., if the pipeline is defined as birectional then the aggregated capacity is available in both directions
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + model.p_sigma_Pipeline[l_tilde, l]
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
                # i.e., if the pipeline is defined as unirectional then the capacity is only available in the defined direction
                constraint = (
                    model.v_F_Capacity[l, l_tilde]
                    == model.p_sigma_Pipeline[l, l_tilde]
                    + sum(
                        model.p_delta_Pipeline[d] * model.vb_y_Pipeline[l, l_tilde, d]
                        for d in model.s_D
                    )
                    + model.v_S_PipelineCapacity[l, l_tilde]
                )
                return process_constraint(constraint)

        else:
            return Constraint.Skip

    model.PipelineCapacityExpansion = Constraint(
        model.s_L,
        model.s_L,
        rule=PipelineCapacityExpansionRule,
        doc="Pipeline capacity construction/expansion",
    )

    def PipelineCapacityRule(model, l, l_tilde, t):
        if (l, l_tilde) in model.s_LLA:
            constraint = (
                model.v_F_Piped[l, l_tilde, t] <= model.v_F_Capacity[l, l_tilde]
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.PipelineCapacity = Constraint(
        (model.s_L - model.s_O - model.s_K),
        (model.s_L - model.s_F),
        model.s_T,
        rule=PipelineCapacityRule,
        doc="Pipeline capacity",
    )

    # only include network node capacity constraint if config is set to true
    if model.config.node_capacity == True:

        def NetworkNodeCapacityRule(model, n, t):
            if value(model.p_sigma_NetworkNode[n]) > 0:
                constraint = (
                    sum(
                        model.v_F_Piped[l, n, t]
                        for l in model.s_L
                        if (l, n) in model.s_LLA
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

    def StorageCapacityRule(model, s, t):
        constraint = model.v_L_Storage[s, t] <= model.v_X_Capacity[s]

        return process_constraint(constraint)

    model.StorageCapacity = Constraint(
        model.s_S, model.s_T, rule=StorageCapacityRule, doc="Storage capacity"
    )

    def DisposalCapacityExpansionRule(model, k):
        constraint = (
            model.v_D_Capacity[k]
            == model.p_sigma_Disposal[k]
            + sum(
                model.p_delta_Disposal[i] * model.vb_y_Disposal[k, i] for i in model.s_I
            )
            * model.p_chi_DisposalExpansionAllowed[k]
            + model.v_S_DisposalCapacity[k]
        )

        return process_constraint(constraint)

    model.DisposalCapacityExpansion = Constraint(
        model.s_K,
        rule=DisposalCapacityExpansionRule,
        doc="Disposal capacity construction/expansion",
    )

    def DisposalCapacityRule(model, k, t):
        constraint = (
            sum(model.v_F_Piped[l, k, t] for l in model.s_L if (l, k) in model.s_LLA)
            + sum(
                model.v_F_Trucked[l, k, t] for l in model.s_L if (l, k) in model.s_LLT
            )
            <= model.v_D_Capacity[k]
        )
        return process_constraint(constraint)

    model.DisposalCapacity = Constraint(
        model.s_K, model.s_T, rule=DisposalCapacityRule, doc="Disposal capacity"
    )

    def TreatmentCapacityExpansionRule(model, r):
        return model.v_T_Capacity[r] == sum(
            (
                model.p_sigma_Treatment[r, wt]
                * sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                + sum(
                    model.p_delta_Treatment[wt, j] * model.vb_y_Treatment[r, wt, j]
                    for j in model.s_J
                )
            )
            for wt in model.s_WT
        )

    model.TreatmentCapacityExpansion = Constraint(
        model.s_R,
        rule=TreatmentCapacityExpansionRule,
        doc="Treatment capacity construction/expansion",
    )

    def TreatmentCapacityRule(model, r, t):
        constraint = (
            sum(model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA)
            + sum(
                model.v_F_Trucked[l, r, t] for l in model.s_L if (l, r) in model.s_LLT
            )
            <= model.v_T_Capacity[r]
        )
        return process_constraint(constraint)

    model.TreatmentCapacity = Constraint(
        model.s_R, model.s_T, rule=TreatmentCapacityRule, doc="Treatment capacity"
    )

    def TreatmentFeedBalanceRule(model, r, t):
        constraint = (
            sum(model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA)
            + sum(
                model.v_F_Trucked[l, r, t] for l in model.s_L if (l, r) in model.s_LLT
            )
            == model.v_F_TreatmentFeed[r, t]
        )
        return process_constraint(constraint)

    model.TreatmentFeedBalance = Constraint(
        model.s_R,
        model.s_T,
        rule=TreatmentFeedBalanceRule,
        doc="Treatment center feed flow balance",
    )

    def TreatmentBalanceRule(model, r, t):
        constraint = (
            model.v_F_TreatmentFeed[r, t]
            == model.v_F_ResidualWater[r, t] + model.v_F_TreatedWater[r, t]
        )
        return process_constraint(constraint)

    model.TreatmentBalance = Constraint(
        model.s_R,
        model.s_T,
        rule=TreatmentBalanceRule,
        doc="Treatment center flow balance",
    )

    def ResidualWaterLHSRule(model, r, wt, t):
        constraint = (
            model.v_F_TreatmentFeed[r, t] * (1 - model.p_epsilon_Treatment[r, wt])
            - model.p_M_Flow
            * (1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J))
            <= model.v_F_ResidualWater[r, t]
        )
        return process_constraint(constraint)

    model.ResidualWaterLHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=ResidualWaterLHSRule,
        doc="Residual water based on treatment efficiency",
    )

    def ResidualWaterRHSRule(model, r, wt, t):
        constraint = (
            model.v_F_TreatmentFeed[r, t] * (1 - model.p_epsilon_Treatment[r, wt])
            + model.p_M_Flow
            * (1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J))
            >= model.v_F_ResidualWater[r, t]
        )
        return process_constraint(constraint)

    model.ResidualWaterRHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=ResidualWaterRHSRule,
        doc="Residual water based on treatment efficiency",
    )

    # Create a set of all treatment sites for which the treated stream should
    # be modeled
    treatment_sites_with_treated_stream_modeled = {
        origin
        for ((origin, _), value) in list(model.df_parameters["LLA"].items())
        + list(model.df_parameters["LLT"].items())
        if origin in model.s_R and value == TreatmentStreams.treated_stream
    }

    def TreatedWaterBalanceRule(model, r, t):
        # If treated stream from a treatment site should be modeled, then
        # create constraint for the treated water. Otherwise, skip.
        if r in treatment_sites_with_treated_stream_modeled:
            constraint = model.v_F_TreatedWater[r, t] == sum(
                model.v_F_Piped[r, l, t]
                for l in model.s_L
                if (r, l) in model.s_LLA
                and model.df_parameters["LLA"][r, l] == TreatmentStreams.treated_stream
            ) + sum(
                model.v_F_Trucked[r, l, t]
                for l in model.s_L
                if (r, l) in model.s_LLT
                and model.df_parameters["LLT"][r, l] == TreatmentStreams.treated_stream
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.TreatedWaterBalance = Constraint(
        model.s_R, model.s_T, rule=TreatedWaterBalanceRule, doc="Treated water balance"
    )

    # Create a set of all treatment sites for which the residual stream should
    # be modeled. Arcs originating from a treatment site may have a value of 0,
    # 1, or 2 to denote no arc, treated stream, and residual stream,
    # respectively.
    treatment_sites_with_residual_stream_modeled = {
        origin
        for ((origin, _), value) in list(model.df_parameters["LLA"].items())
        + list(model.df_parameters["LLT"].items())
        if origin in model.s_R and value == TreatmentStreams.residual_stream
    }

    def ResidualWaterBalanceRule(model, r, t):
        # If residual stream from a treatment site should be modeled, then
        # create constraint for the residual water. Otherwise, skip.
        if r in treatment_sites_with_residual_stream_modeled:
            constraint = model.v_F_ResidualWater[r, t] == sum(
                model.v_F_Piped[r, l, t]
                for l in model.s_L
                if (r, l) in model.s_LLA
                and model.df_parameters["LLA"][r, l] == TreatmentStreams.residual_stream
            ) + sum(
                model.v_F_Trucked[r, l, t]
                for l in model.s_L
                if (r, l) in model.s_LLT
                and model.df_parameters["LLT"][r, l] == TreatmentStreams.residual_stream
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.ResidualWaterBalance = Constraint(
        model.s_R,
        model.s_T,
        rule=ResidualWaterBalanceRule,
        doc="Residual water balance",
    )

    def BeneficialReuseMinimumRule(model, o, t):
        if value(model.p_sigma_BeneficialReuseMinimum[o, t]) > 0:
            constraint = (
                model.v_F_BeneficialReuseDestination[o, t]
                >= model.p_sigma_BeneficialReuseMinimum[o, t]
                * model.vb_y_BeneficialReuse[o, t]
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.BeneficialReuseMinimum = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseMinimumRule,
        doc="Beneficial reuse minimum flow",
    )

    def BeneficialReuseCapacityRule(model, o, t):
        if value(model.p_sigma_BeneficialReuse[o, t]) < 0:
            # Beneficial reuse capacity value has not been provided by user
            constraint = (
                model.v_F_BeneficialReuseDestination[o, t]
                <= model.p_M_Flow * model.vb_y_BeneficialReuse[o, t]
                + model.v_S_BeneficialReuseCapacity[o]
            )
        else:
            # Beneficial reuse capacity value has been provided by user
            constraint = (
                model.v_F_BeneficialReuseDestination[o, t]
                <= model.p_sigma_BeneficialReuse[o, t]
                * model.vb_y_BeneficialReuse[o, t]
                + model.v_S_BeneficialReuseCapacity[o]
            )

        return process_constraint(constraint)

    model.BeneficialReuseCapacity = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseCapacityRule,
        doc="Beneficial reuse capacity",
    )

    # TODO: Improve testing of Beneficial reuse capacity constraint

    def TotalBeneficialReuseVolumeRule(model):
        constraint = model.v_F_TotalBeneficialReuse == (
            sum(
                sum(model.v_F_BeneficialReuseDestination[o, t] for o in model.s_O)
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalBeneficialReuse = Constraint(
        rule=TotalBeneficialReuseVolumeRule, doc="Total beneficial reuse volume"
    )

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

    model.FreshSourcingCost = Constraint(
        model.s_F,
        model.s_CP,
        model.s_T,
        rule=FreshSourcingCostRule,
        doc="Fresh sourcing cost",
    )

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

    def DisposalCostRule(model, k, t):
        constraint = (
            model.v_C_Disposal[k, t]
            == (
                sum(
                    model.v_F_Piped[l, k, t] for l in model.s_L if (l, k) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, k, t]
                    for l in model.s_L
                    if (l, k) in model.s_LLT
                )
            )
            * model.p_pi_Disposal[k]
        )
        return process_constraint(constraint)

    model.DisposalCost = Constraint(
        model.s_K, model.s_T, rule=DisposalCostRule, doc="Disposal cost"
    )

    def TotalDisposalCostRule(model):
        constraint = model.v_C_TotalDisposal == sum(
            sum(model.v_C_Disposal[k, t] for k in model.s_K) for t in model.s_T
        )

        return process_constraint(constraint)

    model.TotalDisposalCost = Constraint(
        rule=TotalDisposalCostRule, doc="Total disposal cost"
    )

    def TotalDisposalVolumeRule(model):
        constraint = model.v_F_TotalDisposed == sum(
            sum(model.v_F_DisposalDestination[k, t] for k in model.s_K)
            for t in model.s_T
        )

        return process_constraint(constraint)

    model.TotalDisposalVolume = Constraint(
        rule=TotalDisposalVolumeRule, doc="Total disposal volume"
    )

    def TreatmentCostLHSRule(model, r, wt, t):
        constraint = (
            model.v_C_Treatment[r, t]
            >= (
                sum(
                    model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, r, t]
                    for l in model.s_L
                    if (l, r) in model.s_LLT
                )
                - model.p_M_Flow
                * (1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J))
            )
            * model.p_pi_Treatment[r, wt]
        )
        return process_constraint(constraint)

    model.TreatmentCostLHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=TreatmentCostLHSRule,
        doc="Treatment cost",
    )

    def TreatmentCostRHSRule(model, r, wt, t):
        constraint = (
            model.v_C_Treatment[r, t]
            <= (
                sum(
                    model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, r, t]
                    for l in model.s_L
                    if (l, r) in model.s_LLT
                )
                + model.p_M_Flow
                * (1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J))
            )
            * model.p_pi_Treatment[r, wt]
        )
        return process_constraint(constraint)

    model.TreatmentCostRHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=TreatmentCostRHSRule,
        doc="Treatment cost",
    )

    def TotalTreatmentCostRule(model):
        constraint = model.v_C_TotalTreatment == sum(
            sum(model.v_C_Treatment[r, t] for r in model.s_R) for t in model.s_T
        )

        return process_constraint(constraint)

    model.TotalTreatmentCost = Constraint(
        rule=TotalTreatmentCostRule, doc="Total treatment cost"
    )

    def CompletionsReuseCostRule(
        model,
        p,
        t,
    ):
        constraint = model.v_C_Reuse[p, t] == (
            (
                sum(
                    model.v_F_Piped[l, p, t]
                    for l in (model.s_L - model.s_F)
                    if (l, p) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, p, t]
                    for l in (model.s_L - model.s_F)
                    if (l, p) in model.s_LLT
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
                        model.v_F_Piped[l, p, t]
                        for l in (model.s_L - model.s_F)
                        if (l, p) in model.s_LLA
                    )
                    + sum(
                        model.v_F_Trucked[l, p, t]
                        for l in (model.s_L - model.s_F)
                        if (l, p) in model.s_LLT
                    )
                    for p in model.s_CP
                )
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalReuseVolume = Constraint(
        rule=TotalReuseVolumeRule, doc="Total volume reused at completions"
    )

    def PipingCostRule(model, l, l_tilde, t):
        if (l, l_tilde) in model.s_LLA:
            if l in model.s_F:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Sourced[l, l_tilde, t]
                    * model.p_pi_Pipeline[l, l_tilde]
                )
            else:
                constraint = (
                    model.v_C_Piped[l, l_tilde, t]
                    == model.v_F_Piped[l, l_tilde, t] * model.p_pi_Pipeline[l, l_tilde]
                )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.PipingCost = Constraint(
        (model.s_L - model.s_O - model.s_K),
        (model.s_L - model.s_F),
        model.s_T,
        rule=PipingCostRule,
        doc="Piping cost",
    )

    def TotalPipingCostRule(model):
        constraint = model.v_C_TotalPiping == (
            sum(
                sum(
                    sum(
                        model.v_C_Piped[l, l_tilde, t]
                        for l in (model.s_L - model.s_O - model.s_K)
                        if (l, l_tilde) in model.s_LLA
                    )
                    for l_tilde in (model.s_L - model.s_F)
                )
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalPipingCost = Constraint(
        rule=TotalPipingCostRule, doc="Total piping cost"
    )

    def StorageDepositCostRule(model, s, t):
        constraint = model.v_C_Storage[s, t] == (
            (
                sum(
                    model.v_F_Piped[l, s, t] for l in model.s_L if (l, s) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, s, t]
                    for l in model.s_L
                    if (l, s) in model.s_LLT
                )
            )
            * model.p_pi_Storage[s]
        )
        return process_constraint(constraint)

    model.StorageDepositCost = Constraint(
        model.s_S, model.s_T, rule=StorageDepositCostRule, doc="Storage deposit cost"
    )

    def TotalStorageCostRule(model):
        constraint = model.v_C_TotalStorage == sum(
            sum(model.v_C_Storage[s, t] for s in model.s_S) for t in model.s_T
        )

        return process_constraint(constraint)

    model.TotalStorageCost = Constraint(
        rule=TotalStorageCostRule, doc="Total storage deposit cost"
    )

    def StorageWithdrawalCreditRule(model, s, t):
        constraint = model.v_R_Storage[s, t] == (
            (
                sum(
                    model.v_F_Piped[s, l, t] for l in model.s_L if (s, l) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[s, l, t]
                    for l in model.s_L
                    if (s, l) in model.s_LLT
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

    def TotalStorageWithdrawalCreditRule(model):
        constraint = model.v_R_TotalStorage == sum(
            sum(model.v_R_Storage[s, t] for s in model.s_S) for t in model.s_T
        )
        return process_constraint(constraint)

    model.TotalStorageWithdrawalCredit = Constraint(
        rule=TotalStorageWithdrawalCreditRule, doc="Total storage withdrawal credit"
    )

    def BeneficialReuseCreditRule(model, o, t):
        constraint = model.v_R_BeneficialReuse[o, t] == (
            (
                sum(
                    model.v_F_Piped[l, o, t] for l in model.s_L if (l, o) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, o, t]
                    for l in model.s_L
                    if (l, o) in model.s_LLT
                )
            )
            * model.p_rho_BeneficialReuse[o]
        )

        return process_constraint(constraint)

    model.BeneficialReuseCredit = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseCreditRule,
        doc="Beneficial reuse credit",
    )

    def TotalBeneficialReuseCreditRule(model):
        constraint = model.v_R_TotalBeneficialReuse == sum(
            sum(model.v_R_BeneficialReuse[o, t] for o in model.s_O) for t in model.s_T
        )
        return process_constraint(constraint)

    model.TotalBeneficialReuseCredit = Constraint(
        rule=TotalBeneficialReuseCreditRule, doc="Total beneficial reuse credit"
    )

    def TruckingCostRule(model, l, l_tilde, t):
        if (l, l_tilde) in model.s_LLT:
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

    model.TruckingCost = Constraint(
        model.s_L, model.s_L, model.s_T, rule=TruckingCostRule, doc="Trucking cost"
    )

    def TotalTruckingCostRule(model):
        constraint = model.v_C_TotalTrucking == (
            sum(
                sum(
                    sum(
                        model.v_C_Trucked[l, l_tilde, t]
                        for l in model.s_L
                        if (l, l_tilde) in model.s_LLT
                    )
                    for l_tilde in model.s_L
                )
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalTruckingCost = Constraint(
        rule=TotalTruckingCostRule, doc="Total trucking cost"
    )

    def TotalTruckingVolumeRule(model):
        constraint = model.v_F_TotalTrucked == (
            sum(
                sum(
                    sum(
                        model.v_F_Trucked[l, l_tilde, t]
                        for l in model.s_L
                        if (l, l_tilde) in model.s_LLT
                    )
                    for l_tilde in model.s_L
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

    def TreatmentExpansionCapExRule(model):
        constraint = model.v_C_TreatmentCapEx == sum(
            sum(
                sum(
                    model.vb_y_Treatment[r, wt, j]
                    * model.p_kappa_Treatment[r, wt, j]
                    * model.p_delta_Treatment[wt, j]
                    for r in model.s_R
                )
                for j in model.s_J
            )
            for wt in model.s_WT
        )
        return process_constraint(constraint)

    model.TreatmentExpansionCapEx = Constraint(
        rule=TreatmentExpansionCapExRule,
        doc="Treatment construction or capacity expansion cost",
    )

    def PipelineExpansionCapExDistanceBasedRule(model):
        constraint = model.v_C_PipelineCapEx == (
            sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[l, l_tilde, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[l, l_tilde]
                        for l in model.s_L
                    )
                    for l_tilde in model.s_L
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
                        model.vb_y_Pipeline[l, l_tilde, d]
                        * model.p_kappa_Pipeline[l, l_tilde, d]
                        * model.p_delta_Pipeline[d]
                        for l in model.s_L
                    )
                    for l_tilde in model.s_L
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
                    model.v_S_PipelineCapacity[l, l_tilde]
                    * model.p_psi_PipelineCapacity
                    for l in model.s_L
                    if (l, l_tilde) in model.s_LLA
                )
                for l_tilde in model.s_L
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
                model.v_S_BeneficialReuseCapacity[o]
                * model.p_psi_BeneficialReuseCapacity
                for o in model.s_O
            )
        )
        return process_constraint(constraint)

    model.SlackCosts = Constraint(rule=SlackCostsRule, doc="Slack costs")

    def LogicConstraintDisposalRule(model, k):
        constraint = sum(model.vb_y_Disposal[k, i] for i in model.s_I) == 1
        return process_constraint(constraint)

    model.LogicConstraintDisposal = Constraint(
        model.s_K, rule=LogicConstraintDisposalRule, doc="Logic constraint disposal"
    )

    def LogicConstraintStorageRule(model, s):
        constraint = sum(model.vb_y_Storage[s, c] for c in model.s_C) == 1
        return process_constraint(constraint)

    model.LogicConstraintStorage = Constraint(
        model.s_S, rule=LogicConstraintStorageRule, doc="Logic constraint storage"
    )

    def LogicConstraintTreatmentRule(model, r):
        constraint = (
            sum(
                sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                for wt in model.s_WT
            )
            == 1
        )
        return process_constraint(constraint)

    model.LogicConstraintTreatmentAssignment = Constraint(
        model.s_R,
        rule=LogicConstraintTreatmentRule,
        doc="Treatment technology assignment",
    )

    def LogicConstraintDesalinationAssignmentRule(model, r):
        if model.p_chi_DesalinationSites[r]:
            constraint = (
                sum(
                    sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                    for wt in model.s_WT
                    if model.p_chi_DesalinationTechnology[wt]
                )
                == 1
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.LogicConstraintDesalinationAssignment = Constraint(
        model.s_R,
        rule=LogicConstraintDesalinationAssignmentRule,
        doc="Logic constraint for flow if not desalination",
    )

    def LogicConstraintNoDesalinationAssignmentRule(model, r):
        if not model.p_chi_DesalinationSites[r]:
            constraint = (
                sum(
                    sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                    for wt in model.s_WT
                    if not model.p_chi_DesalinationTechnology[wt]
                )
                == 1
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.LogicConstraintNoDesalinationAssignment = Constraint(
        model.s_R,
        rule=LogicConstraintNoDesalinationAssignmentRule,
        doc="Logic constraint for flow if not desalination",
    )

    # TODO: make this more general by checking if there is water at t = 1
    # TODO: generalize to not set evaporation at all storage sites
    def EvaporationFlowRule(model, s, t):
        if t == model.s_T.first():
            constraint = model.v_F_StorageEvaporationStream[s, t] == 0
        else:
            constraint = model.v_F_StorageEvaporationStream[
                s, t
            ] == model.p_omega_EvaporationRate * sum(
                sum(model.vb_y_Treatment[r, "CB-EV", j] for j in model.s_J)
                for r in model.s_R
                if model.p_RSA[r, s]
            )
        return process_constraint(constraint)

    model.LogicConstraintEvaporationFlow = Constraint(
        model.s_S,
        model.s_T,
        rule=EvaporationFlowRule,
        doc="Logic constraint for flow if evaporation",
    )

    def LogicConstraintPipelineRule(model, l, l_tilde):
        if (l, l_tilde) in model.s_LLA:
            constraint = sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) == 1
            return process_constraint(constraint)
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
            model.v_F_Piped[l, p, t]
            for l in (model.s_L - model.s_F)
            if (l, p) in model.s_LLA
        ) + sum(
            model.v_F_Trucked[l, p, t]
            for l in (model.s_L - model.s_F)
            if (l, p) in model.s_LLT
        )

        return process_constraint(constraint)

    model.ReuseDestinationDeliveries = Constraint(
        model.s_CP,
        model.s_T,
        rule=ReuseDestinationDeliveriesRule,
        doc="Reuse destinations volume",
    )

    def DisposalDestinationDeliveriesRule(model, k, t):
        constraint = model.v_F_DisposalDestination[k, t] == sum(
            model.v_F_Piped[l, k, t] for l in model.s_L if (l, k) in model.s_LLA
        ) + sum(model.v_F_Trucked[l, k, t] for l in model.s_L if (l, k) in model.s_LLT)

        return process_constraint(constraint)

    model.DisposalDestinationDeliveries = Constraint(
        model.s_K,
        model.s_T,
        rule=DisposalDestinationDeliveriesRule,
        doc="Disposal destinations volume",
    )

    def BeneficialReuseDeliveriesRule(model, o, t):
        constraint = model.v_F_BeneficialReuseDestination[o, t] == sum(
            model.v_F_Piped[l, o, t] for l in model.s_L if (l, o) in model.s_LLA
        ) + sum(model.v_F_Trucked[l, o, t] for l in model.s_L if (l, o) in model.s_LLT)
        return process_constraint(constraint)

    model.BeneficialReuseDeliveries = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseDeliveriesRule,
        doc="Beneficial reuse destinations volume",
    )

    def CompletionsWaterDeliveriesRule(model, p, t):
        constraint = model.v_F_CompletionsDestination[p, t] == (
            sum(
                model.v_F_Piped[l, p, t]
                for l in (model.s_L - model.s_F)
                if (l, p) in model.s_LLA
            )
            + sum(model.v_F_Sourced[f, p, t] for f in model.s_F if model.p_FCA[f, p])
            + sum(
                model.v_F_Trucked[l, p, t]
                for l in (model.s_L - model.s_F)
                if (l, p) in model.s_LLT
            )
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

    def SeismicActivityExceptionRule(model, k, t):
        constraint = (
            model.v_F_DisposalDestination[k, t]
            <= model.p_epsilon_DisposalOperatingCapacity[k, t] * model.v_D_Capacity[k]
        )
        return process_constraint(constraint)

    model.SeismicResponseArea = Constraint(
        model.s_K,
        model.s_T,
        rule=SeismicActivityExceptionRule,
        doc="Constraint to restrict flow to a seismic response area",
    )

    # Define Objective and Solve Statement #

    model.objective = Objective(
        expr=model.v_Z, sense=minimize, doc="Objective function"
    )

    if model.config.water_quality is WaterQuality.discrete:
        model = water_quality_discrete(model, df_parameters, df_sets)

    return model


def pipeline_hydraulics(model):
    """
    The hydraulics module asssists in computing pressures at each node
    in the network accounting for pressure drop due to friction using
    Hazen-Williams equation and due to elevation change in the topology. This model
    consists of a pressure balance equation for each pipeline and bounds for
    pressure. The objective is to minimize the total cost of installing and operating pumps.
    This method adds a block for hydraulics with all necessary variables and constriants.
    Currently, there are two methods to solve the hydraulics block:
        1) post-process method: only the hydraulics block is solved for pressures
        2) co-optimize method: the hydraulics block is solved along with the network
    """
    cons_scaling_factor = 1e0

    # Create a block to add all variables and constraints for hydraulics within the model
    model.hydraulics = Block()
    mh = model.hydraulics

    # declaring variables and parameters required regardless of the hydraulics method
    mh.p_iota_HW_material_factor_pipeline = Param(
        initialize=130,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Pipeline material factor for Hazen-Williams equation",
    )
    mh.p_rhog = Param(
        initialize=9.8 * 1,
        units=model.model_units["pressure"] / pyunits.meter,
        doc="g (m/s2) * density of PW (assumed to be 1000 kg/m3)",
    )
    mh.p_nu_PumpFixedCost = Param(
        initialize=1,
        mutable=True,
        units=model.model_units["currency"],
        doc="Fixed cost of adding a pump in kUSD",
    )
    mh.p_nu_ElectricityCost = Param(
        initialize=0.1e-3,
        mutable=True,
        doc="Cost of Electricity assumed in kUSD/kWh",
    )
    mh.p_eta_PumpEfficiency = Param(
        initialize=0.9,
        mutable=True,
        doc="Pumps Efficiency",
    )
    mh.p_eta_MotorEfficiency = Param(
        initialize=0.9,
        mutable=True,
        doc="Motor Efficiency of the Pump",
    )
    mh.p_xi_Min_AOP = Param(
        initialize=pyunits.convert_value(
            model.df_parameters["Hydraulics"]["min_allowable_pressure"],
            from_units=model.user_units["pressure"],
            to_units=model.model_units["pressure"],
        ),
        mutable=True,
        units=model.model_units["pressure"],
        doc="Minimum ALlowable Operating Pressure",
    )
    mh.p_xi_Max_AOP = Param(
        initialize=pyunits.convert_value(
            model.df_parameters["Hydraulics"]["max_allowable_pressure"],
            from_units=model.user_units["pressure"],
            to_units=model.model_units["pressure"],
        ),
        mutable=True,
        units=model.model_units["pressure"],
        doc="Maximum ALlowable Operating Pressure",
    )
    mh.p_Initial_Pipeline_Diameter = Param(
        model.s_L,
        model.s_L,
        default=pyunits.convert_value(
            0,
            from_units=model.user_units["diameter"],
            to_units=model.model_units["diameter"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["diameter"],
                to_units=model.model_units["diameter"],
            )
            for key, value in model.df_parameters["InitialPipelineDiameters"].items()
        },
        units=model.model_units["diameter"],
        doc="Initial pipeline diameter [inch]",
    )
    mh.p_upsilon_WellPressure = Param(
        model.s_P,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["pressure"],
                to_units=model.model_units["pressure"],
            )
            for key, value in model.df_parameters["WellPressure"].items()
        },
        units=model.model_units["pressure"],
        doc="Well pressure at production or completions pad [pressure]",
    )
    mh.vb_Y_Pump = Var(
        model.s_LLA,
        within=Binary,
        initialize=0,
        doc="Binary variable for fixed cost of Pump",
    )
    mh.v_PumpHead = Var(
        model.s_LLA,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=pyunits.meter,
        doc="Pump Head added in the direction of flow, m",
    )
    mh.v_ValveHead = Var(
        model.s_LLA,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=pyunits.meter,
        doc="Valve Head removed in the direction of flow, m",
    )
    mh.v_PumpCost = Var(
        model.s_LLA,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["currency"],
        doc="Pump cost",
    )
    mh.v_Pressure = Var(
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        initialize=mh.p_xi_Min_AOP,
        bounds=(mh.p_xi_Min_AOP, None),
        units=model.model_units["pressure"],
        doc="Pressure at location l at time t in Pa",
    )
    mh.v_Z_HydrualicsCost = Var(
        within=Reals,
        units=model.model_units["currency"],
        doc="Total cost for Pumps and Valves [currency]",
    )

    # if the well pressure are known, i.e., for the production pads or the disposable wells, then fix them
    for p in model.s_P:
        for t in model.s_T:
            if value(mh.p_upsilon_WellPressure[p, t]) > 0:
                mh.v_Pressure[p, t].fix(mh.p_upsilon_WellPressure[p, t])

    # add all necessary constraints
    def MAOPressureRule(b, l1, t1):
        constraint = (
            b.v_Pressure[l1, t1] * cons_scaling_factor
            <= b.p_xi_Max_AOP * cons_scaling_factor
        )
        return process_constraint(constraint)

    mh.MAOPressure = Constraint(
        model.s_L - model.s_P,
        model.s_T,
        rule=MAOPressureRule,
        doc="Max allowable pressure rule",
    )

    def PumpHeadeRule(b, l1, l2):
        constraint = (
            sum(b.v_PumpHead[l1, l2, t] for t in model.s_T)
        ) * cons_scaling_factor <= (
            model.p_M_Flow * mh.vb_Y_Pump[l1, l2]
        ) * cons_scaling_factor
        return process_constraint(constraint)

    mh.PumpHeadCons = Constraint(
        model.s_LLA,
        rule=PumpHeadeRule,
        doc="Pump Head Constraint",
    )

    def HydraulicsCostRule(b):
        constraint = (
            mh.v_Z_HydrualicsCost * cons_scaling_factor
            == (sum((mh.v_PumpCost[key]) for key in model.s_LLA)) * cons_scaling_factor
        )
        return process_constraint(constraint)

    mh.HydraulicsCostEq = Constraint(
        rule=HydraulicsCostRule,
        doc="Total cost for pumps and valves rule",
    )

    if model.config.hydraulics == Hydraulics.post_process:
        """
        For the post process method, the pressure is computed using the
        Hazen-Williams equation in a separate stand alone method "_hazen_williams_head". In this method,
        the hydraulics block is solved alone for the objective of minimizing total cost of pumps.
        """
        mh.p_effective_Pipeline_diameter = Param(
            model.s_LLA,
            default=0,
            initialize=0,
            mutable=True,
            units=model.model_units["diameter"],
            doc="Effective pipeline diameter when two or more pipelines exist between two locations [inch]",
        )
        mh.p_HW_loss = Param(
            model.s_LLA,
            model.s_T,
            default=0,
            initialize=0,
            within=NonNegativeReals,
            mutable=True,
            units=pyunits.meter,
            doc="Hazen-Williams Frictional loss, m",
        )
        for key in model.s_LLA:
            mh.p_effective_Pipeline_diameter[key] = mh.p_Initial_Pipeline_Diameter[
                key
            ] + value(
                sum(
                    model.vb_y_Pipeline[key, d]
                    * model.df_parameters["PipelineDiameterValues"][d]
                    for d in model.s_D
                )
            )

        # Compute Hazen-Williams head
        for t0 in model.s_T:
            for key in model.s_LLA:
                if value(model.v_F_Piped[key, t0]) > 0.01:
                    if value(mh.p_effective_Pipeline_diameter[key]) > 0.1:
                        mh.p_HW_loss[key, t0] = _hazen_williams_head(
                            mh.p_iota_HW_material_factor_pipeline,
                            pyunits.convert(
                                model.p_lambda_Pipeline[key], to_units=pyunits.meter
                            ),
                            pyunits.convert(
                                mh.p_effective_Pipeline_diameter[key],
                                to_units=pyunits.meter,
                            ),
                            pyunits.convert(
                                model.v_F_Piped[key, t0],
                                to_units=pyunits.m**3 / pyunits.s,
                            ),
                        )

        def NodePressureRule(b, l1, l2, t1):
            if value(model.v_F_Piped[l1, l2, t1]) > 0.01:
                constraint = (
                    b.v_Pressure[l1, t1] + model.p_zeta_Elevation[l1] * mh.p_rhog
                ) * cons_scaling_factor == (
                    b.v_Pressure[l2, t1]
                    + model.p_zeta_Elevation[l2] * mh.p_rhog
                    + b.p_HW_loss[l1, l2, t1] * mh.p_rhog
                    - b.v_PumpHead[l1, l2, t1] * mh.p_rhog
                    + b.v_ValveHead[l1, l2, t1] * mh.p_rhog
                ) * cons_scaling_factor
                return process_constraint(constraint)
            else:
                return Constraint.Skip

        mh.NodePressure = Constraint(
            model.s_LLA,
            model.s_T,
            rule=NodePressureRule,
            doc="Pressure at Node L",
        )

        def PumpCostRule(b, l1, l2):
            constraint = (
                b.v_PumpCost[l1, l2] * cons_scaling_factor
                == (
                    mh.p_nu_PumpFixedCost * mh.vb_Y_Pump[l1, l2]
                    + (
                        (mh.p_nu_ElectricityCost / 3.6e6)
                        * mh.p_rhog
                        * 1e3  # convert the kUSD/kWh to kUSD/Ws
                        * sum(
                            b.v_PumpHead[l1, l2, t]
                            * pyunits.convert_value(
                                value(model.v_F_Piped[l1, l2, t]),
                                from_units=model.model_units["volume_time"],
                                to_units=pyunits.meter**3 / pyunits.h,
                            )
                            for t in model.s_T
                        )
                    )
                )
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.PumpCostEq = Constraint(
            model.s_LLA,
            rule=PumpCostRule,
            doc="Capital Cost of Pump",
        )

        mh.objective = Objective(
            expr=(mh.v_Z_HydrualicsCost),
            sense=minimize,
            doc="Objective function for Hydraulics block",
        )

    elif model.config.hydraulics == Hydraulics.co_optimize:
        """
        For the co-optimize method, the hydraulics block is solved along with
        the network model to optimize the network in the presence of
        hydraulics constraints. The objective is to minimize total cost including
        the cost of pumps.
        """
        # In the co_optimize method the objective should include the cost of pumps. So,
        # delete the original objective to add a modified objective in this method.
        del model.objective

        # add necessary variables and constraints
        mh.v_HW_loss = Var(
            model.s_LLA,
            model.s_T,
            initialize=0,
            within=NonNegativeReals,
            units=pyunits.meter,
            doc="Hazen-Williams Frictional loss, m",
        )
        mh.v_effective_Pipeline_diameter = Var(
            model.s_LLA,
            initialize=0,
            units=model.model_units["diameter"],
            doc="Diameter of pipeline between two locations [inch]",
        )

        def EffectiveDiameterRule(b, l1, l2, t1):
            constraint = mh.v_effective_Pipeline_diameter[
                l1, l2
            ] == mh.p_Initial_Pipeline_Diameter[l1, l2] + sum(
                model.vb_y_Pipeline[l1, l2, d]
                * model.df_parameters["PipelineDiameterValues"][d]
                for d in model.s_D
            )
            return process_constraint(constraint)

        mh.EffectiveDiameter = Constraint(
            model.s_LLA,
            model.s_T,
            rule=EffectiveDiameterRule,
            doc="Pressure at Node L",
        )

        def HazenWilliamsRule(b, l1, l2, t1):
            constraint = (
                b.v_HW_loss[l1, l2, t1]
                * (
                    pyunits.convert(
                        mh.v_effective_Pipeline_diameter[l1, l2], to_units=pyunits.m
                    )
                    ** 4.87
                )
            ) * cons_scaling_factor == (
                10.704
                * (
                    (
                        pyunits.convert(
                            model.v_F_Piped[l1, l2, t1],
                            to_units=pyunits.m**3 / pyunits.s,
                        )
                        / mh.p_iota_HW_material_factor_pipeline
                    )
                    ** 1.85
                )
                * (pyunits.convert(model.p_lambda_Pipeline[l1, l2], to_units=pyunits.m))
            ) * cons_scaling_factor
            return process_constraint(constraint)

        mh.HW_loss_equaltion = Constraint(
            model.s_LLA,
            model.s_T,
            rule=HazenWilliamsRule,
            doc="Pressure at Node L",
        )

        def NodePressureRule(b, l1, l2, t1):
            constraint = (
                b.v_Pressure[l1, t1]
                + model.p_zeta_Elevation[l1] * mh.p_rhog * cons_scaling_factor
                == (
                    b.v_Pressure[l2, t1]
                    + model.p_zeta_Elevation[l2] * mh.p_rhog
                    + b.v_HW_loss[l1, l2, t1] * mh.p_rhog
                    - b.v_PumpHead[l1, l2, t1] * mh.p_rhog
                    + b.v_ValveHead[l1, l2, t1] * mh.p_rhog
                )
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.NodePressure = Constraint(
            model.s_LLA,
            model.s_T,
            rule=NodePressureRule,
            doc="Pressure at Node L",
        )

        def PumpCostRule(b, l1, l2):
            constraint = (
                b.v_PumpCost[l1, l2] * cons_scaling_factor
                == (
                    mh.p_nu_PumpFixedCost * mh.vb_Y_Pump[l1, l2]
                    + (
                        (mh.p_nu_ElectricityCost / 3.6e6)
                        * mh.p_rhog
                        * 1e3  # convert the kUSD/kWh to kUSD/Ws
                        * sum(
                            b.v_PumpHead[l1, l2, t]
                            * pyunits.convert(
                                (model.v_F_Piped[l1, l2, t]),
                                to_units=pyunits.meter**3 / pyunits.h,
                            )
                            for t in model.s_T
                        )
                    )
                )
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.PumpCostEq = Constraint(
            model.s_LLA,
            rule=PumpCostRule,
            doc="Capital Cost of Pump",
        )

        model.objective = Objective(
            expr=(model.v_Z + mh.v_Z_HydrualicsCost),
            sense=minimize,
            doc="Objective function",
        )

    return model


def _hazen_williams_head(mat_factor, length, diameter, flow):
    """
    Computes Hazen-Williams (HW) head in a pipeline

    Input Args
    ----------
    mat_factor: pipeline material factor for HW equation
    length : length of pipeline segment in m.
    diameter : diameter of pipeline segment in m.
    flow : water flow through the pipeline segment in m3/s.

    Returns
    -------
    hw_friction_head : frictional head loss based on Hazen-Williams rule in m.

    """

    temp_1 = length / (diameter**4.87)
    temp_2 = (flow / mat_factor) ** 1.85
    hw_friction_head = 10.704 * temp_2 * temp_1
    return hw_friction_head


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
    # Create a set for water quality tracked at the intermediate node between treatment facility and treated water end points
    treated_water_label = "-PostTreatmentTreatedWaterNode"
    model.df_sets["TreatedWaterNodes"] = [
        r + treated_water_label for r in model.df_sets["TreatmentSites"]
    ]
    model.quality.s_R_TreatedWaterNodes = Set(
        initialize=model.df_sets["TreatedWaterNodes"],
        doc="Treated Water Node",
    )

    residual_water_label = "-PostTreatmentResidualNode"
    model.df_sets["ResidualWaterNodes"] = [
        r + residual_water_label for r in model.df_sets["TreatmentSites"]
    ]
    model.quality.s_R_ResidualWaterNodes = Set(
        initialize=model.df_sets["ResidualWaterNodes"],
        doc="Residual Water Node",
    )

    # Create a set of locations to track water quality over
    model.quality.s_WQL = Set(
        initialize=(
            model.s_L
            | model.quality.s_CP_Storage
            | model.quality.s_CP_Intermediate
            | model.quality.s_R_TreatedWaterNodes
            | model.quality.s_R_ResidualWaterNodes
        ),
        doc="Locations with tracked water quality ",
    )

    # Quality at pad
    model.quality.p_nu_pad = Param(
        model.s_P,
        model.s_QC,
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
        model.s_QC,
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
        model.s_QC,
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
        model.s_QC,
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
        model.s_QC,
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
    def DisposalWaterQualityRule(b, k, qc, t):
        constraint = (
            sum(
                b.parent_block().v_F_Piped[n, k, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NKA[n, k]
            )
            + sum(
                b.parent_block().v_F_Piped[s, k, t] * b.v_Q[s, qc, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SKA[s, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[s, k, t] * b.v_Q[s, qc, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SKT[s, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, k, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PKT[p, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, k, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CKT[p, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[r, k, t] * b.v_Q[r, qc, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_RKT[r, k]
            )
            == b.v_Q[k, qc, t] * b.parent_block().v_F_DisposalDestination[k, t]
        )
        return process_constraint(constraint)

    model.quality.DisposalWaterQuality = Constraint(
        model.s_K,
        model.s_QC,
        model.s_T,
        rule=DisposalWaterQualityRule,
        doc="Disposal water quality rule",
    )
    # endregion

    # region Storage
    def StorageSiteWaterQualityRule(b, s, qc, t):
        if t == b.parent_block().s_T.first():
            constraint = b.parent_block().p_lambda_Storage[s] * b.p_xi_StorageSite[
                s, qc
            ] + sum(
                b.parent_block().v_F_Piped[n, s, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NSA[n, s]
            ) + sum(
                b.parent_block().v_F_Piped[r, s, t]
                * b.v_Q[r + treated_water_label, qc, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_RSA[r, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PST[p, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CST[p, s]
            ) == b.v_Q[
                s, qc, t
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
                + b.parent_block().v_F_StorageEvaporationStream[s, t]
            )
        else:
            constraint = b.parent_block().v_L_Storage[
                s, b.parent_block().s_T.prev(t)
            ] * b.v_Q[s, qc, b.parent_block().s_T.prev(t)] + sum(
                b.parent_block().v_F_Piped[n, s, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NSA[n, s]
            ) + sum(
                b.parent_block().v_F_Piped[r, s, t]
                * b.v_Q[r + treated_water_label, qc, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_RSA[r, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PST[p, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CST[p, s]
            ) == b.v_Q[
                s, qc, t
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
                + b.parent_block().v_F_StorageEvaporationStream[s, t]
            )
        return process_constraint(constraint)

    model.quality.StorageSiteWaterQuality = Constraint(
        model.s_S,
        model.s_QC,
        model.s_T,
        rule=StorageSiteWaterQualityRule,
        doc="Storage site water quality rule",
    )
    # endregion

    # region Treatment
    def TreatmentFeedWaterQualityRule(b, r, qc, t):
        constraint = (
            sum(
                b.parent_block().v_F_Piped[n, r, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NRA[n, r]
            )
            + sum(
                b.parent_block().v_F_Piped[s, r, t] * b.v_Q[s, qc, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SRA[s, r]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, r, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PRT[p, r]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, r, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CRT[p, r]
            )
        ) == b.v_Q[r, qc, t] * b.parent_block().v_F_TreatmentFeed[r, t]

        return process_constraint(constraint)

    model.quality.TreatmentFeedWaterQuality = Constraint(
        model.s_R,
        model.s_QC,
        model.s_T,
        rule=TreatmentFeedWaterQualityRule,
        doc="Treatment Feed water quality",
    )

    def TreatmentWaterQualityRule(b, r, qc, t):
        constraint = (
            b.v_Q[r, qc, t] * b.parent_block().v_F_TreatmentFeed[r, t]
            == b.v_Q[r + treated_water_label, qc, t]
            * b.parent_block().v_F_TreatedWater[r, t]
            + b.v_Q[r + residual_water_label, qc, t]
            * b.parent_block().v_F_ResidualWater[r, t]
        )

        return process_constraint(constraint)

    model.quality.TreatmentWaterQuality = Constraint(
        model.s_R,
        model.s_QC,
        model.s_T,
        rule=TreatmentWaterQualityRule,
        doc="Treatment water quality",
    )

    def TreatedWaterQualityConcentrationBasedLHSRule(b, r, wt, qc, t):
        constraint = (
            b.v_Q[r, qc, t]
            * (1 - b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc])
            + b.parent_block().p_M_Concentration
            * (
                1
                - sum(
                    b.parent_block().vb_y_Treatment[r, wt, j]
                    for j in b.parent_block().s_J
                )
            )
            >= b.v_Q[r + treated_water_label, qc, t]
        )

        return process_constraint(constraint)

    def TreatedWaterQualityConcentrationBasedRHSRule(b, r, wt, qc, t):
        constraint = (
            b.v_Q[r, qc, t]
            * (1 - b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc])
            - b.parent_block().p_M_Concentration
            * (
                1
                - sum(
                    b.parent_block().vb_y_Treatment[r, wt, j]
                    for j in b.parent_block().s_J
                )
            )
            <= b.v_Q[r + treated_water_label, qc, t]
        )

        return process_constraint(constraint)

    def TreatedWaterQualityLoadBasedLHSRule(b, r, wt, qc, t):
        constraint = (
            b.v_Q[r, qc, t]
            * b.parent_block().v_F_TreatmentFeed[r, t]
            * (1 - b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc])
            + b.parent_block().p_M_Flow_Conc
            * (
                1
                - sum(
                    b.parent_block().vb_y_Treatment[r, wt, j]
                    for j in b.parent_block().s_J
                )
            )
            >= b.v_Q[r + treated_water_label, qc, t]
            * b.parent_block().v_F_TreatedWater[r, t]
        )

        return process_constraint(constraint)

    def TreatedWaterQualityLoadBasedRHSRule(b, r, wt, qc, t):
        constraint = (
            b.v_Q[r, qc, t]
            * b.parent_block().v_F_TreatmentFeed[r, t]
            * (1 - b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc])
            - b.parent_block().p_M_Flow_Conc
            * (
                1
                - sum(
                    b.parent_block().vb_y_Treatment[r, wt, j]
                    for j in b.parent_block().s_J
                )
            )
            <= b.v_Q[r + treated_water_label, qc, t]
            * b.parent_block().v_F_TreatedWater[r, t]
        )

        return process_constraint(constraint)

    if (
        model.config.removal_efficiency_method
        == RemovalEfficiencyMethod.concentration_based
    ):
        model.quality.TreatmentWaterQualityLHS = Constraint(
            model.s_R,
            model.s_WT,
            model.s_QC,
            model.s_T,
            rule=TreatedWaterQualityConcentrationBasedLHSRule,
            doc="Treatment water quality with concentration based removal efficiency",
        )
        model.quality.TreatmentWaterQualityRHS = Constraint(
            model.s_R,
            model.s_WT,
            model.s_QC,
            model.s_T,
            rule=TreatedWaterQualityConcentrationBasedRHSRule,
            doc="Treatment water quality with concentration based removal efficiency",
        )
    elif model.config.removal_efficiency_method == RemovalEfficiencyMethod.load_based:
        model.quality.TreatmentWaterQualityLHS = Constraint(
            model.s_R,
            model.s_WT,
            model.s_QC,
            model.s_T,
            rule=TreatedWaterQualityLoadBasedLHSRule,
            doc="Treatment water quality with load based removal efficiency",
        )
        model.quality.TreatmentWaterQualityRHS = Constraint(
            model.s_R,
            model.s_WT,
            model.s_QC,
            model.s_T,
            rule=TreatedWaterQualityLoadBasedRHSRule,
            doc="Treatment water quality with load based removal efficiency",
        )

    # endregion

    # region Network
    def NetworkNodeWaterQualityRule(b, n, qc, t):
        constraint = sum(
            b.parent_block().v_F_Piped[p, n, t] * b.p_nu_pad[p, qc]
            for p in b.parent_block().s_PP
            if b.parent_block().p_PNA[p, n]
        ) + sum(
            b.parent_block().v_F_Piped[p, n, t] * b.p_nu_pad[p, qc]
            for p in b.parent_block().s_CP
            if b.parent_block().p_CNA[p, n]
        ) + sum(
            b.parent_block().v_F_Piped[s, n, t] * b.v_Q[s, qc, t]
            for s in b.parent_block().s_S
            if b.parent_block().p_SNA[s, n]
        ) + sum(
            b.parent_block().v_F_Piped[n_tilde, n, t] * b.v_Q[n_tilde, qc, t]
            for n_tilde in b.parent_block().s_N
            if b.parent_block().p_NNA[n_tilde, n]
        ) + sum(
            b.parent_block().v_F_Piped[r, n, t] * b.v_Q[r, qc, t]
            for r in b.parent_block().s_R
            if b.parent_block().p_RNA[r, n]
        ) == b.v_Q[
            n, qc, t
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
        model.s_QC,
        model.s_T,
        rule=NetworkNodeWaterQualityRule,
        doc="Network water quality",
    )
    # endregion

    # region Beneficial Reuse
    def BeneficialReuseWaterQuality(b, o, qc, t):
        constraint = (
            sum(
                b.parent_block().v_F_Piped[n, o, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NOA[n, o]
            )
            + sum(
                b.parent_block().v_F_Piped[s, o, t] * b.v_Q[s, qc, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SOA[s, o]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, o, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_POT[p, o]
            )
            == b.v_Q[o, qc, t] * b.parent_block().v_F_BeneficialReuseDestination[o, t]
        )
        return process_constraint(constraint)

    model.quality.BeneficialReuseWaterQuality = Constraint(
        model.s_O,
        model.s_QC,
        model.s_T,
        rule=BeneficialReuseWaterQuality,
        doc="Beneficial reuse water quality",
    )
    # endregion

    # region Completions Pad

    # Water that is Piped and Trucked to a completions pad is mixed and split into two output streams.
    # Stream (1) goes to the completions pad and stream (2) is input to the completions storage.
    # This is the intermediate step.
    # Finally, water that meets completions demand comes from two inputs.
    # The first input is output stream (1) from the intermediate step.
    # The second is outgoing flow from the storage tank.

    def CompletionsPadIntermediateWaterQuality(b, p, qc, t):
        constraint = sum(
            b.parent_block().v_F_Piped[n, p, t] * b.v_Q[n, qc, t]
            for n in b.parent_block().s_N
            if b.parent_block().p_NCA[n, p]
        ) + sum(
            b.parent_block().v_F_Piped[p_tilde, p, t] * b.v_Q[p_tilde, qc, t]
            for p_tilde in b.parent_block().s_PP
            if b.parent_block().p_PCA[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Piped[s, p, t] * b.v_Q[s, qc, t]
            for s in b.parent_block().s_S
            if b.parent_block().p_SCA[s, p]
        ) + sum(
            b.parent_block().v_F_Piped[p_tilde, p, t] * b.v_Q[p_tilde, qc, t]
            for p_tilde in b.parent_block().s_CP
            if b.parent_block().p_CCA[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Piped[r, p, t] * b.v_Q[r + treated_water_label, qc, t]
            for r in b.parent_block().s_R
            if b.parent_block().p_RCA[r, p]
        ) + sum(
            b.parent_block().v_F_Sourced[f, p, t] * b.p_nu_freshwater[f, qc]
            for f in b.parent_block().s_F
            if b.parent_block().p_FCA[f, p]
        ) + sum(
            b.parent_block().v_F_Trucked[p_tilde, p, t] * b.v_Q[p_tilde, qc, t]
            for p_tilde in b.parent_block().s_PP
            if b.parent_block().p_PCT[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Trucked[p_tilde, p, t] * b.v_Q[p_tilde, qc, t]
            for p_tilde in b.parent_block().s_CP
            if b.parent_block().p_CCT[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Trucked[s, p, t] * b.v_Q[s, qc, t]
            for s in b.parent_block().s_S
            if b.parent_block().p_SCT[s, p]
        ) + sum(
            b.parent_block().v_F_Trucked[f, p, t] * b.p_nu_freshwater[f, qc]
            for f in b.parent_block().s_F
            if b.parent_block().p_FCT[f, p]
        ) == b.v_Q[
            p + intermediate_label, qc, t
        ] * (
            b.parent_block().v_F_PadStorageIn[p, t]
            + b.parent_block().v_F_CompletionsDestination[p, t]
        )
        return process_constraint(constraint)

    model.quality.CompletionsPadIntermediateWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadIntermediateWaterQuality,
        doc="Completions pad water quality",
    )

    def CompletionsPadWaterQuality(b, p, qc, t):
        constraint = (
            b.parent_block().v_F_PadStorageOut[p, t] * b.v_Q[p + storage_label, qc, t]
            + b.parent_block().v_F_CompletionsDestination[p, t]
            * b.v_Q[p + intermediate_label, qc, t]
            == b.v_Q[p, qc, t] * b.parent_block().p_gamma_Completions[p, t]
        )
        return process_constraint(constraint)

    model.quality.CompletionsPadWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadWaterQuality,
        doc="Completions pad water quality",
    )
    # endregion

    # region Completion Pad Storage
    def CompletionsPadStorageWaterQuality(b, p, qc, t):
        if t == b.parent_block().s_T.first():
            constraint = b.p_xi_PadStorage[
                p, qc
            ] * b.parent_block().p_lambda_PadStorage[p] + b.v_Q[
                p + intermediate_label, qc, t
            ] * b.parent_block().v_F_PadStorageIn[
                p, t
            ] == b.v_Q[
                p + storage_label, qc, t
            ] * (
                b.parent_block().v_L_PadStorage[p, t]
                + b.parent_block().v_F_PadStorageOut[p, t]
            )
        else:
            constraint = b.v_Q[
                p + storage_label, qc, b.parent_block().s_T.prev(t)
            ] * b.parent_block().v_L_PadStorage[
                p, b.parent_block().s_T.prev(t)
            ] + b.v_Q[
                p + intermediate_label, qc, t
            ] * b.parent_block().v_F_PadStorageIn[
                p, t
            ] == b.v_Q[
                p + storage_label, qc, t
            ] * (
                b.parent_block().v_L_PadStorage[p, t]
                + b.parent_block().v_F_PadStorageOut[p, t]
            )
        return process_constraint(constraint)

    model.quality.CompletionsPadStorageWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadStorageWaterQuality,
        doc="Completions pad storage water quality",
    )
    # endregion

    # Define Objective
    def ObjectiveFunctionRule(b):
        return b.v_X == sum(
            sum(
                sum(b.v_Q[p, qc, t] for p in b.parent_block().s_P)
                for qc in b.parent_block().s_QC
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


def get_max_value_for_parameter(parameter):
    return max([x.value for x in parameter.values()])


def water_quality_discrete(model, df_parameters, df_sets):
    # Add sets, parameters and constraints

    # Crate a set for Completions Pad storage by appending "-storage" to each item in the CompletionsPads Set
    storage_label = "-storage"
    df_sets["CompletionsPadsStorage"] = [
        p + storage_label for p in df_sets["CompletionsPads"]
    ]
    model.s_CP_Storage = Set(
        initialize=df_sets["CompletionsPadsStorage"],
        doc="Completions Pad Storage Tanks",
    )

    # Create a set for water quality tracked at the intermediate node between treatment facility and treated water end points
    treatment_intermediate_label = "-PostTreatmentIntermediateNode"
    model.df_sets["TreatedWaterIntermediateNodes"] = [
        r + treatment_intermediate_label for r in model.df_sets["TreatmentSites"]
    ]
    model.s_R_TreatedWaterIntermediateNode = Set(
        initialize=model.df_sets["TreatedWaterIntermediateNodes"],
        doc="Treated Water Node",
    )

    # Create a set for water quality at Completions Pads intermediate flows (i.e. the blended trucked and piped water to pad)
    intermediate_label = "-intermediate"
    df_sets["CompletionsPadsIntermediate"] = [
        p + intermediate_label for p in df_sets["CompletionsPads"]
    ]
    model.s_CP_Intermediate = Set(
        initialize=df_sets["CompletionsPadsIntermediate"],
        doc="Completions Pad Intermediate Flows",
    )

    # Quality at pad
    model.p_nu_pad = Param(
        model.s_P,
        model.s_QC,
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
    model.p_nu_freshwater = Param(
        model.s_F,
        model.s_QC,
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
    model.p_xi_StorageSite = Param(
        model.s_S,
        model.s_QC,
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
    model.p_xi_PadStorage = Param(
        model.s_CP,
        model.s_QC,
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

    # region discretization

    # Create list of discretized qualities
    discrete_quality_list = discrete_water_quality_list(6)

    # Create set with the list of discretized qualities
    model.s_Q = Set(initialize=discrete_quality_list, doc="Discrete water qualities")

    discrete_water_qualities = discretize_water_quality(
        df_parameters, df_sets, discrete_quality_list
    )
    # Initialize values for each discrete quality
    model.p_discrete_quality = Param(
        model.s_QC,
        model.s_Q,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in discrete_water_qualities.items()
        },
        units=model.model_units["concentration"],
        doc="Discretization of water components",
    )

    # For the discretization we need a upperbound for the maximum number of trucks for each truck flow
    model.p_max_number_of_trucks = Param(
        initialize=500,
        mutable=True,  # Mutable Param - can be changed in sensitivity analysis without rebuilding the entire model
        doc="Max number of trucks. Needed for upperbound on v_F_Trucked",
    )

    # Create sets for location to location arcs where the quality for the from location is variable.
    # This excludes the production pads and fresh water sources because the quality is known.
    model.s_NonPLP = Set(
        initialize=[
            NonFromPPipelines
            for NonFromPPipelines in model.s_LLA
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
        initialize=(
            model.s_K
            | model.s_S
            | model.s_R
            | model.s_O
            | model.s_N
            | model.s_CP_Storage
            | model.s_CP_Intermediate
            | model.s_R_TreatedWaterIntermediateNode
        ),
        doc="Locations with discrete quality",
    )

    def SetZToMax(model, l, t, qc, q):
        # Set initial value for discrete quality to max value. This is for setting initial solution.
        if q == discrete_quality_list[-1]:
            return 1
        return 0

    model.v_DQ = Var(
        model.s_QL,
        model.s_T,
        model.s_QC,
        model.s_Q,
        within=Binary,
        initialize=SetZToMax,
        doc="Discrete quality at location ql at time t for component w",
    )

    model.OnlyOneDiscreteQualityPerLocation = Constraint(
        model.s_QL,
        model.s_T,
        model.s_QC,
        rule=lambda model, l, t, qc: sum(model.v_DQ[l, t, qc, q] for q in model.s_Q)
        == 1,
        doc="Only one discrete quality can be chosen",
    )

    def DiscretizePipeFlowQuality(model):
        model.v_F_DiscretePiped = Var(
            model.s_NonPLP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            initialize=0,
            doc="Produced water quantity piped from location l to location l for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxPipeFlow = Constraint(
            model.s_NonPLP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, l, l_tilde, t, qc, q: model.v_F_DiscretePiped[
                l, l_tilde, t, qc, q
            ]
            <= (
                model.p_sigma_Pipeline[l, l_tilde]
                + get_max_value_for_parameter(model.p_delta_Pipeline)
            )
            * model.v_DQ[l, t, qc, q],
            doc="Only one flow can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowPiped = Constraint(
            model.s_NonPLP,
            model.s_T,
            model.s_QC,
            rule=lambda model, l, l_tilde, t, qc: sum(
                model.v_F_DiscretePiped[l, l_tilde, t, qc, q] for q in model.s_Q
            )
            == model.v_F_Piped[l, l_tilde, t],
            doc="Sum for each flow for component qc equals the produced water quantity piped from location l to location l ",
        )

    def DiscretizeTruckedFlowQuality(model):

        model.v_F_DiscreteTrucked = Var(
            model.s_NonPLT,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            initialize=0,
            doc="Produced water quantity trucked from location l to location l for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxTruckedFlow = Constraint(
            model.s_NonPLT,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, l, l_tilde, t, qc, q: model.v_F_DiscreteTrucked[
                l, l_tilde, t, qc, q
            ]
            <= (model.p_delta_Truck * model.p_max_number_of_trucks)
            * model.v_DQ[l, t, qc, q],
            doc="Only one flow can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowTrucked = Constraint(
            model.s_NonPLT,
            model.s_T,
            model.s_QC,
            rule=lambda model, l, l_tilde, t, qc: sum(
                model.v_F_DiscreteTrucked[l, l_tilde, t, qc, q] for q in model.s_Q
            )
            == model.v_F_Trucked[l, l_tilde, t],
            doc="Sum for each flow for component qc equals the produced water quantity trucked from location l to location l  ",
        )

    def DiscretizeDisposalDestinationQuality(model):

        model.v_F_DiscreteDisposalDestination = Var(
            model.s_K,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at disposal k for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxDisposalDestination = Constraint(
            model.s_K,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, k, t, qc, q: model.v_F_DiscreteDisposalDestination[
                k, t, qc, q
            ]
            <= (
                model.p_sigma_Disposal[k]
                + get_max_value_for_parameter(model.p_delta_Disposal)
            )
            * model.v_DQ[k, t, qc, q],
            doc="Only one quantity at disposal can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteDisposalDestinationIsDisposalDestination = Constraint(
            model.s_K,
            model.s_T,
            model.s_QC,
            rule=lambda model, k, t, qc: sum(
                model.v_F_DiscreteDisposalDestination[k, t, qc, q] for q in model.s_Q
            )
            == model.v_F_DisposalDestination[k, t],
            doc="The sum of discretized quality q for disposal destination k equals the disposal destination k",
        )

    def DiscretizeOutStorageQuality(model):
        model.v_F_DiscreteFlowOutStorage = Var(
            model.s_S,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity out of storage site s for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxOutStorageFlow = Constraint(
            model.s_S,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, s, t, qc, q: model.v_F_DiscreteFlowOutStorage[
                s, t, qc, q
            ]
            <= (
                model.p_sigma_Storage[s]
                + sum(
                    model.p_sigma_Pipeline[s, n]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for n in model.s_N
                    if model.p_SNA[s, n]
                )
                + sum(
                    model.p_sigma_Pipeline[s, p]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for p in model.s_CP
                    if model.p_SCA[s, p]
                )
                + sum(
                    model.p_sigma_Pipeline[s, k]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for k in model.s_K
                    if model.p_SKA[s, k]
                )
                + sum(
                    model.p_sigma_Pipeline[s, r]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for r in model.s_R
                    if model.p_SRA[s, r]
                )
                + sum(
                    model.p_sigma_Pipeline[s, o]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
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
            * model.v_DQ[s, t, qc, q],
            doc="Only one outflow for storage site s can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowOutStorage = Constraint(
            model.s_S,
            model.s_T,
            model.s_QC,
            rule=lambda model, s, t, qc: sum(
                model.v_F_DiscreteFlowOutStorage[s, t, qc, q] for q in model.s_Q
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
                + model.v_F_StorageEvaporationStream[s, t]
            ),
            doc="The sum of discretized outflows at storage site s equals the total outflow for storage site s",
        )

    def DiscretizeStorageQuality(model):
        model.v_L_DiscreteStorage = Var(
            model.s_S,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume"],
            doc="Produced water quantity at storage site s for each quality component qc and discretized quality q [volume]",
        )

        model.DiscreteMaxStorage = Constraint(
            model.s_S,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, s, t, qc, q: model.v_L_DiscreteStorage[s, t, qc, q]
            <= (
                model.p_sigma_Storage[s]
                + get_max_value_for_parameter(model.p_delta_Storage)
            )
            * model.v_DQ[s, t, qc, q],
            doc="Only one quantity for storage site s can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteStorageIsStorage = Constraint(
            model.s_S,
            model.s_T,
            model.s_QC,
            rule=lambda model, s, t, qc: sum(
                model.v_L_DiscreteStorage[s, t, qc, q] for q in model.s_Q
            )
            == model.v_L_Storage[s, t],
            doc="The sum of discretized quantities at storage site s equals the total quantity for storage site s",
        )

    def DiscretizeTreatmentQuality(model):
        model.v_F_DiscreteFlowTreatment = Var(
            model.s_R,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at treatment site r for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxTreatmentFlow = Constraint(
            model.s_R,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, r, t, qc, q: model.v_F_DiscreteFlowTreatment[r, t, qc, q]
            <= (
                get_max_value_for_parameter(model.p_sigma_Treatment)
                + get_max_value_for_parameter(model.p_delta_Treatment)
            )
            * model.v_DQ[r, t, qc, q],
            doc="Only one quantity for treatment site r can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowTreatment = Constraint(
            model.s_R,
            model.s_T,
            model.s_QC,
            rule=lambda model, r, t, qc: sum(
                model.v_F_DiscreteFlowTreatment[r, t, qc, q] for q in model.s_Q
            )
            == (model.v_F_ResidualWater[r, t] + model.v_F_TreatedWater[r, t]),
            doc="The sum of discretized quantities at treatment site r equals the total quantity for treatment site r",
        )

    def DiscretizeFlowOutNodeQuality(model):
        model.v_F_DiscreteFlowOutNode = Var(
            model.s_N,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity out of node n for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxOutNodeFlow = Constraint(
            model.s_N,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, n, t, qc, q: model.v_F_DiscreteFlowOutNode[n, t, qc, q]
            <= (
                sum(
                    model.p_sigma_Pipeline[n, n_tilde]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for n_tilde in model.s_N
                    if model.p_NNA[n, n_tilde]
                )
                + sum(
                    model.p_sigma_Pipeline[n, p]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for p in model.s_CP
                    if model.p_NCA[n, p]
                )
                + sum(
                    model.p_sigma_Pipeline[n, k]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for k in model.s_K
                    if model.p_NKA[n, k]
                )
                + sum(
                    model.p_sigma_Pipeline[n, r]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for r in model.s_R
                    if model.p_NRA[n, r]
                )
                + sum(
                    model.p_sigma_Pipeline[n, s]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for s in model.s_S
                    if model.p_NSA[n, s]
                )
                + sum(
                    model.p_sigma_Pipeline[n, o]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for o in model.s_O
                    if model.p_NOA[n, o]
                )
            )
            * model.v_DQ[n, t, qc, q],
            doc="Only one outflow for node n can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowOutNode = Constraint(
            model.s_N,
            model.s_T,
            model.s_QC,
            rule=lambda model, n, t, qc: sum(
                model.v_F_DiscreteFlowOutNode[n, t, qc, q] for q in model.s_Q
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
        model.v_F_DiscreteBRDestination = Var(
            model.s_O,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at beneficial reuse destination o for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxBeneficialReuseFlow = Constraint(
            model.s_O,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, o, t, qc, q: model.v_F_DiscreteBRDestination[o, t, qc, q]
            <= (
                sum(
                    model.p_sigma_Pipeline[n, o]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for n in model.s_N
                    if model.p_NOA[n, o]
                )
                + sum(
                    model.p_sigma_Pipeline[s, o]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for s in model.s_S
                    if model.p_SOA[s, o]
                )
                + sum(
                    (model.p_delta_Truck * model.p_max_number_of_trucks)
                    for p in model.s_PP
                    if model.p_POT[p, o]
                )
            )
            * model.v_DQ[o, t, qc, q],
            doc="Only one quantity for beneficial reuse destination o can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowBeneficialReuse = Constraint(
            model.s_O,
            model.s_T,
            model.s_QC,
            rule=lambda model, o, t, qc: sum(
                model.v_F_DiscreteBRDestination[o, t, qc, q] for q in model.s_Q
            )
            == model.v_F_BeneficialReuseDestination[o, t],
            doc="The sum of discretized quantities at beneficial reuse destination o equals the total quantity for beneficial reuse destination o",
        )

    def DiscretizeCompletionsPadIntermediateQuality(model):
        model.v_F_DiscreteFlowCPIntermediate = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity flowing out of intermediate at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxCompletionsPadIntermediateFlow = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteFlowCPIntermediate[
                p, t, qc, q
            ]
            <= (model.p_gamma_Completions[p, t] + model.p_sigma_PadStorage[p])
            * model.v_DQ[p + intermediate_label, t, qc, q],
            doc="Only one quantity for flowing out of intermediate at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowCompletionsPadIntermediate = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteFlowCPIntermediate[p, t, qc, q] for q in model.s_Q
            )
            == model.v_F_PadStorageIn[p, t] + model.v_F_CompletionsDestination[p, t],
            doc="The sum of discretized quantities for flowing out of intermediate at completion pad cp equals the total quantity for flowing out of intermediate at completion pad cp",
        )

    def DiscretizeCompletionsPadStorageQuality(model):
        model.v_F_DiscreteFlowCPStorage = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at pad storage at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxCompletionsPadStorageFlow = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteFlowCPStorage[p, t, qc, q]
            <= (model.p_gamma_Completions[p, t] + model.p_sigma_PadStorage[p])
            * model.v_DQ[p + storage_label, t, qc, q],
            doc="Only one quantity at pad storage at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowCompletionsPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteFlowCPStorage[p, t, qc, q] for q in model.s_Q
            )
            == model.v_L_PadStorage[p, t] + model.v_F_PadStorageOut[p, t],
            doc="The sum of discretized quantities at pad storage at completion pad cp equals the total quantity at pad storage at completion pad cp",
        )

    def DiscretizePadStorageQuality(model):
        model.v_L_DiscretePadStorage = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume"],
            doc="Produced water quantity at pad storage for completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_L_DiscretePadStorage[p, t, qc, q]
            <= (model.p_sigma_PadStorage[p]) * model.v_DQ[p + storage_label, t, qc, q],
            doc="Only one quantity at pad storage for completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscretePadStorageIsPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_L_DiscretePadStorage[p, t, qc, q] for q in model.s_Q
            )
            == model.v_L_PadStorage[p, t],
            doc="The sum of discretized quantities at pad storage for completion pad cp equals the total quantity at pad storage for completion pad cp",
        )

    def DiscretizeFlowOutPadStorageQuality(model):
        model.v_F_DiscreteFlowOutPadStorage = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity out of padstorage at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxFlowOutPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteFlowOutPadStorage[
                p, t, qc, q
            ]
            <= (model.p_sigma_PadStorage[p]) * model.v_DQ[p + storage_label, t, qc, q],
            doc="Only one outflow for padstorage at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowOutPadStorageIsFlowOutPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteFlowOutPadStorage[p, t, qc, q] for q in model.s_Q
            )
            == model.v_F_PadStorageOut[p, t],
            doc="The sum of discretized outflows at padstorage at completion pad cp equals the total outflow for padstorage at completion pad cp",
        )

    def DiscretizeFlowInPadStorageQuality(model):
        model.v_F_DiscreteFlowInPadStorage = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity flowing in at padstorage at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxFlowInPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteFlowInPadStorage[
                p, t, qc, q
            ]
            <= (model.p_sigma_PadStorage[p])
            * model.v_DQ[p + intermediate_label, t, qc, q],
            doc="Only one inflow for padstorage at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowInPadStorageIsFlowInPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteFlowInPadStorage[p, t, qc, q] for q in model.s_Q
            )
            == model.v_F_PadStorageIn[p, t],
            doc="The sum of discretized inflows at padstorage at completion pad cp equals the total inflows for padstorage at completion pad cp",
        )

    def DiscretizeCompletionsDestinationQuality(model):
        model.v_F_DiscreteCPDestination = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity flowing in from intermediate at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxCompletionsDestination = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteCPDestination[p, t, qc, q]
            <= (model.p_gamma_Completions[p, t])
            * model.v_DQ[p + intermediate_label, t, qc, q],
            doc="Only one quantity for flowing in from intermediate at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteCompletionsDestinationIsCompletionsDestination = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteCPDestination[p, t, qc, q] for q in model.s_Q
            )
            == model.v_F_CompletionsDestination[p, t],
            doc="The sum of discretized quantities for flowing in from intermediate at completion pad cp equals the total quantity for flowing in from intermediate at completion pad cp",
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

    DiscretizeCompletionsPadIntermediateQuality(model)
    DiscretizeCompletionsPadStorageQuality(model)
    DiscretizePadStorageQuality(model)
    DiscretizeFlowOutPadStorageQuality(model)
    DiscretizeFlowInPadStorageQuality(model)
    DiscretizeCompletionsDestinationQuality(model)

    # endregion
    # region Disposal
    # Material Balance
    def DisposalWaterQualityRule(b, k, qc, t):
        return sum(
            sum(
                model.v_F_DiscretePiped[n, k, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for n in model.s_N
            if model.p_NKA[n, k]
        ) + sum(
            model.v_F_Piped[s, k, t] * model.p_xi[s, qc]
            for s in model.s_S
            if model.p_SKA[s, k]
        ) + sum(
            model.v_F_Trucked[s, k, t] * model.p_xi[s, qc]
            for s in model.s_S
            if model.p_SKT[s, k]
        ) + sum(
            model.v_F_Trucked[p, k, t] * b.p_nu_pad[p, qc]
            for p in model.s_PP
            if model.p_PKT[p, k]
        ) + sum(
            model.v_F_Trucked[p, k, t] * b.p_nu_pad[p, qc]
            for p in model.s_CP
            if model.p_CKT[p, k]
        ) + sum(
            sum(
                model.v_F_DiscreteTrucked[r, k, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for r in model.s_R
            if model.p_RKT[r, k]
        ) <= sum(
            model.v_F_DiscreteDisposalDestination[k, t, qc, q]
            * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.DisposalWaterQuality = Constraint(
        model.s_K,
        model.s_QC,
        model.s_T,
        rule=DisposalWaterQualityRule,
        doc="Disposal water quality rule",
    )
    # endregion

    # region Storage
    def StorageSiteWaterQualityRule(b, s, qc, t):
        if t == model.s_T.first():
            return model.p_lambda_Storage[s] * b.p_xi_StorageSite[s, qc] + sum(
                sum(
                    model.v_F_DiscretePiped[n, s, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                sum(
                    model.v_F_DiscretePiped[r, s, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for r in model.s_R
                if model.p_RSA[r, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) <= sum(
                model.v_F_DiscreteFlowOutStorage[s, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
        else:
            return sum(
                model.v_L_DiscreteStorage[s, model.s_T.prev(t), qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            ) + sum(
                sum(
                    model.v_F_DiscretePiped[n, s, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                sum(
                    model.v_F_DiscretePiped[r, s, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for r in model.s_R
                if model.p_RSA[r, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) <= sum(
                model.v_F_DiscreteFlowOutStorage[s, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )

    model.StorageSiteWaterQuality = Constraint(
        model.s_S,
        model.s_QC,
        model.s_T,
        rule=StorageSiteWaterQualityRule,
        doc="Storage site water quality rule",
    )
    # endregion

    # region Treatment
    def TreatmentWaterQualityRule(b, r, qc, t):
        return (
            sum(
                sum(
                    model.v_F_DiscretePiped[n, r, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for n in model.s_N
                if model.p_NRA[n, r]
            )
            + sum(
                sum(
                    model.v_F_DiscretePiped[s, r, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for s in model.s_S
                if model.p_SRA[s, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * b.p_nu_pad[p, qc]
                for p in model.s_PP
                if model.p_PRT[p, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * b.p_nu_pad[p, qc]
                for p in model.s_CP
                if model.p_CRT[p, r]
            )
        ) <= sum(
            model.v_F_DiscreteFlowTreatment[r, t, qc, q]
            * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.TreatmentWaterQuality = Constraint(
        model.s_R,
        model.s_QC,
        model.s_T,
        rule=TreatmentWaterQualityRule,
        doc="Treatment water quality",
    )
    # endregion

    # region Network """
    def NetworkNodeWaterQualityRule(b, n, qc, t):
        return sum(
            model.v_F_Piped[p, n, t] * b.p_nu_pad[p, qc]
            for p in model.s_PP
            if model.p_PNA[p, n]
        ) + sum(
            model.v_F_Piped[p, n, t] * b.p_nu_pad[p, qc]
            for p in model.s_CP
            if model.p_CNA[p, n]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[s, n, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SNA[s, n]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[n_tilde, n, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for n_tilde in model.s_N
            if model.p_NNA[n_tilde, n]
        ) <= sum(
            model.v_F_DiscreteFlowOutNode[n, t, qc, q] * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.NetworkWaterQuality = Constraint(
        model.s_N,
        model.s_QC,
        model.s_T,
        rule=NetworkNodeWaterQualityRule,
        doc="Network water quality",
    )
    # endregion

    # region Beneficial Reuse
    def BeneficialReuseWaterQuality(b, o, qc, t):
        return sum(
            sum(
                model.v_F_DiscretePiped[n, o, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for n in model.s_N
            if model.p_NOA[n, o]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[s, o, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SOA[s, o]
        ) + sum(
            model.v_F_Trucked[p, o, t] * b.p_nu_pad[p, qc]
            for p in model.s_PP
            if model.p_POT[p, o]
        ) <= sum(
            model.v_F_DiscreteBRDestination[o, t, qc, q]
            * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.BeneficialReuseWaterQuality = Constraint(
        model.s_O,
        model.s_QC,
        model.s_T,
        rule=BeneficialReuseWaterQuality,
        doc="Beneficial reuse water quality",
    )
    # endregion

    # region Completions Pad

    # Water that is Piped and Trucked to a completions pad is mixed and split into two output streams.
    # Stream (1) goes to the completions pad and stream (2) is input to the completions storage.
    # This is the intermediate step.
    # Finally, water that meets completions demand comes from two inputs.
    # The first input is output stream (1) from the intermediate step.
    # The second is outgoing flow from the storage tank.

    def CompletionsPadIntermediateWaterQuality(b, p, qc, t):
        return sum(
            sum(
                model.v_F_DiscretePiped[n, p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for n in model.s_N
            if model.p_NCA[n, p]
        ) + sum(
            model.v_F_Piped[p_tilde, p, t] * b.p_nu_pad[p, qc]
            for p_tilde in model.s_PP
            if model.p_PCA[p_tilde, p]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[s, p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SCA[s, p]
        ) + sum(
            model.v_F_Piped[p_tilde, p, t] * b.p_nu_pad[p, qc]
            for p_tilde in model.s_CP
            if model.p_CCA[p_tilde, p]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[r, p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for r in model.s_R
            if model.p_RCA[r, p]
        ) + sum(
            model.v_F_Sourced[f, p, t] * b.p_nu_freshwater[f, qc]
            for f in model.s_F
            if model.p_FCA[f, p]
        ) + sum(
            model.v_F_Trucked[p_tilde, p, t] * b.p_nu_pad[p, qc]
            for p_tilde in model.s_PP
            if model.p_PCT[p_tilde, p]
        ) + sum(
            model.v_F_Trucked[p_tilde, p, t] * b.p_nu_pad[p, qc]
            for p_tilde in model.s_CP
            if model.p_CCT[p_tilde, p]
        ) + sum(
            sum(
                model.v_F_DiscreteTrucked[s, p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SCT[s, p]
        ) + sum(
            model.v_F_Trucked[f, p, t] * b.p_nu_freshwater[f, qc]
            for f in model.s_F
            if model.p_FCT[f, p]
        ) <= sum(
            model.v_F_DiscreteFlowCPIntermediate[p, t, qc, q]
            * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.CompletionsPadIntermediateWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadIntermediateWaterQuality,
        doc="Completions pad water quality",
    )

    # The flow to the completion pad is given, so the quality can be continuous.
    model.v_Q_CompletionPad = Var(
        model.s_CP,
        model.s_QC,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["concentration"],
        doc="Water quality at completion pad [concentration]",
    )

    def CompletionsPadWaterQuality(b, p, qc, t):
        return (
            sum(
                model.v_F_DiscreteFlowOutPadStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            + sum(
                model.v_F_DiscreteCPDestination[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            == model.v_Q_CompletionPad[p, qc, t] * model.p_gamma_Completions[p, t]
        )

    model.CompletionsPadWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadWaterQuality,
        doc="Completions pad water quality",
    )
    # endregion

    # region Completion Pad Storage
    def CompletionsPadStorageWaterQuality(b, p, qc, t):
        if t == model.s_T.first():
            return b.p_xi_PadStorage[p, qc] * model.p_lambda_PadStorage[p] + sum(
                model.v_F_DiscreteFlowInPadStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            ) <= sum(
                model.v_F_DiscreteFlowCPStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
        else:
            return sum(
                model.v_L_DiscretePadStorage[p, model.s_T.prev(t), qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            ) + sum(
                model.v_F_DiscreteFlowInPadStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            ) <= sum(
                model.v_F_DiscreteFlowCPStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )

    model.CompletionsPadStorageWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadStorageWaterQuality,
        doc="Completions pad storage water quality",
    )
    # endregion

    model.v_ObjectiveWithQuality = Var(
        within=Reals,
        doc="Obj value including minimizing quality at completion pads",
    )

    def ObjectiveFunctionRule(model):
        return (
            model.v_ObjectiveWithQuality
            == model.v_Z
            + sum(
                sum(
                    sum(model.v_Q_CompletionPad[p, qc, t] for p in model.s_CP)
                    for t in model.s_T
                )
                for qc in model.s_QC
            )
            / 1000
        )

    model.ObjectiveFunction = Constraint(
        rule=ObjectiveFunctionRule, doc="Objective function water quality"
    )

    model.objective.set_value(expr=model.v_ObjectiveWithQuality)

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
    if opt.type == "gurobi_direct":
        opt.solve(water_quality_model.quality, tee=True, save_results=False)
    else:
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
    model.scaling_factor[model.v_F_StorageEvaporationStream] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TreatmentFeed] = 1 / scaling_factor
    model.scaling_factor[model.v_F_ResidualWater] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TreatedWater] = 1 / scaling_factor
    model.scaling_factor[model.v_F_BeneficialReuseDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_CompletionsDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Sourced] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalDisposed] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalReused] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalBeneficialReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalSourced] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalTrucked] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Trucked] = 1 / scaling_factor
    model.scaling_factor[model.v_L_PadStorage] = 1 / scaling_factor
    model.scaling_factor[model.v_L_Storage] = 1 / scaling_factor
    model.scaling_factor[model.v_R_Storage] = 1 / scaling_factor
    model.scaling_factor[model.v_R_BeneficialReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_R_TotalStorage] = 1 / scaling_factor
    model.scaling_factor[model.v_R_TotalBeneficialReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_S_DisposalCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_Flowback] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_FracDemand] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_PipelineCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_Production] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_BeneficialReuseCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_TreatmentCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_StorageCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_T_Capacity] = 1 / scaling_factor
    model.scaling_factor[model.v_X_Capacity] = 1 / scaling_factor

    if model.config.water_quality is WaterQuality.discrete:
        model.scaling_factor[model.v_F_DiscretePiped] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteTrucked] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteDisposalDestination] = 1 / (
            scaling_factor
        )
        model.scaling_factor[model.v_F_DiscreteFlowOutStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_L_DiscreteStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteFlowTreatment] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteFlowOutNode] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteBRDestination] = 1 / (scaling_factor)

        model.scaling_factor[model.v_F_DiscreteFlowCPIntermediate] = 1 / (
            scaling_factor
        )
        model.scaling_factor[model.v_F_DiscreteFlowCPStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_L_DiscretePadStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteFlowOutPadStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteFlowInPadStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteCPDestination] = 1 / (scaling_factor)
        model.scaling_factor[model.v_Q_CompletionPad] = 1 / (scaling_factor)
        model.scaling_factor[model.v_ObjectiveWithQuality] = 1 / (scaling_factor)
        model.scaling_factor[model.ObjectiveFunction] = 1 / scaling_factor

    # Scaling constraints
    if model.config.objective == Objectives.cost:
        model.scaling_factor[model.CostObjectiveFunction] = 1 / scaling_factor
    elif model.config.objective == Objectives.reuse:
        model.scaling_factor[model.ReuseObjectiveFunction] = 1 / scaling_factor

    model.scaling_factor[model.BeneficialReuseMinimum] = 1 / scaling_factor
    model.scaling_factor[model.BeneficialReuseCapacity] = 1 / scaling_factor
    model.scaling_factor[model.TotalBeneficialReuse] = 1 / scaling_factor
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
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintDesalinationAssignment] = 1
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintNoDesalinationAssignment] = 1
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
    model.scaling_factor[model.BeneficialReuseCredit] = 1 / scaling_factor
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
    model.scaling_factor[model.TotalBeneficialReuseCredit] = 1 / scaling_factor
    model.scaling_factor[model.TotalTreatmentCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalTruckingCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalTruckingVolume] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentFeedBalance] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentBalance] = 1 / scaling_factor
    model.scaling_factor[model.TreatedWaterBalance] = 1 / scaling_factor
    model.scaling_factor[model.ResidualWaterBalance] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCapacity] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCapacityExpansion] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCostLHS] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCostRHS] = 1 / scaling_factor
    model.scaling_factor[model.ResidualWaterLHS] = 1 / scaling_factor
    model.scaling_factor[model.ResidualWaterRHS] = 1 / scaling_factor
    model.scaling_factor[model.TruckingCost] = 1 / (scaling_factor * 100)
    model.scaling_factor[model.TreatmentExpansionCapEx] = 1 / scaling_factor
    model.scaling_factor[model.LogicConstraintEvaporationFlow] = 1 / scaling_factor
    model.scaling_factor[model.SeismicResponseArea] = 1 / scaling_factor

    if model.config.node_capacity == True:
        model.scaling_factor[model.NetworkCapacity] = 1 / scaling_factor

    if model.config.water_quality is WaterQuality.discrete:
        model.scaling_factor[model.OnlyOneDiscreteQualityPerLocation] = 1

        model.scaling_factor[model.DiscreteMaxPipeFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowPiped] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxTruckedFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowTrucked] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxDisposalDestination] = 1 / scaling_factor
        model.scaling_factor[
            model.SumDiscreteDisposalDestinationIsDisposalDestination
        ] = (1 / scaling_factor)

        model.scaling_factor[model.DiscreteMaxOutStorageFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowOutStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxStorage] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteStorageIsStorage] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxTreatmentFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowTreatment] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxOutNodeFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowOutNode] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxBeneficialReuseFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowBeneficialReuse] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxCompletionsPadIntermediateFlow] = (
            1 / scaling_factor
        )
        model.scaling_factor[model.SumDiscreteFlowsIsFlowCompletionsPadIntermediate] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxCompletionsPadStorageFlow] = (
            1 / scaling_factor
        )
        model.scaling_factor[model.SumDiscreteFlowsIsFlowCompletionsPadStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxPadStorage] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscretePadStorageIsPadStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxFlowOutPadStorage] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowOutPadStorageIsFlowOutPadStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxFlowInPadStorage] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowInPadStorageIsFlowInPadStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxCompletionsDestination] = (
            1 / scaling_factor
        )
        model.scaling_factor[
            model.SumDiscreteCompletionsDestinationIsCompletionsDestination
        ] = (1 / scaling_factor)

        model.scaling_factor[model.DisposalWaterQuality] = 1 / (scaling_factor * 100)
        model.scaling_factor[model.StorageSiteWaterQuality] = 1 / (scaling_factor * 100)
        model.scaling_factor[model.TreatmentWaterQuality] = 1 / (scaling_factor * 100)
        model.scaling_factor[model.NetworkWaterQuality] = 1 / (scaling_factor * 100)
        model.scaling_factor[model.BeneficialReuseWaterQuality] = 1 / (
            scaling_factor * 100
        )

        model.scaling_factor[model.CompletionsPadIntermediateWaterQuality] = 1 / (
            scaling_factor * 100
        )
        model.scaling_factor[model.CompletionsPadWaterQuality] = 1 / (
            scaling_factor * 100
        )
        model.scaling_factor[model.CompletionsPadStorageWaterQuality] = 1 / (
            scaling_factor * 100
        )

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


def infrastructure_timing(model):
    # Store the start build time to a dictionary
    model.infrastructure_buildStart = {}
    # Store the lead time for built facilities to a dictionary
    model.infrastructure_leadTime = {}
    # Store time period for first use to a dictionary
    model.infrastructure_firstUse = {}
    # Due to tolerances, binaries may not exactly equal 1
    binary_epsilon = 0.1

    # Iterate through our built sites
    # Treatment - "vb_y_Treatment"
    treatment_data = model.vb_y_Treatment._data
    # Treatment Site - iterate through vb_y variables
    for i in treatment_data:
        # Get site name from data
        treatment_site = i[0]
        # add values to output dictionary
        if (
            treatment_data[i].value >= 1 - binary_epsilon
            and treatment_data[i].value <= 1 + binary_epsilon
            and model.p_delta_Treatment[(i[1], i[2])].value
            > 0  # selected capacity is nonzero
        ):
            # determine first time period that site is used
            # first use is time period where there is more volume to treatment than starting capacity
            for t in model.s_T:
                if (
                    sum(
                        model.v_F_Piped[l, treatment_site, t].value
                        for l in model.s_L
                        if (l, treatment_site) in model.s_LLA
                    )
                    + sum(
                        model.v_F_Trucked[l, treatment_site, t].value
                        for l in model.s_L
                        if (l, treatment_site) in model.s_LLT
                    )
                    > model.p_sigma_Treatment[treatment_site, i[1]].value
                ):
                    # Add first use to a dictionary
                    model.infrastructure_firstUse[treatment_site] = t
                    # Get the lead time rounded up to the nearest full time period
                    model.infrastructure_leadTime[treatment_site] = math.ceil(
                        model.p_tau_TreatmentExpansionLeadTime[i].value
                    )
                    break

    # Disposal - "vb_y_Disposal"
    disposal_data = model.vb_y_Disposal._data
    for i in disposal_data:
        # Get site name from data
        disposal_site = i[0]
        # add values to output dictionary
        if (
            disposal_data[i].value >= 1 - binary_epsilon
            and disposal_data[i].value <= 1 + binary_epsilon
            and model.p_delta_Disposal[i[1]].value > 0  # selected capacity is nonzero
        ):
            # determine first time period that site is used
            # First use is time period where more water is sent to disposal than initial capacity
            for t in model.s_T:
                if (
                    model.v_F_DisposalDestination[disposal_site, t].value
                    > model.p_sigma_Disposal[disposal_site].value
                ):
                    # Add first use to a dictionary
                    model.infrastructure_firstUse[disposal_site] = t
                    # Get the lead time rounded up to the nearest full time period
                    model.infrastructure_leadTime[disposal_site] = math.ceil(
                        model.p_tau_DisposalExpansionLeadTime[i].value
                    )
                    break

    # Storage - "vb_y_Storage"
    storage_data = model.vb_y_Storage._data
    # Storage Site - iterate through vb_y variables
    for i in storage_data:
        # Get site name from data
        storage_site = i[0]
        # add values to output dictionary
        if (
            storage_data[i].value >= 1 - binary_epsilon
            and storage_data[i].value <= 1 + binary_epsilon
            and model.p_delta_Storage[i[1]].value > 0  # selected capacity is nonzero
        ):
            # determine first time period that site is used
            # First use is when the water level exceeds the initial storage capacity
            for t in model.s_T:
                if (
                    model.v_L_Storage[storage_site, t].value
                    > model.p_sigma_Storage[storage_site].value
                ):
                    # Add first use to a dictionary
                    model.infrastructure_firstUse[storage_site] = t
                    # Get the lead time rounded up to the nearest full time period
                    model.infrastructure_leadTime[storage_site] = math.ceil(
                        model.p_tau_StorageExpansionLeadTime[i].value
                    )
                    break

    # Pipeline - "vb_y_Pipeline"
    pipeline_data = model.vb_y_Pipeline._data
    for i in pipeline_data:
        # Get site name from data
        pipeline = (i[0], i[1])
        # add values to output dictionary
        if (
            pipeline_data[i].value >= 1 - binary_epsilon
            and pipeline_data[i].value <= 1 + binary_epsilon
            and model.p_delta_Pipeline[i[2]].value > 0  # selected capacity is nonzero
        ):
            # determine first time period that site is used
            # pipeline is first used when water is sent in either direction of pipeline at a volume above the initial capacity
            for t in model.s_T:
                above_initial_capacity = False
                # if the pipeline is defined as bidirectional then the aggregated initial capacity is available in both directions
                if pipeline[::-1] in model.s_LLA:
                    initial_capacity = (
                        model.p_sigma_Pipeline[pipeline].value
                        + model.p_sigma_Pipeline[pipeline[::-1]].value
                    )
                    if (
                        model.v_F_Piped[pipeline, t].value > initial_capacity
                        or model.v_F_Piped[pipeline[::-1], t].value > initial_capacity
                    ):
                        above_initial_capacity = True
                else:
                    initial_capacity = model.p_sigma_Pipeline[pipeline].value
                    if model.v_F_Piped[pipeline, t].value > initial_capacity:
                        above_initial_capacity = True

                if above_initial_capacity:
                    # Add first use to a dictionary
                    model.infrastructure_firstUse[pipeline] = t
                    # Get the lead time rounded up to the nearest full time period

                    if model.config.pipeline_cost == PipelineCost.distance_based:
                        model.infrastructure_leadTime[pipeline] = math.ceil(
                            model.p_tau_PipelineExpansionLeadTime.value
                            * model.p_lambda_Pipeline[pipeline].value
                        )
                    elif model.config.pipeline_cost == PipelineCost.capacity_based:
                        # Pipelines lead time may only be defined in one direction
                        model.infrastructure_leadTime[pipeline] = math.ceil(
                            max(
                                model.p_tau_PipelineExpansionLeadTime[i].value,
                                model.p_tau_PipelineExpansionLeadTime[
                                    pipeline[::-1], i[2]
                                ].value,
                            )
                        )
                    break

    # Calculate start build for all infrastructure
    # Convert the ordered set to a list for easier use
    s_T_list = list(model.s_T)
    for key, value in model.infrastructure_firstUse.items():
        # Find the index of time period in the list
        finish_index = s_T_list.index(value)
        start_index = finish_index - model.infrastructure_leadTime[key]
        # if start time is within time horizon, report time period
        if start_index >= 0:
            model.infrastructure_buildStart[key] = model.s_T.at(start_index + 1)
        # if start time is prior to time horizon, report # time period prior to start
        else:
            if abs(start_index) > 1:
                plural = "s"
            else:
                plural = ""

            model.infrastructure_buildStart[key] = (
                str(abs(start_index))
                + " "
                + model.decision_period.to_string()
                + plural
                + " prior to "
                + model.s_T.first()
            )


def solve_discrete_water_quality(model, opt, scaled):
    # Discrete water quality method consists of 3 steps:
    # Step 1 - generate a feasible initial solution
    # Step 1a -- fix discrete water quality variables
    # Step 1b -- solve model, obtain optimal flows without considering quality
    # Step 1c -- fix or bound all non quality variables
    # Step 1d -- free discrete water quality variables
    # Step 1e -- solve model again for a feasible initial solution for discrete water quality
    # Step 2 - solve full discrete water quality
    # Step 2a -- free or remove bounds for all non quality variables
    # Step 2b -- call solver to solve whole model using previous solve as initial solution
    # Step 3 - Return solution

    # Step 1 - generate a feasible initial solution
    v_DQ = model.scaled_v_DQ if scaled else model.v_DQ
    # Step 1a - fix discrete water quality variables
    v_DQ.fix()
    # Step 1b - solve model, obtain optimal flows without considering quality
    opt.solve(model, tee=True)
    # Step 1c - fix or bound all non quality variables
    prefix = "scaled_" if scaled else ""
    discrete_variables_names = {
        prefix + "v_F_DiscretePiped",
        prefix + "v_F_DiscreteTrucked",
        prefix + "v_F_DiscreteDisposalDestination",
        prefix + "v_F_DiscreteFlowOutStorage",
        prefix + "v_L_DiscreteStorage",
        prefix + "v_F_DiscreteFlowTreatment",
        prefix + "v_F_DiscreteFlowOutNode",
        prefix + "v_F_DiscreteBRDestination",
        prefix + "v_F_DiscreteFlowCPIntermediate",
        prefix + "v_F_DiscreteFlowCPStorage",
        prefix + "v_L_DiscretePadStorage",
        prefix + "v_F_DiscreteFlowOutPadStorage",
        prefix + "v_F_DiscreteFlowInPadStorage",
        prefix + "v_F_DiscreteCPDestination",
        prefix + "v_Q_CompletionPad",
        prefix + "v_ObjectiveWithQuality",
    }
    for var in model.component_objects(Var):
        if var.name in discrete_variables_names:
            continue
        for index in var:
            index_var = var if index is None else var[index]
            value = index_var.value
            # Fix binary variables to their value and bound the continuous variables
            if index_var.domain is Binary:
                index_var.fix(round(value))
            else:
                index_var.setlb(0.99 * value)
                index_var.setub(1.01 * value)
    # Step 1d - free discrete water quality variables
    v_DQ.free()

    # Step 1e - solve model again for a feasible initial solution for discrete water quality
    print("\n")
    print("*" * 50)
    print(" " * 15, "Solving non-discrete water quality model")
    print("*" * 50)
    opt.solve(model, tee=True, warmstart=True)

    # Step 2 - solve full discrete water quality
    # Step 2a - free or remove bounds for all non quality variables
    for var in model.component_objects(Var):
        if var.name in discrete_variables_names:
            continue
        for index in var:
            index_var = var if index is None else var[index]
            value = index_var.value
            # unfix binary variables and unbound the continuous variables

            if index_var.domain is Binary:
                index_var.free()
            else:
                index_var.setlb(0)
                index_var.setub(None)

    # Step 2b - call solver to solve whole model using previous solve as initial solution
    print("\n")
    print("*" * 50)
    print(" " * 15, "Solving discrete water quality model")
    print("*" * 50)
    results = opt.solve(model, tee=True, warmstart=True)

    # Step 3 - Return solution
    return results


def solve_model(model, options=None):
    # default option values
    running_time = 60  # solver running time in seconds
    gap = 0  # solver gap
    deactivate_slacks = True  # yes/no to deactivate slack variables
    use_scaling = False  # yes/no to scale the model
    scaling_factor = 1000000  # scaling factor to apply to the model (only relevant if scaling is turned on)
    solver = ("gurobi_direct", "gurobi", "cbc")  # solvers to try and load in order
    gurobi_numeric_focus = 1

    # raise an exception if options is neither None nor a user-provided dictionary
    if options is not None and not isinstance(options, dict):
        raise Exception("options must either be None or a dictionary")

    # Override any default values with user-specified options
    if options is not None:
        if "running_time" in options.keys():
            running_time = options["running_time"]
        if "gap" in options.keys():
            gap = options["gap"]
        if "deactivate_slacks" in options.keys():
            deactivate_slacks = options["deactivate_slacks"]
        if "scale_model" in options.keys():
            # Note - we can't use "scale_model" as a local variable name because
            # that is the name of the function that is called later to apply
            # scaling to the model. So use "use_scaling" instead
            use_scaling = options["scale_model"]
        if "scaling_factor" in options.keys():
            scaling_factor = options["scaling_factor"]
        if "solver" in options.keys():
            solver = options["solver"]
        if "gurobi_numeric_focus" in options.keys():
            gurobi_numeric_focus = options["gurobi_numeric_focus"]

    # load pyomo solver
    opt = get_solver(*solver) if type(solver) is tuple else get_solver(solver)

    # set maximum running time for solver
    set_timeout(opt, timeout_s=running_time)

    # set solver gap
    if opt.type in ("gurobi_direct", "gurobi"):
        # Apply Gurobi specific options
        opt.options["mipgap"] = gap
        opt.options["NumericFocus"] = gurobi_numeric_focus
    elif opt.type in ("cbc"):
        # Apply CBC specific option
        opt.options["ratioGap"] = gap
    else:
        print("\nNot implemented passing gap for solver :%s\n" % opt.type)

    # deactivate slack variables if necessary
    if deactivate_slacks:
        model.v_C_Slack.fix(0)
        model.v_S_FracDemand.fix(0)
        model.v_S_Production.fix(0)
        model.v_S_Flowback.fix(0)
        model.v_S_PipelineCapacity.fix(0)
        model.v_S_StorageCapacity.fix(0)
        model.v_S_DisposalCapacity.fix(0)
        model.v_S_TreatmentCapacity.fix(0)
        model.v_S_BeneficialReuseCapacity.fix(0)

    if use_scaling:
        # Step 1: scale model
        scaled_model = scale_model(model, scaling_factor=scaling_factor)
        # Step 2: solve scaled mathematical model
        print("\n")
        print("*" * 50)
        print(" " * 15, "Solving scaled model")
        print("*" * 50)
        # Step 3: check model to be solved
        #       option 3.1 - full space model,
        #       option 3.2 - post process water quality,
        #       option 3.3 - discrete water quality,
        if model.config.water_quality is WaterQuality.discrete:
            # option 3.3:
            results = solve_discrete_water_quality(scaled_model, opt, scaled=True)
        elif model.config.water_quality is WaterQuality.post_process:
            # option 3.2:
            results = opt.solve(scaled_model, tee=True)
            if results.solver.termination_condition != TerminationCondition.infeasible:
                TransformationFactory("core.scale_model").propagate_solution(
                    scaled_model, model
                )
                model = postprocess_water_quality_calculation(model, opt)
        else:
            # option 3.1:
            results = opt.solve(scaled_model, tee=True)

        # Step 4: propagate scaled model results to original model
        if results.solver.termination_condition != TerminationCondition.infeasible:
            # if model is optimal propagate scaled model results to original model
            TransformationFactory("core.scale_model").propagate_solution(
                scaled_model, model
            )
    else:
        # Step 1: solve unscaled mathematical model
        print("\n")
        print("*" * 50)
        print(" " * 15, "Solving unscaled model")
        print("*" * 50)
        # Step 2: check model to be solved
        #       option 2.1 - full space model,
        #       option 2.2 - post process water quality,
        #       option 2.3 - discrete water quality,
        if model.config.water_quality is WaterQuality.discrete:
            # option 2.3:
            results = solve_discrete_water_quality(model, opt, scaled=False)
        elif model.config.water_quality is WaterQuality.post_process:
            # option 2.2:
            results = opt.solve(model, tee=True)
            if results.solver.termination_condition != TerminationCondition.infeasible:
                model = postprocess_water_quality_calculation(model, opt)
        else:
            # option 2.1:
            results = opt.solve(model, tee=True)

    if results.solver.termination_condition == TerminationCondition.infeasible:
        print(
            "WARNING: Model is infeasible. We recommend adding Slack variables to avoid infeasibilities\n, \
                however this is an indication that the input data should be revised. \
                This can be done by selecting 'deactivate_slacks': False in the options"
        )

    # For a given time t and beneficial reuse option o, if the beneficial reuse
    # minimum flow parameter is zero (p_sigma_BeneficialReuseMinimum[o, t] = 0)
    # and the optimal total flow to beneficial reuse is zero
    # (v_F_BeneficialReuseDestination[o, t] = 0), then it is arbitrary whether
    # the binary variable vb_y_BeneficialReuse[o, t] takes a value of 0 or 1. In
    # these cases it's preferred to report a value of 0 to the user, so change
    # the value of vb_y_BeneficialReuse[o, t] as necessary.
    for t in model.s_T:
        for o in model.s_O:
            if (
                value(model.p_sigma_BeneficialReuseMinimum[o, t]) < 1e-6
                and value(model.v_F_BeneficialReuseDestination[o, t]) < 1e-6
                and value(model.vb_y_BeneficialReuse[o, t] > 0)
            ):
                model.vb_y_BeneficialReuse[o, t].value = 0

    # post-process infrastructure buildout
    if model.config.infrastructure_timing == InfrastructureTiming.true:
        infrastructure_timing(model)

    results.write()

    if model.config.hydraulics != Hydraulics.false:
        model_h = pipeline_hydraulics(model)

        if model.config.hydraulics == Hydraulics.post_process:
            # In the post-process solve, only the hydraulics block is solved.

            mh = model_h.hydraulics
            # Calculate hydraulics. The following condition is used to avoid attribute error when
            # using gurobi_direct on hydraulics sub-block
            if opt.type == "gurobi_direct":
                results_2 = opt.solve(mh, tee=True, save_results=False)
            else:
                results_2 = opt.solve(mh, tee=True)

        elif model.config.hydraulics == Hydraulics.co_optimize:
            # Currently, this method is supported for only MINLP solvers accessed through GAMS.
            # The default solver is Baron and is set to find the first feasible solution.
            # If the user has SCIP, then the feasible solution from BARON is passed to SCIP, which is then solved to a gap of 0.3.
            # If the user do not have these solvers installed then it limits the use of co_optimize method at this time.
            # Ongoing work is geared to address this limitation and will soon be updated here.

            # Adding temporary variable bounds until the bounding method is implemented for the following Vars
            model_h.v_F_Piped.setub(1050)
            model_h.hydraulics.v_Pressure.setub(3.5e6)

            try:
                solver = SolverFactory("gams")
                mathoptsolver = "baron"
            except:
                print(
                    "Either GAMS or a license to BARON was not found. Please add GAMS to the path. If you do not have GAMS or BARON, \
                      please continue to use the post-process method for hydraulics at this time"
                )
            else:
                solver_options = {
                    "firstfeas": 1,
                }

                if not os.path.exists("temp"):
                    os.makedirs("temp")

                with open("temp/" + mathoptsolver + ".opt", "w") as f:
                    for k, v in solver_options.items():
                        f.write(str(k) + " " + str(v) + "\n")

                results_baron = solver.solve(
                    model_h,
                    tee=True,
                    keepfiles=True,
                    solver=mathoptsolver,
                    tmpdir="temp",
                    add_options=["gams_model.optfile=1;"],
                )
                try:
                    # second solve with SCIP
                    solver2 = SolverFactory("scip", solver_io="nl")
                    print("  ")
                    print(
                        "WARNING: A default relative optimality gap of 30%/ is set to obtain good solutions at this time"
                    )
                    print("  ")
                except:
                    print(
                        "A second solve with SCIP cannot be executed as SCIP was not found. Please add it to Path. \
                          If you do not haev SCIP, proceed with caution when using solution obtain from first solve using BARON"
                    )
                else:
                    results_2 = solver2.solve(
                        model_h, options={"limits/gap": 0.3}, tee=True
                    )

        # Once the hydraulics block is solved, it is deactivated to retain the original MILP
        model_h.hydraulics.deactivate()

        results_2.write()
    return results
