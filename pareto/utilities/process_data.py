#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2026 by the software owners:
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

    # Collect set-tab findings (deleted or present-but-empty) from every
    # optional-set check below, so one consolidated error can list all
    # affected sets at once instead of only the first one hit.
    set_findings = []

    def _check_optional_data_accumulating(*args, **kwargs):
        return _check_optional_data(*args, set_findings=set_findings, **kwargs)

    # If either post_process or discrete config option is selected for water
    # quality, then additional data may be needed, depending on what node types
    # are used in the system. For example, If external water sources are used,
    # external water quality is needed.
    if (
        config.water_quality is WaterQuality.discrete
        or config.water_quality is WaterQuality.post_process
    ):
        # Check if storage sites are given. If so, check for storage initial water quality.
        df_sets, df_parameters = _check_optional_data_accumulating(
            df_sets,
            df_parameters,
            optional_set_name="StorageSites",
            required_sets_with_option={},
            required_parameters_with_option={"StorageInitialWaterQuality"},
            requires_at_least_one=[],
        )
        # Check if external water sources are given. If so, check for external water source quality.
        df_sets, df_parameters = _check_optional_data_accumulating(
            df_sets,
            df_parameters,
            optional_set_name="ExternalWaterSources",
            required_sets_with_option={},
            required_parameters_with_option={"ExternalWaterQuality"},
            requires_at_least_one=[],
        )
        # Check if production pads are given. If so, check for production pad water quality.
        df_sets, df_parameters = _check_optional_data_accumulating(
            df_sets,
            df_parameters,
            optional_set_name="ProductionPads",
            required_sets_with_option={},
            required_parameters_with_option={"PadWaterQuality"},
            requires_at_least_one=[],
        )
        # Check if completions pads are given. If so, check for completions pad water quality.
        df_sets, df_parameters = _check_optional_data_accumulating(
            df_sets,
            df_parameters,
            optional_set_name="CompletionsPads",
            required_sets_with_option={},
            required_parameters_with_option={"PadWaterQuality"},
            requires_at_least_one=[],
        )

    if config.infrastructure_timing is InfrastructureTiming.true:
        # Check if disposal capex is considered. If so, check for lead time.
        df_sets, df_parameters = _check_optional_data_accumulating(
            df_sets,
            df_parameters,
            optional_set_name="InjectionCapacities",
            required_sets_with_option={},
            required_parameters_with_option={"DisposalExpansionLeadTime"},
            requires_at_least_one=[],
        )

        # Check if treatment capex is considered. If so, check for lead time.
        df_sets, df_parameters = _check_optional_data_accumulating(
            df_sets,
            df_parameters,
            optional_set_name="TreatmentCapacities",
            required_sets_with_option={},
            required_parameters_with_option={"TreatmentExpansionLeadTime"},
            requires_at_least_one=[],
        )

        # Check if storage capex is considered. If so, check for lead time.
        df_sets, df_parameters = _check_optional_data_accumulating(
            df_sets,
            df_parameters,
            optional_set_name="StorageCapacities",
            required_sets_with_option={},
            required_parameters_with_option={"StorageExpansionLeadTime"},
            requires_at_least_one=[],
        )

        # Check if pipeline capex is considered. Check for relevant lead time type.
        if config.pipeline_cost is PipelineCost.distance_based:
            df_sets, df_parameters = _check_optional_data_accumulating(
                df_sets,
                df_parameters,
                optional_set_name="PipelineDiameters",
                required_sets_with_option={},
                required_parameters_with_option={"PipelineExpansionLeadTime_Dist"},
                requires_at_least_one=[],
            )
        elif config.pipeline_cost is PipelineCost.capacity_based:
            df_sets, df_parameters = _check_optional_data_accumulating(
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
            + "\n\n"
            "Every strategic model needs:\n"
            "  - a 'Units' tab (volume, distance, time, pressure, and currency units),\n"
            "  - at least one water source tab (ProductionPads, CompletionsPads, or ExternalWaterSources),\n"
            "  - at least one water sink tab (CompletionsPads, SWDSites, ReuseOptions, or StorageSites).\n\n"
            + "-" * 60
            + "\n"
            "To fix: re-add the missing tab(s) from the PARETO input template, including their header rows. "
            "If a tab exists in the workbook but did not load, scroll up for a warning starting with "
            "'Data loading failed for the following sheets': it names the broken tab."
        )

    # Optional Data: If data is not given, create empty dictionaries and raise a warning to the user

    # CompletionsPads. If given, check for additional data required to consider CompletionsPads in the model.
    # Call _check_optional_data function. This returns modified df_sets and df_parameters that
    # include empty dictionaries for missing data, so the parameters can be defined without error
    # when building the PARETO model.
    df_sets, df_parameters = _check_optional_data_accumulating(
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
    df_sets, df_parameters = _check_optional_data_accumulating(
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
    df_sets, df_parameters = _check_optional_data_accumulating(
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
    df_sets, df_parameters = _check_optional_data_accumulating(
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
    df_sets, df_parameters = _check_optional_data_accumulating(
        df_sets,
        df_parameters,
        optional_set_name="ReuseOptions",
        required_sets_with_option={},
        required_parameters_with_option={
            "BeneficialReuseCost",
            "BeneficialReuseCredit",
            "ReuseMinimum",
            "ReuseCapacity",
        },
        requires_at_least_one=[["ROA", "SOA", "NOA", "ROT", "SOT", "POT"]],
    )

    # StorageSites
    df_sets, df_parameters = _check_optional_data_accumulating(
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
    df_sets, df_parameters = _check_optional_data_accumulating(
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
    df_sets, df_parameters = _check_optional_data_accumulating(
        df_sets,
        df_parameters,
        optional_set_name="NetworkNodes",
        required_sets_with_option={},
        required_parameters_with_option={},
        requires_at_least_one=[piping_arcs],
    )

    # Treatment Capacity Expansion
    df_sets, df_parameters = _check_optional_data_accumulating(
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
    df_sets, df_parameters = _check_optional_data_accumulating(
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
    df_sets, df_parameters = _check_optional_data_accumulating(
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

    # One consolidated error for every set tab that is present but empty while
    # parameter tabs referencing it still contain entries: building the model
    # would index those parameters over the now-empty sets, so construction
    # fails with an internal error such as "Index '('CP01', 'N08')' is not
    # valid for indexed component 'p_CNA'".
    if set_findings:
        findings_by_set = {}
        for set_name, kind, tabs in set_findings:
            existing = findings_by_set.setdefault(
                set_name, {"kind": kind, "tabs": set()}
            )
            existing["tabs"].update(tabs)

        # Role of each affected set, from the authors' source/sink groups
        # (set_list_require_at_least_one): a set that is the scenario's only
        # remaining water source or sink cannot be left empty or deleted, so
        # "delete the referencing tabs" is not a viable fix for it.
        def _set_is_nonempty(name):
            return name in df_sets and len(df_sets[name]) > 0

        def _describe_role(name):
            for label, group in (
                ("water source", set_list_require_at_least_one[0]),
                ("water sink", set_list_require_at_least_one[1]),
            ):
                if name in group:
                    others = [s for s in group if s != name and _set_is_nonempty(s)]
                    if not others:
                        return (
                            f"the scenario's only remaining {label}: it must "
                            "list at least one facility, or another set in the "
                            f"same group ({', '.join(s for s in group if s != name)}) "
                            "must be filled instead"
                        )
                    return f"a {label} set"
            return None

        refs_by_set = {
            set_name: ", ".join(sorted(info["tabs"]))
            for set_name, info in findings_by_set.items()
        }

        # One finding: lead with the plain per-set sentence (referencing tabs
        # listed there). Several findings: skip the repeated sentences and let
        # the bullets below carry kind, role, and referencing tabs.
        old_style_head = ""
        if len(findings_by_set) == 1:
            set_name, info = next(iter(findings_by_set.items()))
            if info["kind"] == "missing":
                old_style_head = (
                    f"Essential data is incomplete. Parameter data for {set_name} "
                    f'is given, but the "{set_name}" Set is missing. Please add '
                    f"and complete the following tab(s): {set_name}, or remove "
                    f"the following Parameters: {refs_by_set[set_name]}"
                )
            else:
                old_style_head = (
                    f'Essential data is incomplete. The "{set_name}" Set tab is '
                    "present but contains no facility names, while parameter "
                    f"data for {set_name} is given. Please list the facility "
                    f'names in the "{set_name}" tab, or remove the following '
                    f"Parameters: {refs_by_set[set_name]}"
                )
            old_style_head += "\n\n"

        findings_lines_list = []
        for set_name, info in findings_by_set.items():
            role = _describe_role(set_name)
            kind_text = (
                "tab deleted or renamed"
                if info["kind"] == "missing"
                else "tab present but empty"
            )
            line = f"  - '{set_name}' ({kind_text}"
            if role:
                line += f"; {role}"
            line += ")"
            if len(findings_by_set) > 1:
                line += f": referenced by {refs_by_set[set_name]}"
            findings_lines_list.append(line)
        findings_lines = "\n".join(findings_lines_list)
        raise MissingDataError(
            old_style_head + f"Summary: {len(findings_by_set)} set tab(s) "
            "are missing from the workbook or contain no facility names, "
            "while parameter tabs that reference them still contain entries. "
            "The model would be built with zero facilities for these sets, so "
            "every referencing entry is invalid; this surfaces as internal "
            "errors such as \"Index '('CP01', 'N08')' is not valid for "
            "indexed component 'p_CNA'\".\n"
            + findings_lines
            + "\n\nNote: a tab listed as deleted was removed from the workbook "
            "(or its name is not a valid PARETO set tab name); a tab listed as "
            "present but empty had its rows deleted or its contents cleared. A "
            "sheet that exists but fails to parse is reported by the 'Data "
            "loading failed' warning and does not trigger this error."
            "\n\n" + "-" * 60 + "\n"
            "To fix, either:\n"
            "  - restore the deleted set tabs from the PARETO input template "
            "(a set tab needs its header row), or\n"
            "  - list the facility names in the set tabs that are present but "
            "empty (one row per facility below the header row), or\n"
            "  - if those facilities are not part of this scenario, delete "
            "the parameter tabs that reference them — but sets marked as the "
            "scenario's only remaining water source or sink must list at "
            "least one facility instead."
        )

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
        doc="Total completions demand at each time period [volume]",
    )

    def capacity_check_rule(model, t):
        return model.e_TotalPW[t] - model.e_MaxPWCapacity[t]

    strategic_model.e_capacity_check = Expression(
        strategic_model.s_T,
        rule=capacity_check_rule,
        doc="Compare total water supply with total system water capacity [volume]",
    )

    # Check capacity feasibility
    for t in strategic_model.s_T:
        if value(strategic_model.e_capacity_check[t]) > 0:
            capacity_feasibility_message.append(
                f"{t} ({round(value(strategic_model.e_TotalPW[t]))} total {strategic_model.model_units['volume']}s PW vs {round(value(strategic_model.e_MaxPWCapacity[t]))} {strategic_model.model_units['volume']}s PW capacity)"
            )

    if capacity_feasibility_message:
        error_message = ", ".join(capacity_feasibility_message)
        print("-" * 60)
        print(
            "To fix: increase system capacity for the affected periods (e.g. "
            "InitialDisposalCapacity, InitialStorageCapacity, ReuseCapacity, or "
            "pipeline capacity) or reduce produced water (PadRates) in those periods."
        )
        print(
            "Note: this check is aggregate only; passing it does not guarantee the "
            "network itself is feasible."
        )
        print("-" * 60)
        raise DataInfeasibilityError(
            "An infeasibility in the input data has been detected. Produced water volumes exceeds total system capacity for time periods: "
            + error_message
        )

    # 2) INCREMENTAL STORAGE-BASED DEMAND CHECK
    sorted_times = sorted(strategic_model.s_T)

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

    # Gather maximum possible storage capacity (base + expansions).
    max_storage_capacity = 0

    for s in strategic_model.s_S:
        base_cap = value(strategic_model.p_sigma_Storage[s])
        expansions_for_site = {
            k: v for (k, v) in strategic_model.p_delta_Storage.items() if k[0] == s
        }
        expansion = (
            _get_max_value_for_parameter(expansions_for_site)
            if expansions_for_site
            else 0
        )
        max_storage_capacity += base_cap + expansion

    for cp in strategic_model.s_CP:
        pad_storage_value = value(strategic_model.p_sigma_PadStorage[cp])
        max_storage_capacity += pad_storage_value

    # Initial water level at storage sites and pad storage sites.
    initial_storage = 0

    initial_storage = sum(
        value(strategic_model.p_lambda_Storage[s]) for s in strategic_model.s_S
    ) + sum(
        value(strategic_model.p_lambda_PadStorage[cp]) for cp in strategic_model.s_CP
    )
    # Leftover refers to the excess water stored from previous periods that will be added to produced water and external source water to calculate the total available water in the current time period.
    leftover = initial_storage

    for t in sorted_times:
        # Add PW and external water this period to total water available in storage
        leftover += value(strategic_model.e_WaterAvailable[t])

        # Keep track of water available before subtracting demand
        leftover_before_demand = leftover

        demand_t = value(strategic_model.e_TimePeriodDemand[t])

        # Subtract demand
        leftover -= demand_t

        # If leftover is now negative, record infeasibility and reset leftover to 0 (storage cannot be negative)
        if leftover < 0:
            demand_feasibility_message.append(
                f"{t} ({round(demand_t)} {strategic_model.model_units['volume']}s demand vs "
                f"{round(leftover_before_demand)} {strategic_model.model_units['volume']}s available water)"
            )
            # no negative carryover
            leftover = 0

        # Storage cannot exceed total capacity
        if leftover > max_storage_capacity:
            leftover = max_storage_capacity

        if demand_feasibility_message:
            error_message = ", ".join(str(tp) for tp in demand_feasibility_message)
            print("-" * 60)
            print(
                "To fix: increase supply or storage for the affected periods "
                "(e.g. PadRates, ExtWaterSourcingAvailability, InitialStorageCapacity) "
                "or reduce CompletionsDemand in those periods."
            )
            print(
                "Note: this check stops at the first deficient period, so later "
                "deficient periods are not listed; re-run after fixing to reveal any."
            )
            print("-" * 60)
            raise DataInfeasibilityError(
                "An infeasibility in the input data has been detected. Completion demand volume exceeds the total of produced water, external sources, and stored water in the following time periods: "
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
    set_findings=None,
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
    # Arc tabs matching the set's node-letter naming convention (e.g. CNA,
    # CCT for CompletionsPads) also reference the set and are reported too.
    node_letter = {
        "ProductionPads": "P",
        "CompletionsPads": "C",
        "SWDSites": "K",
        "ExternalWaterSources": "F",
        "StorageSites": "S",
        "TreatmentSites": "R",
        "ReuseOptions": "O",
        "NetworkNodes": "N",
    }.get(optional_set_name)

    # Function that extracts the arc tabs (network-connection tabs, e.g. CNA,
    # CKT, PCA) that reference the optional set, matched by the node-letter
    # naming convention in the tab name, and actually contain data. These tabs
    # are not in required_parameters_with_option, but their entries index over
    # the set and crash the build the same way when it is missing or emptied.

    def _tab_has_entries(tab):
        data = df_parameters.get(tab)
        if data is None:
            return False
        if hasattr(data, "empty"):
            return not data.empty
        return len(data) > 0

    def _nonempty_arc_tabs():
        return sorted(
            arc_tab
            for arc_tab in df_parameters
            if node_letter
            and isinstance(arc_tab, str)
            and len(arc_tab) == 3
            and (arc_tab[0] == node_letter or arc_tab[1] == node_letter)
            and arc_tab[-1] in ("A", "T")
            and _tab_has_entries(arc_tab)
        )

    # Here we check if 1) the set tab is missing (optional_set_name not in
    # df_sets: deleted from the workbook, or renamed/misspelled) and 2) something
    # still depends on it: dependent parameter tabs included, or non-empty arc
    # tabs referencing it.

    if optional_set_name not in df_sets and (
        len(_input_parameters_dependent_on_optional_set) > 0 or _nonempty_arc_tabs()
    ):
        # We construct a tabs set that is based on the input parameters dependent on the optional set
        # and the network-connection tabs
        tabs = (
            sorted(_input_parameters_dependent_on_optional_set) + _nonempty_arc_tabs()
        )
        if set_findings is None:
            raise MissingDataError(
                f"Essential data is incomplete: the workbook contains parameter or "
                f"network-connection tabs referencing "
                f"'{optional_set_name}' ({', '.join(tabs)}), but the "
                f'"{optional_set_name}" set tab itself was not found in the workbook. '
                f"Without that set, the model has no {optional_set_name} facilities and "
                "the parameter tabs cannot be used."
                f"\n\nNote: reaching this error means the '{optional_set_name}' tab is not "
                "present in the workbook at all (or its name is not a valid PARETO set "
                "tab name). A sheet that exists but fails to parse is reported by the "
                "'Data loading failed' warning and does not trigger this error."
                f"\n\nIf the tab was renamed or misspelled, scroll up for the warning "
                "starting with 'Invalid PARETO input': it lists tab names that are not "
                "standard PARETO inputs."
                f"\n\n" + "-" * 60 + "\n"
                "To fix, either:\n"
                f"  - restore the '{optional_set_name}' tab from the PARETO input template "
                "(a set tab needs its header row), or\n"
                f"  - if {optional_set_name} facilities are not part of this scenario, "
                "delete the dependent parameter tabs listed above."
            )
        set_findings.append((optional_set_name, "missing", tabs))

    # If the optional set is present but contains no facility names, while
    # parameter or arc tabs that reference it still contain entries, the model
    # cannot be built: the referencing parameters are indexed over the
    # now-empty set, so construction fails with an internal error such as
    # "Index '('CP01', 'N08')' is not valid for indexed component 'p_CNA'".
    # Raise a plain-language error instead, before the model is built.
    if (
        optional_set_name in df_sets
        and len(df_sets[optional_set_name]) == 0
        and (
            len(_input_parameters_dependent_on_optional_set) > 0 or _nonempty_arc_tabs()
        )
    ):
        referencing_tabs = (
            sorted(
                tab
                for tab in _input_parameters_dependent_on_optional_set
                if _tab_has_entries(tab)
            )
            + _nonempty_arc_tabs()
        )
        if referencing_tabs:
            if set_findings is None:
                raise MissingDataError(
                    f"Essential data is incomplete: the '{optional_set_name}' "
                    "tab is present but contains no facility names, while "
                    "parameter tabs that reference "
                    f"{optional_set_name} facilities still contain "
                    f"entries: {', '.join(referencing_tabs)}. The model would "
                    f"be built with zero {optional_set_name} facilities, so "
                    "every referencing entry is invalid; this surfaces as an "
                    "internal error such as \"Index '('CP01', 'N08')' is not "
                    "valid for indexed component 'p_CNA'\"."
                    "\n\nNote: this is different from the tab being missing "
                    "entirely: here the tab exists, but its rows were deleted "
                    "or its contents were cleared."
                    "\n\n" + "-" * 60 + "\n"
                    "To fix, either:\n"
                    f"  - list the {optional_set_name} facility names in the "
                    f"'{optional_set_name}' tab (one row per facility below "
                    "the header row), or\n"
                    f"  - if {optional_set_name} facilities are not part of "
                    "this scenario, also empty or delete the parameter tabs "
                    "listed above, or\n"
                    f"  - restore the '{optional_set_name}' tab from the "
                    "PARETO input template."
                )
            set_findings.append((optional_set_name, "empty", referencing_tabs))
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
