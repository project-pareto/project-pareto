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

from pyomo.environ import (
    Set,
    Param,
    units as pyunits,
    value,
    NonNegativeReals,
    Var,
    Binary,
)
from pareto.utilities.process_data import (
    get_valid_piping_arc_list,
    get_valid_trucking_arc_list,
)
from pareto.utilities.enums import (
    ProdTank,
    Hydraulics,
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


def build_common_params(model):
    """Build parameters common to operational and strategic models."""

    # Define dictionaries used to build arc Params
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

    # p_beta_Production and p_beta_Flowback are the same in the strategic and
    # operational models if the operational model is using equalized production
    # tanks.
    if model.type == "strategic" or (
        model.type == "operational"
        and model.config.production_tanks == ProdTank.equalized
    ):
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
    else:  # Operational model with individual production tanks
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
        model.p_beta_Flowback = Param(
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
                for key, value in model.df_parameters["TankFlowbackRates"].items()
            },
            units=model.model_units["volume_time"],
            doc="Flowback supply forecast for a completions pad [volume/time]",
        )

    # Some parameters are only slightly different between the operational and
    # strategic models, e.g., the tab name used for initialization.
    if model.type == "strategic":
        p_sigma_Pipeline_init = {
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["InitialPipelineCapacity"].items()
        }
        p_sigma_Disposal_tabname = "InitialDisposalCapacity"
        p_sigma_Storage_init = {
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume"],
                to_units=model.model_units["volume"],
            )
            for key, value in model.df_parameters["InitialStorageCapacity"].items()
        }
        p_lambda_Storage_init = {
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume"],
                to_units=model.model_units["volume"],
            )
            for key, value in model.df_parameters["InitialStorageLevel"].items()
        }
        p_pi_Storage_init = {
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in model.df_parameters["StorageCost"].items()
        }
        p_rho_Storage_init = {
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in model.df_parameters["StorageWithdrawalRevenue"].items()
        }
        p_sigma_PadStorage_idx = (model.s_CP,)
        p_sigma_Treatment_idx = (model.s_R, model.s_WT)
        p_sigma_Treatment_tabname = "InitialTreatmentCapacity"
        p_epsilon_Treatment_idx = (model.s_R, model.s_WT)
        p_pi_Treatment_idx = (model.s_R, model.s_WT)
    else:  # operational model
        p_sigma_Pipeline_init = {}
        p_sigma_Disposal_tabname = "DisposalCapacity"
        p_sigma_Storage_init = {}
        p_lambda_Storage_init = {}
        p_pi_Storage_init = {}
        p_rho_Storage_init = {}
        p_sigma_PadStorage_idx = (model.s_CP, model.s_T)
        p_sigma_Treatment_idx = (model.s_R,)
        p_sigma_Treatment_tabname = "TreatmentCapacity"
        p_epsilon_Treatment_idx = (model.s_R, model.s_QC)
        p_pi_Treatment_idx = (model.s_R,)

    model.p_sigma_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=0,
        initialize=p_sigma_Pipeline_init,
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
            for key, value in model.df_parameters[p_sigma_Disposal_tabname].items()
        },
        units=model.model_units["volume_time"],
        doc="Initial disposal capacity at disposal sites [volume/time]",
    )

    model.p_sigma_Storage = Param(
        model.s_S,
        default=0,
        initialize=p_sigma_Storage_init,
        units=model.model_units["volume"],
        doc="Initial storage capacity at storage site [volume]",
    )

    model.p_sigma_ExternalWater = Param(
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
                "ExtWaterSourcingAvailability"
            ].items()
        },
        units=model.model_units["volume_time"],
        doc="Externally sourced water capacity [volume/time]",
        mutable=True,
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
        mutable=True,
    )

    model.p_sigma_OffloadingStorage = Param(
        model.s_S,
        default=pyunits.convert_value(
            9999,
            from_units=pyunits.koil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        initialize={},
        units=model.model_units["volume_time"],
        doc="Truck offloading capacity per pad [volume/time]",
        mutable=True,
    )

    model.p_sigma_ProcessingStorage = Param(
        model.s_S,
        default=pyunits.convert_value(
            9999,
            from_units=pyunits.koil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        initialize={},
        units=model.model_units["volume_time"],
        doc="Processing (e.g. clarification) capacity per storage site [volume/time]",
        mutable=True,
    )

    model.p_delta_Truck = Param(
        default=pyunits.convert_value(
            110, from_units=pyunits.oil_bbl, to_units=model.model_units["volume"]
        ),
        units=model.model_units["volume"],
        doc="Truck capacity [volume]",
    )

    # It is expected that the units for p_tau_trucking are hours, which usually
    # differs from the time units used for flow rates, e.g., day, week, month.
    # Therefore, for the sake of simplicity, no units are defined for
    # p_tau_trucking, as the hr units will cancel out with the units in
    # model.p_pi_Trucking which is the hourly cost of trucking.
    model.p_tau_Trucking = Param(
        model.s_L,
        model.s_L,
        default=12,
        initialize=model.df_parameters["TruckingTime"],
        mutable=True,
        doc="Drive time between locations [hr]",
    )

    model.p_lambda_Storage = Param(
        model.s_S,
        default=0,
        initialize=p_lambda_Storage_init,
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
        default=(
            max(DisposalOperationalCost_convert_to_model.values()) * 100
            if DisposalOperationalCost_convert_to_model
            else pyunits.convert_value(
                25,
                from_units=pyunits.USD / pyunits.oil_bbl,
                to_units=model.model_units["currency_volume"],
            )
        ),
        initialize=DisposalOperationalCost_convert_to_model,
        units=model.model_units["currency_volume"],
        doc="Disposal operational cost [currency/volume]",
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
        default=(
            max(ReuseOperationalCost_convert_to_model.values()) * 100
            if ReuseOperationalCost_convert_to_model
            else pyunits.convert_value(
                25,
                from_units=pyunits.USD / pyunits.oil_bbl,
                to_units=model.model_units["currency_volume"],
            )
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
        initialize=p_pi_Storage_init,
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
        initialize=p_rho_Storage_init,
        units=model.model_units["currency_volume"],
        doc="Storage withdrawal operational credit [currency/volume]",
    )

    if model.type == "strategic" and model.config.hydraulics != Hydraulics.false:
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

    if model.type == "strategic" and model.config.hydraulics == Hydraulics.post_process:
        # In the post-process based hydraulics model an economics-based penalty
        # is added to moderate flow through pipelines based on the elevation
        # change.
        p_pi_Pipeline_init = {}
        max_elevation = max([val for val in model.df_parameters["Elevation"].values()])
        min_elevation = min([val for val in model.df_parameters["Elevation"].values()])
        max_elevation_change = max_elevation - min_elevation
        # Set economic penalties for pipeline operational cost based on the
        # elevation changes.
        for k1 in model.s_L:
            for k2 in model.s_L:
                if (k1, k2) in model.s_LLA:
                    elevation_delta = value(model.p_zeta_Elevation[k1]) - value(
                        model.p_zeta_Elevation[k2]
                    )
                    p_pi_Pipeline_init[(k1, k2)] = max(
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
        p_pi_Pipeline_init = model.df_parameters["PipelineOperationalCost"]

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
            for key, value in p_pi_Pipeline_init.items()
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
    # For p_pi_trucking, only currency units are defined, as the hourly rate is
    # canceled out with the trucking time units from parameter p_Tau_Trucking.
    # This is to avoid adding an extra unit for time which may be confusing.
    model.p_pi_Trucking = Param(
        model.s_L,
        default=(
            max(TruckingHourlyCost_convert_to_model.values()) * 100
            if TruckingHourlyCost_convert_to_model
            else pyunits.convert_value(
                15000,
                from_units=pyunits.USD,
                to_units=model.model_units["currency"],
            )
        ),
        initialize=TruckingHourlyCost_convert_to_model,
        units=model.model_units["currency"],
        doc="Trucking hourly cost (by source) [currency/hr]",
    )

    ExternalSourcingCost_convert_to_model = {
        key: pyunits.convert_value(
            value,
            from_units=model.user_units["currency_volume"],
            to_units=model.model_units["currency_volume"],
        )
        for key, value in model.df_parameters["ExternalSourcingCost"].items()
    }
    model.p_pi_Sourcing = Param(
        model.s_F,
        default=(
            max(ExternalSourcingCost_convert_to_model.values()) * 100
            if ExternalSourcingCost_convert_to_model
            else pyunits.convert_value(
                150,
                from_units=pyunits.USD / pyunits.oil_bbl,
                to_units=model.model_units["currency_volume"],
            )
        ),
        initialize=ExternalSourcingCost_convert_to_model,
        units=model.model_units["currency_volume"],
        doc="Externally sourced water cost [currency/volume]",
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

    model.p_psi_FracDemand = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/(volume/time)]",
    )

    model.p_psi_Production = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/(volume/time)]",
    )

    model.p_psi_Flowback = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/(volume/time)]",
    )

    model.p_psi_PipelineCapacity = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/(volume/time)]",
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
        doc="Slack cost parameter [currency/(volume/time)]",
    )

    model.p_psi_TreatmentCapacity = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/(volume/time)]",
    )

    model.p_psi_BeneficialReuseCapacity = Param(
        default=pyunits.convert_value(
            99999,
            from_units=pyunits.USD / (pyunits.koil_bbl / pyunits.week),
            to_units=model.model_units["currency_volume_time"],
        ),
        units=model.model_units["currency_volume_time"],
        doc="Slack cost parameter [currency/(volume/time)]",
    )

    model.p_sigma_PadStorage = Param(
        *p_sigma_PadStorage_idx,
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
        *p_sigma_Treatment_idx,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters[p_sigma_Treatment_tabname].items()
        },
        units=model.model_units["volume_time"],
        doc="Initial treatment capacity at treatment site [volume/time]",
    )

    model.p_epsilon_Treatment = Param(
        *p_epsilon_Treatment_idx,
        default=1.0,
        initialize=model.df_parameters["TreatmentEfficiency"],
        mutable=True,
        doc="Treatment efficiency [%]",
    )

    model.p_pi_Treatment = Param(
        *p_pi_Treatment_idx,
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


def build_common_vars(model):
    """Build variables common to operational and strategic models."""

    # Some variables are only slightly different between the operational and
    # strategic models, e.g., the tab name used for initialization.
    if model.type == "strategic":
        v_C_Piped_idx = (model.s_L, model.s_L, model.s_T)
        v_C_Trucked_idx = (model.s_L, model.s_L, model.s_T)
        v_F_Capacity_idx = (model.s_L, model.s_L)
        v_S_PipelineCapacity_idx = (model.s_L, model.s_L)
        vb_y_Flow_idx = (model.s_L, model.s_L, model.s_T)
    else:  # operational model
        v_C_Piped_idx = (model.s_LLA, model.s_T)
        v_C_Trucked_idx = (model.s_LLT, model.s_T)
        v_F_Capacity_idx = (model.s_LLA,)
        v_S_PipelineCapacity_idx = (model.s_LLA,)
        vb_y_Flow_idx = (model.s_LLA, model.s_T)

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
        doc="Externally sourced water from source f to completions pad p [volume/time]",
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

    model.v_F_TotalSourced = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume of externally sourced water [volume]",
    )

    model.v_C_Piped = Var(
        *v_C_Piped_idx,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Cost of piping produced water from location l to location l [currency/time]",
    )

    model.v_C_Trucked = Var(
        *v_C_Trucked_idx,
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
        doc="Cost of externally sourced water from source f to completion pad p [currency/time]",
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
        doc="Total cost of externally sourced water [currency]",
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
        doc="Total deliveries to Beneficial Reuse Option [volume/time]",
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
        *v_F_Capacity_idx,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Flow capacity along pipeline arc [volume/time]",
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
        doc="Slack variable to process flowback water production [volume/time]",
    )

    model.v_S_PipelineCapacity = Var(
        *v_S_PipelineCapacity_idx,
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

    # Binary variables
    model.vb_y_Flow = Var(
        *vb_y_Flow_idx,
        within=Binary,
        initialize=0,
        doc="Directional flow between two locations",
    )
