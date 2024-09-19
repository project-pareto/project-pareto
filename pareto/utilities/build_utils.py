#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2024 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################
"""
Module with build utility functions for strategic and operational models.

Authors: PARETO Team
"""

from pyomo.environ import Set, Param
from pareto.utilities.process_data import (
    get_valid_piping_arc_list,
    get_valid_trucking_arc_list,
)


def build_sets(model):
    """Build sets for operational and strategic models."""

    # Build sets which are common to operational and strategic models
    model.s_T = Set(
        initialize=model.df_sets["TimePeriods"], doc="Time Periods", ordered=True
    )
    model.s_PP = Set(initialize=model.df_sets["ProductionPads"], doc="Production Pads")
    model.s_CP = Set(
        initialize=model.df_sets["CompletionsPads"], doc="Completions Pads"
    )
    model.s_P = Set(initialize=(model.s_PP | model.s_CP), doc="Pads")
    model.s_F = Set(
        initialize=model.df_sets["ExternalWaterSources"], doc="External Water Sources"
    )
    model.s_K = Set(initialize=model.df_sets["SWDSites"], doc="Disposal Sites")
    model.s_S = Set(initialize=model.df_sets["StorageSites"], doc="Storage Sites")
    model.s_R = Set(initialize=model.df_sets["TreatmentSites"], doc="Treatment Sites")
    model.s_O = Set(initialize=model.df_sets["ReuseOptions"], doc="Reuse Options")
    model.s_N = Set(initialize=model.df_sets["NetworkNodes"], doc="Network Nodes")
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
    model.s_QC = Set(
        initialize=model.df_sets["WaterQualityComponents"],
        doc="Water Quality Components",
    )

    # Build dictionary of all specified piping arcs
    piping_arc_types = get_valid_piping_arc_list()
    model.df_parameters["LLA"] = {}
    for arctype in piping_arc_types:
        if arctype in model.df_parameters:
            model.df_parameters["LLA"].update(model.df_parameters[arctype])
    model.s_LLA = Set(
        initialize=list(model.df_parameters["LLA"].keys()), doc="Valid Piping Arcs"
    )

    # Build dictionary of all specified trucking arcs
    trucking_arc_types = get_valid_trucking_arc_list()
    model.df_parameters["LLT"] = {}
    for arctype in trucking_arc_types:
        if arctype in model.df_parameters:
            model.df_parameters["LLT"].update(model.df_parameters[arctype])
    model.s_LLT = Set(
        initialize=list(model.df_parameters["LLT"].keys()), doc="Valid Trucking Arcs"
    )

    # Build sets specific to operational model
    if model.type == "operational":
        model.s_A = Set(
            initialize=model.df_sets["ProductionTanks"], doc="Production Tanks"
        )
        model.s_D = Set(initialize=["D0"], doc="Pipeline diameters")
        model.s_C = Set(initialize=["C0"], doc="Storage capacities")
        model.s_I = Set(initialize=["I0"], doc="Injection (i.e. disposal) capacities")

    # Build sets specific to strategic model
    if model.type == "strategic":
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
            initialize=model.df_sets["TreatmentTechnologies"],
            doc="Treatment Technologies",
        )
        model.s_AC = Set(
            initialize=model.df_sets["AirEmissionsComponents"],
            doc="Air emission components",
        )


def build_params(model):
    """Build parameters common to operational and strategic models."""
    node_type = {
        "P": "PP",
        "C": "CP",
        "N": "N",
        "K": "K",
        "S": "S",
        "R": "R",
        "O": "O",
        "F": "F",
    }
    node_description = {
        "P": "production",
        "C": "completions",
        "N": "node",
        "K": "disposal",
        "S": "storage",
        "R": "treatment",
        "O": "reuse",
        "F": "externally sourced water",
    }
    transport_description = {
        "A": "piping",
        "T": "trucking",
    }

    # Build Params for all arc types
    arc_types = get_valid_piping_arc_list() + get_valid_trucking_arc_list()
    for at in arc_types:
        # at is a string of the form "XYZ", where X and Y are node types and Z
        # is either A for piping or T for trucking
        setattr(
            model,
            "p_" + at,  # e.g., p_PCA
            Param(
                getattr(model, "s_" + node_type[at[0]]),  # e.g., model.s_PP
                getattr(model, "s_" + node_type[at[1]]),  # e.g., model.s_CP
                default=0,
                initialize=model.df_parameters.get(at, {}),
                doc=f"Valid {node_description[at[0]]}-to-{node_description[at[1]]} {transport_description[at[2]]} arcs",
            ),
        )
