#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2025 by the software owners:
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
Module to process data from get_data.py and provide helpful feedback to users if input data is
insufficient or infeasible.

This module includes error handling for missing data, warnings for missing non-essential data, and
basic infeasibility testing.

Authors: PARETO Team
"""
# Imports
import warnings
from pareto.utilities.get_data import (
    get_valid_input_set_tab_names,
    get_valid_input_parameter_tab_names,
)
from pyomo.environ import Expression, value


def get_valid_trucking_arc_list():
    """Returns a list of all valid trucking arcs."""
    return [
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


def get_valid_piping_arc_list():
    """Returns a list of all valid piping arcs."""
    return [
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
        "ROA",
        "SNA",
        "SCA",
        "SKA",
        "SRA",
        "SOA",
    ]


# Process the input data (df_sets, df_parameters) from get_data.py.
# Raise errors and warnings for missing data and infeasibilities.
def check_required_data(df_sets, df_parameters, config, model_type="strategic"):
    # Import config option classes here instead of at the top of this module to
    # avoid circular imports
    from pareto.strategic_water_management.strategic_produced_water_optimization import (
        WaterQuality,
        PipelineCost,
        Hydraulics,
        PipelineCapacity,
        InfrastructureTiming,
        DesalinationModel,
        SubsurfaceRisk,
        Objectives,
    )

    # Create a list to hold all missing data that causes an error
    data_error_items = []

    # Check that input data contains all minimally required data
    # Tab names for required Sets.
    # Currently there are no required stand alone sets,
    # but tab names can be added to this list if required sets are added.
    set_list_min_required = []

    # Tab names for required Parameters
    parameter_list_min_required = [
        "Units",
    ]

    # Tab names for parameters. For each list in the list, at least one Parameter tab is required.
    set_list_require_at_least_one = [
        ["ProductionPads", "CompletionsPads", "ExternalWaterSources"],  # water sources
        ["CompletionsPads", "SWDSites", "ReuseOptions", "StorageSites"],  # water sinks
    ]

    # Tab names for parameters. For each tuple in the list, at least one Parameter tab is required.
    param_list_require_at_least_one = []

    # Check that Set list contains required Set tabs
    for set_name in set_list_min_required:
        if set_name not in df_sets.keys():
            data_error_items.append(set_name)

    # Check that Parameter list contains required Parameter tabs
    for param in parameter_list_min_required:
        if param not in df_parameters.keys():
            data_error_items.append(param)

    # Check that Set list contains at least one Set tab for each group of Set
    for set_list in set_list_require_at_least_one:
        # Check that there is at least one of set names in tuple in the data
        if len(set(set_list) & set(df_sets.keys())) < 1:
            data_error_items.append("One of tabs " + str(set_list))

    # Check that Parameter list contains at least one Parameter tab for each group of parameters
    for param_list in param_list_require_at_least_one:
        # Check that there is at least one of set names in tuple in the data
        if len(set(param_list) & set(df_parameters.keys())) < 1:
            data_error_items.append("One of tabs " + str(param_list))

    # Required Data for Configurations
    # Note: no config check needed for RemovalEfficiency. This tab is always required when TreatmentSites are in the model.

    # Hydraulics config - check needed data
    hydraulics_config_errors = _check_config_dependent_data(
        df_sets,
        df_parameters,
        config.hydraulics,
        config_required_sets={
            Hydraulics.false: [],
            Hydraulics.post_process: [],
            Hydraulics.co_optimize: [],
            Hydraulics.co_optimize_linearized: [],
        },
        config_required_params={
            Hydraulics.false: [],
            Hydraulics.post_process: [
                "Hydraulics",
                "Elevation",
                "WellPressure",
                "InitialPipelineDiameters",
                "PipelineDiameterValues",
            ],
            Hydraulics.co_optimize: [
                "Hydraulics",
                "Elevation",
                "WellPressure",
                "InitialPipelineDiameters",
                "PipelineDiameterValues",
            ],
            Hydraulics.co_optimize_linearized: [
                "Hydraulics",
                "Elevation",
                "WellPressure",
                "InitialPipelineDiameters",
                "PipelineDiameterValues",
            ],
        },
    )
    data_error_items.extend(hydraulics_config_errors)

    # Desalination model config - check needed data
    desalination_config_errors = _check_config_dependent_data(
        df_sets,
        df_parameters,
        config.desalination_model,
        config_required_sets={
            DesalinationModel.false: [],
            DesalinationModel.mvc: [],
            DesalinationModel.md: [],
        },
        config_required_params={
            DesalinationModel.false: [],
            DesalinationModel.mvc: ["DesalinationSurrogate"],
            DesalinationModel.md: ["DesalinationSurrogate"],
        },
    )
    data_error_items.extend(desalination_config_errors)

    # Pipeline cost config - check needed data
    pipeline_cost_config_errors = _check_config_dependent_data(
        df_sets,
        df_parameters,
        config.pipeline_cost,
        config_required_sets={
            PipelineCost.distance_based: [],
            PipelineCost.capacity_based: [],
        },
        config_required_params={
            PipelineCost.distance_based: [
                "PipelineCapexDistanceBased",
                "PipelineExpansionDistance",
                "PipelineDiameterValues",
            ],
            PipelineCost.capacity_based: ["PipelineCapexCapacityBased"],
        },
    )
    data_error_items.extend(pipeline_cost_config_errors)

    # Pipeline capacity config - check needed data
    pipeline_capacity_config_errors = _check_config_dependent_data(
        df_sets,
        df_parameters,
        config.pipeline_capacity,
        config_required_sets={
            PipelineCapacity.input: [],
            PipelineCapacity.calculated: [],
        },
        config_required_params={
            PipelineCapacity.input: ["PipelineCapacityIncrements"],
            PipelineCapacity.calculated: ["Hydraulics", "PipelineDiameterValues"],
        },
    )
    data_error_items.extend(pipeline_capacity_config_errors)

    # Node capacity config - check needed data
    node_capacity_config_errors = _check_config_dependent_data(
        df_sets,
        df_parameters,
        config.node_capacity,
        config_required_sets={
            True: [],
            False: [],
        },
        config_required_params={
            True: ["NodeCapacities"],
            False: [],
        },
    )
    data_error_items.extend(node_capacity_config_errors)

    # Subsurface Risk config - check needed data
    subsurface_risk_config_errors = _check_config_dependent_data(
        df_sets,
        df_parameters,
        config.subsurface_risk,
        config_required_sets={
            SubsurfaceRisk.false: [],
            SubsurfaceRisk.exclude_over_and_under_pressured_wells: [],
            SubsurfaceRisk.calculate_risk_metrics: [],
        },
        config_required_params={
            SubsurfaceRisk.false: [],
            SubsurfaceRisk.exclude_over_and_under_pressured_wells: [
                "SWDProxPAWell",
                "SWDProxInactiveWell",
                "SWDProxEQ",
                "SWDProxFault",
                "SWDProxHpOrLpWell",
                "SWDDeep",
                "SWDAveragePressure",
                "SWDRiskFactors",
            ],
            SubsurfaceRisk.calculate_risk_metrics: [
                "SWDProxPAWell",
                "SWDProxInactiveWell",
                "SWDProxEQ",
                "SWDProxFault",
                "SWDProxHpOrLpWell",
                "SWDDeep",
                "SWDAveragePressure",
                "SWDRiskFactors",
            ],
        },
    )
    data_error_items.extend(subsurface_risk_config_errors)

    # Objective config - check needed data
    objectives_config_errors = _check_config_dependent_data(
        df_sets,
        df_parameters,
        config.objective,
        config_required_sets={
            Objectives.cost: [],
            Objectives.reuse: [],
            Objectives.subsurface_risk: [],
            Objectives.cost_surrogate: [],
            Objectives.environmental: [],
        },
        config_required_params={
            Objectives.cost: [],
            Objectives.reuse: [],
            Objectives.subsurface_risk: [
                "SWDProxPAWell",
                "SWDProxInactiveWell",
                "SWDProxEQ",
                "SWDProxFault",
                "SWDProxHpOrLpWell",
                "SWDDeep",
                "SWDAveragePressure",
                "SWDRiskFactors",
            ],
            Objectives.cost_surrogate: ["DesalinationSurrogate"],
            Objectives.environmental: [
                "AirEmissionCoefficients",
                "TreatmentEmissionCoefficients",
            ],
        },
    )
    data_error_items.extend(objectives_config_errors)

    # Water Quality config - check needed data.
    water_quality_config_errors = _check_config_dependent_data(
        df_sets,
        df_parameters,
        config.water_quality,
        config_required_sets={
            WaterQuality.false: [],
            WaterQuality.post_process: ["WaterQualityComponents"],
            WaterQuality.discrete: ["WaterQualityComponents"],
        },
        config_required_params={
            WaterQuality.false: [],
            WaterQuality.post_process: [],
            WaterQuality.discrete: [],
        },
    )
    data_error_items.extend(water_quality_config_errors)

    # If either post_process or discrete config option is selected for water
    # quality, then additional data may be needed, depending on what node types
    # are used in the system. For example, If external water sources are used,
    # external water quality is needed.
    if (
        config.water_quality is WaterQuality.discrete
        or config.water_quality is WaterQuality.post_process
    ):
        # Check if storage sites are given. If so, check for storage initial water quality.
        (df_sets, df_parameters) = _check_optional_data(
            df_sets,
            df_parameters,
            optional_set_name="StorageSites",
            required_sets_with_option={},
            required_parameters_with_option={"StorageInitialWaterQuality"},
            requires_at_least_one=[],
        )
        # Check if external water sources are given. If so, check for external water source quality.
        (df_sets, df_parameters) = _check_optional_data(
            df_sets,
            df_parameters,
            optional_set_name="ExternalWaterSources",
            required_sets_with_option={},
            required_parameters_with_option={"ExternalWaterQuality"},
            requires_at_least_one=[],
        )
        # Check if production pads are given. If so, check for production pad water quality.
        (df_sets, df_parameters) = _check_optional_data(
            df_sets,
            df_parameters,
            optional_set_name="ProductionPads",
            required_sets_with_option={},
            required_parameters_with_option={"PadWaterQuality"},
            requires_at_least_one=[],
        )
        # Check if completions pads are given. If so, check for completions pad water quality.
        (df_sets, df_parameters) = _check_optional_data(
            df_sets,
            df_parameters,
            optional_set_name="CompletionsPads",
            required_sets_with_option={},
            required_parameters_with_option={"PadWaterQuality"},
            requires_at_least_one=[],
        )

    if config.infrastructure_timing is InfrastructureTiming.true:
        # Check if disposal capex is considered. If so, check for lead time.
        (df_sets, df_parameters) = _check_optional_data(
            df_sets,
            df_parameters,
            optional_set_name="InjectionCapacities",
            required_sets_with_option={},
            required_parameters_with_option={"DisposalExpansionLeadTime"},
            requires_at_least_one=[],
        )

        # Check if treatment capex is considered. If so, check for lead time.
        (df_sets, df_parameters) = _check_optional_data(
            df_sets,
            df_parameters,
            optional_set_name="TreatmentCapacities",
            required_sets_with_option={},
            required_parameters_with_option={"TreatmentExpansionLeadTime"},
            requires_at_least_one=[],
        )

        # Check if storage capex is considered. If so, check for lead time.
        (df_sets, df_parameters) = _check_optional_data(
            df_sets,
            df_parameters,
            optional_set_name="StorageCapacities",
            required_sets_with_option={},
            required_parameters_with_option={"StorageExpansionLeadTime"},
            requires_at_least_one=[],
        )

        # Check if pipeline capex is considered. Check for relevant lead time type.
        if config.pipeline_cost is PipelineCost.distance_based:
            (df_sets, df_parameters) = _check_optional_data(
                df_sets,
                df_parameters,
                optional_set_name="PipelineDiameters",
                required_sets_with_option={},
                required_parameters_with_option={"PipelineExpansionLeadTime_Dist"},
                requires_at_least_one=[],
            )
        elif config.pipeline_cost is PipelineCost.capacity_based:
            (df_sets, df_parameters) = _check_optional_data(
                df_sets,
                df_parameters,
                optional_set_name="PipelineDiameters",
                required_sets_with_option={},
                required_parameters_with_option={"PipelineExpansionLeadTime_Capac"},
                requires_at_least_one=[],
            )

    # If there are config errors to raise, raise them.
    if len(data_error_items) > 0:
        error_message = ", ".join(data_error_items)
        raise MissingDataError(
            "Essential data is incomplete. Please add the following missing data tabs: "
            + error_message
        )

    # Optional Data: If data is not given, create empty dictionaries and raise a warning to the user

    # CompletionsPads. If given, check for additional data required to consider CompletionsPads in the model.
    # Call _check_optional_data function. This returns modified df_sets and df_parameters that
    # include empty dictionaries for missing data, so the parameters can be defined without error
    # when building the PARETO model.
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="CompletionsPads",
        required_sets_with_option={},
        required_parameters_with_option={
            "CompletionsDemand",
            "FlowbackRates",
            "CompletionsPadOutsideSystem",
            "PadOffloadingCapacity",
        },
        requires_at_least_one=[
            [
                "CNA",
                "CCA",
                "CST",
                "CCT",
                "CKT",
                "CRT",
            ],  # arc to remove flowback water
            [
                "NCA",
                "FCA",
                "RCA",
                "PCA",
                "CCA",
                "SCA",
                "FCT",
                "PCT",
                "CCT",
                "SCT",
            ],  # arc to meet completions demand
        ],
    )

    # ProductionPads
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="ProductionPads",
        required_sets_with_option={},
        required_parameters_with_option={"PadRates"},
        requires_at_least_one=[
            ["PCA", "PNA", "PPA", "PCT", "PKT", "PST", "PRT", "POT"]
        ],
    )

    # SWDs
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="SWDSites",
        required_sets_with_option={},
        required_parameters_with_option={
            "InitialDisposalCapacity",
            "DisposalOperationalCost",
            "DisposalOperatingCapacity",
            "CompletionsPadStorage",
        },
        requires_at_least_one=[["NKA", "SKA", "RKA", "PKT", "CKT", "SKT", "RKT"]],
    )

    # Treatment Sites.
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="TreatmentSites",
        required_sets_with_option={"TreatmentTechnologies"},
        required_parameters_with_option={
            "InitialTreatmentCapacity",
            "TreatmentOperationalCost",
            "DesalinationTechnologies",
            "DesalinationSites",
            "TreatmentEfficiency",
            "RemovalEfficiency",
        },
        requires_at_least_one=[
            ["RNA", "RSA", "RKA", "ROA", "RCA", "RST", "ROT", "RKT"],
            ["PRT", "CRT", "NRA", "SRA"],
        ],
    )

    # Beneficial Reuse
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="ReuseOptions",
        required_sets_with_option={},
        required_parameters_with_option={
            "BeneficialReuseCost",
            "BeneficialReuseCredit",
            "ReuseMinimum",
            "ReuseCapacity",
            "ReuseOperationalCost",
        },
        requires_at_least_one=[["ROA", "SOA", "NOA", "ROT", "SOT", "POT"]],
    )

    # StorageSites
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="StorageSites",
        required_sets_with_option={},
        required_parameters_with_option={
            "InitialStorageCapacity",
            "InitialStorageLevel",
            "StorageCost",
            "StorageWithdrawalRevenue",
        },
        requires_at_least_one=[
            ["SOA", "SNA", "SCA", "SKA", "SRA", "SCT", "SKT", "SOT"],
            ["NSA", "RSA", "CST", "RST", "PST"],
        ],
    )

    # FreshwaterSources
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="ExternalWaterSources",
        required_sets_with_option={},
        required_parameters_with_option={
            "ExtWaterSourcingAvailability",
            "ExternalSourcingCost",
        },
        requires_at_least_one=[
            ["FCA", "FCT"],
        ],
    )

    # NetworkNodes
    piping_arcs = get_valid_piping_arc_list()
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="NetworkNodes",
        required_sets_with_option={},
        required_parameters_with_option={},
        requires_at_least_one=[piping_arcs],
    )

    # Treatment Capacity Expansion
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="TreatmentCapacities",
        required_sets_with_option={},
        required_parameters_with_option={
            "TreatmentExpansionCost",
            "TreatmentCapacityIncrements",
        },
        requires_at_least_one=[],
    )

    # Disposal Capacity Expansion
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="InjectionCapacities",
        required_sets_with_option={},
        required_parameters_with_option={
            "DisposalExpansionCost",
            "DisposalCapacityIncrements",
        },
        requires_at_least_one=[],
    )

    # Storage Capacity Expansion
    (df_sets, df_parameters) = _check_optional_data(
        df_sets,
        df_parameters,
        optional_set_name="StorageCapacities",
        required_sets_with_option={},
        required_parameters_with_option={
            "StorageExpansionCost",
            "StorageCapacityIncrements",
        },
        requires_at_least_one=[],
    )

    # Trucking is optional, but if trucking arcs are included, relevant parameters are required
    trucking_parameters = ["TruckingTime", "TruckingHourlyCost"]
    trucking_arcs = get_valid_trucking_arc_list()

    if len(set(trucking_arcs) & set(df_parameters)) > 0:
        # Check that Parameter list contains trucking Parameter tabs
        missing_trucking_data = set(trucking_parameters) - set(df_parameters)
        if len(missing_trucking_data) > 0:
            # Add empty dictionary to df_parameters
            for s in missing_trucking_data:
                df_parameters[s] = {}
            warning_message = (
                "Trucking arcs are given, but some trucking parameters are missing. The following missing parameters have been set to default values: "
                + str(missing_trucking_data)
            )
            warnings.warn(warning_message, stacklevel=3)

    # Set Default Data
    # Iterate through all expected input. For all input left without data, fill with empty dictionary or default data.
    # Raise warning if empty dictionary or default is used.
    default_used = []
    # Defaults - Sets
    all_set_input_tabs = get_valid_input_set_tab_names(model_type)

    for set_tab in all_set_input_tabs:
        if set_tab not in df_sets.keys():
            df_sets[set_tab] = {}
            default_used.append(set_tab)

    # Defaults - Parameter
    # Most default values are defined at the parameter definition. Some input data is not directly
    # associated with a parameter (e.g. "Economics")
    default_values = {
        "Economics": {"discount_rate": 0.08, "CAPEX_lifetime": 20.0},
        "DesalinationSurrogate": {"inlet_salinity": 200.0, "recovery": 1.0},
    }
    for input_tab in default_values.keys():
        if input_tab not in df_parameters.keys():
            df_parameters[input_tab] = default_values[input_tab]
            default_used.append(input_tab)

    # If an empty dictionary is passed to create_model(), the default value for the parameter
    # is defined at the initialization of the parameter
    all_parameter_input_tabs = get_valid_input_parameter_tab_names(model_type)
    for param_tab in all_parameter_input_tabs:
        if param_tab not in df_parameters.keys():
            df_parameters[param_tab] = {}
            default_used.append(param_tab)

    # Raise warning for default values
    if len(default_used) > 0:
        warning_message = (
            f"The following parameters were missing and default values were substituted: "
            + str(default_used)
        )
        warnings.warn(warning_message, stacklevel=3)

    return (df_sets, df_parameters)


def model_infeasibility_detection(strategic_model):
    # check_required_data() performs basic feasibility checks:
    # - at least one source node in the model
    # - at least one sink node in the model
    # - each source node has an outgoing arc, each sink node has an incoming arc, and all other nodes have both an incoming and an outgoing arc.

    capacity_feasibility_message = []
    demand_feasibility_message = []

    # Checks that for each time period, the volume of produced water is below the maximum capacity limit of sink nodes
    # Get the total system produced water for each time period (PadRates, FlowbackRates)
    def total_pw_rule(model, t):
        return sum(
            (model.p_beta_Production[p, t] + model.p_beta_Flowback[p, t])
            * model.model_units["time"]
            for p in model.s_P
        )

    strategic_model.e_TotalPW = Expression(
        strategic_model.s_T,
        rule=total_pw_rule,
        doc="Combined water supply forecast (flowback & production) at each time period [volume]",
    )

    # Get the maximum capacity of sink nodes for each time period
    # Sink nodes: CompletionsDemand, (InitialDisposalCapacity + max(disposalCapacityIncrements)) * DisposalOperatingCapacity,
    # StorageEvaporation, ReuseCapacity, InitialStorageCapacity + Storage CapacityIncrements,
    # (InitialTreatmentCapacity+TreatmentCapacityIncrements)*TreatmentResidual
    # Note: The Max function is used in this rule. In order for the expression to be updated,
    # process_data must be re-run.
    def total_pw_capacity_rule(model, t):
        return (
            (
                sum(
                    model.p_gamma_Completions[p, t]
                    for p in model.s_P  # Completions Demand
                )
                + sum(
                    model.p_omega_EvaporationRate
                    for s in model.s_S  # Storage Evaporation
                )
                + sum(
                    (
                        model.p_sigma_BeneficialReuse[o, t]
                        if model.p_sigma_BeneficialReuse[o, t].value >= 0
                        else model.p_M_Flow
                    )
                    for o in model.s_O
                    # Beneficial Reuse (if user does not specify a value, p_sigma_BeneficialReuse is -1)
                    # In this case, Beneficial Reuse at this site has no limit (big M parameter)
                )
                + sum(
                    (
                        model.p_sigma_Disposal[k]
                        + _get_max_value_for_parameter(model.p_delta_Disposal)
                    )
                    * model.p_epsilon_DisposalOperatingCapacity[k, t]
                    for k in model.s_K  # (Initial Disposal + max disposal) * operating capacity
                )
            )
            * model.model_units["time"]
            + sum(
                max(
                    [
                        (
                            model.p_sigma_Treatment[r, wt].value
                            + max(
                                [
                                    model.p_delta_Treatment[wt, j].value
                                    for j in model.s_J
                                ]
                            )
                        )
                        for wt in model.s_WT
                    ]
                )
                for r in model.s_R
            )
            * model.model_units["volume"]
            + sum(
                model.p_sigma_Storage[s]
                + _get_max_value_for_parameter(model.p_delta_Storage)
                for s in model.s_S  # Storage
            )
        )  # Treatment: for each treatment site, select treatment technology that yields the
        # maximum value for (initial treatment + max treatment expansion)

    strategic_model.e_MaxPWCapacity = Expression(
        strategic_model.s_T,
        rule=total_pw_capacity_rule,
        doc="Combined produced water capacity in system [volume]",
    )

    def total_water_demand_rule(model, t):
        # Note: if completions pad is outside system, demand is not required to be met
        return (
            sum(
                (
                    model.p_gamma_Completions[cp, t]
                    if model.p_chi_OutsideCompletionsPad[cp] == 0
                    else 0
                )
                for cp in model.s_CP
            )
            * model.model_units["time"]
        )

    strategic_model.e_TimePeriodDemand = Expression(
        strategic_model.s_T,
        rule=total_water_demand_rule,
        doc="Total water demand at each time period [volume]",
    )

    def total_water_available_rule(model, t):
        return (
            model.e_TotalPW[t]
            + sum(model.p_sigma_ExternalWater[f, t] for f in model.s_F)
            * model.model_units["time"]
        )

    strategic_model.e_WaterAvailable = Expression(
        strategic_model.s_T,
        rule=total_water_available_rule,
        doc="Total PW and external water available [volume]",
    )

    def capacity_check_rule(model, t):
        return model.e_TotalPW[t] - model.e_MaxPWCapacity[t]

    strategic_model.e_capacity_check = Expression(
        strategic_model.s_T,
        rule=capacity_check_rule,
        doc="Compare total water supply with total system water capacity [volume]",
    )

    def demand_check_rule(model, t):
        return model.e_TimePeriodDemand[t] - model.e_WaterAvailable[t]

    strategic_model.e_demand_check = Expression(
        strategic_model.s_T,
        rule=demand_check_rule,
        doc="Compare total water demand with total amount of water available [volume]",
    )

    # For each time period, check for infeasibilities
    for t in strategic_model.s_T:
        # If volume of produced water is greater than capacity, raise an infeasibility error
        if value(strategic_model.e_capacity_check[t]) > 0:
            capacity_feasibility_message.append(
                f"{t} ({round(value(strategic_model.e_TotalPW[t]))} total {strategic_model.model_units['volume']}s PW vs {round(value(strategic_model.e_MaxPWCapacity[t]))} {strategic_model.model_units['volume']}s PW capacity)"
            )

        # If completions demand is greater than combined water in system and external water available, raise an infeasibility error
        if value(strategic_model.e_demand_check[t]) > 0:
            demand_feasibility_message.append(
                f"{t} ({round(value(strategic_model.e_TimePeriodDemand[t]))} {strategic_model.model_units['volume']}s demand vs {round(value(strategic_model.e_WaterAvailable[t]))} {strategic_model.model_units['volume']}s available water)"
            )

    if len(capacity_feasibility_message) > 0:
        error_message = ", ".join(capacity_feasibility_message)
        raise DataInfeasibilityError(
            "An infeasibility in the input data has been detected. The following time periods have larger volumes of produced water than capacity in the system: "
            + error_message
        )

    if len(demand_feasibility_message) > 0:
        error_message = ", ".join(demand_feasibility_message)
        raise DataInfeasibilityError(
            "An infeasibility in the input data has been detected. The following time periods have higher demand than volume of produced water and externally sourced water available: "
            + error_message
        )

    return strategic_model


def _get_max_value_for_parameter(parameter):
    return max([x.value for x in parameter.values()]) * parameter.get_units()


# Custom error for Missing Data.
class MissingDataError(Exception):
    def __init__(self, message):
        super().__init__(message)


# Custom error for Data Infeasibility
class DataInfeasibilityError(Exception):
    def __init__(self, message):
        super().__init__(message)


# Helper function to check for data that is expected if an optional set
# (e.g. node type like "ReuseOptions") is given
def _check_optional_data(
    df_sets,
    df_parameters,
    optional_set_name,  # e.g., "ReuseOptions"
    required_sets_with_option,  # []
    required_parameters_with_option,  # ["BeneficialReuseCost","BeneficialReuseCredit"]
    requires_at_least_one=[],  # ["ROA", "SOA", "NOA", "ROT", "SOT"]
):
    # create set object for df_sets and df_parameters for simpler list comparison
    _df_sets_set = set(df_sets)
    _df_parameters_set = set(df_parameters.keys())

    # Check that optional_set_name is given by user (if not, no need to check)
    if optional_set_name in _df_sets_set:
        # Get missing parameters and sets
        _missing_parameters = set(required_parameters_with_option) - _df_parameters_set
        _missing_sets = set(required_sets_with_option) - _df_sets_set
        # For each missing parameter, add an empty dictionary to df_parameters and raise a warning
        if len(_missing_parameters) > 0 or len(_missing_sets) > 0:
            for param in _missing_parameters:
                df_parameters[param] = {}
            for s in _missing_sets:
                df_sets[s] = {}
            _missing_tabs = _missing_sets
            _missing_tabs.update(_missing_parameters)
            warning_message = (
                f"{optional_set_name} are given, but {optional_set_name} data is missing. Inputs for the following tabs have been set to default values: "
                + str(_missing_tabs)
            )
            warnings.warn(warning_message, stacklevel=3)
        # For each group in requires_at_least_one, check that at least one parameter exists in the input
        for requires_list in requires_at_least_one:
            _included_params = set(requires_list) & _df_parameters_set
            if len(_included_params) < 1:
                warning_message = (
                    f"{optional_set_name} are given, but some piping and trucking arcs are missing. At least one of the following arcs are required (missing sets have been assumed to be empty): "
                    + str(requires_list)
                )
                warnings.warn(warning_message, stacklevel=3)
            # Check missing sets, add empty sets
            for param in requires_list:
                if param not in df_parameters:
                    df_parameters[param] = {}

    # If the optional_set_name is missing from the input and required data dependent on it is included
    # (e.g. "SWDSites" is missing, but "DisposalOperationalCost" is included), raise a warning
    _input_parameters_dependent_on_optional_set = (
        set(required_parameters_with_option) & _df_parameters_set
    )
    if optional_set_name not in df_sets and (
        len(_input_parameters_dependent_on_optional_set) > 0
    ):
        raise MissingDataError(
            f'Essential data is incomplete. Parameter data for {optional_set_name} is given, but the "{optional_set_name}" Set is missing. Please add and complete the following tab(s): {optional_set_name}, or remove the following Parameters:'
            + str(_input_parameters_dependent_on_optional_set)
        )
    return (df_sets, df_parameters)


# Helper function for checking set and parameter data that is dependent on configuration options
def _check_config_dependent_data(
    df_sets,
    df_parameters,
    config_argument,  # e.g., "Hydraulics"
    config_required_sets,  # {config option 1: [set1, set2], config option 2: []}
    config_required_params,  # {config option 1: [param1], config option 2: [param2]}
):
    # Error message
    error_message = []

    # Data error is raised if the input tabs required for the configuration option are not provided
    _df_sets_set = set(df_sets)
    _df_params_set = set(df_parameters)

    required_sets = set(config_required_sets[config_argument])
    _missing_sets = required_sets - _df_sets_set

    required_params = set(config_required_params[config_argument])
    _missing_params = required_params - _df_params_set

    if len(_missing_params) > 0 or len(_missing_sets) > 0:
        _missing_tabs = _missing_sets
        _missing_tabs.update(_missing_params)
        error_message.append(
            f"The following inputs are missing and required for the selected config option {config_argument}: "
            + str(_missing_tabs)
        )

    return error_message
