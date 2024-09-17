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

from pyomo.environ import Set
from pareto.utilities.process_data import (
    get_valid_piping_arc_list,
    get_valid_trucking_arc_list,
)

def define_sets(model):
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
        initialize=model.df_sets["WaterQualityComponents"], doc="Water Quality Components",
    )

    if model.type == "operational":
        model.s_A = Set(initialize=model.df_sets["ProductionTanks"], doc="Production Tanks")
        model.s_D = Set(initialize=["D0"], doc="Pipeline diameters")
        model.s_C = Set(initialize=["C0"], doc="Storage capacities")
        model.s_I = Set(initialize=["I0"], doc="Injection (i.e. disposal) capacities")

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
            initialize=model.df_sets["TreatmentTechnologies"], doc="Treatment Technologies"
        )
        model.s_A = Set(
            initialize=model.df_sets["AirEmissionsComponents"],
            doc="Air emission components",
        )  # TODO change s_A to something else in strategic model to avoid name clash with production tanks in operational model

    # Build dictionary of all specified piping arcs
    piping_arc_types = get_valid_piping_arc_list(model.type)
    model.df_parameters["LLA"] = {}
    for arctype in piping_arc_types:
        if arctype in model.df_parameters:
            model.df_parameters["LLA"].update(model.df_parameters[arctype])
    model.s_LLA = Set(
        initialize=list(model.df_parameters["LLA"].keys()), doc="Valid Piping Arcs"
    )

    # Build dictionary of all specified trucking arcs
    trucking_arc_types = get_valid_trucking_arc_list(model.type)
    model.df_parameters["LLT"] = {}
    for arctype in trucking_arc_types:
        if arctype in model.df_parameters:
            model.df_parameters["LLT"].update(model.df_parameters[arctype])
    model.s_LLT = Set(
        initialize=list(model.df_parameters["LLT"].keys()), doc="Valid Trucking Arcs"
    )
