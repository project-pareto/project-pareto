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
This code file contains the updated function to generate report for each scenarios of our model.
"""

import pyomo.environ as pyo
from pyomo.environ import Constraint, Var, Expression, units as pyunits, value
import re

from pareto.utilities.enums import (
    WaterQuality,
    PipelineCost,
    InfrastructureTiming,
)

from pareto.utilities.results import (
    PrintValues,
    OutputUnits,
)
from pyomo.environ import Constraint, Var, Expression, units as pyunits, value
import pandas as pd
from enum import Enum
import contextlib


def generate_stochastic_report(
    model,
    results_obj=None,
    is_print=None,
    output_units=OutputUnits.user_units,
    fname="PARETO_report.xlsx",
):
    """
    This method identifies the type of model: [strategic, operational], create a printing list based on is_print,
    and creates a dictionary that contains headers for all the variables that will be included in an Excel report.
    IMPORTANT: If an indexed variable is added or removed from a model, the printing lists and headers should be updated
    accordingly.
    """
    if isinstance(model, pyo.Block):
        base_model = model.model()  # top-level Model
    else:
        base_model = model

    # Printing model sets, parameters, constraints, variable values

    printing_list = []

    # if model.type == "strategic":
    # if getattr(model, "model_type", None) == "strategic":
    if is_print is None:
        printing_list = []
    else:
        # PrintValues.detailed: Slacks values included, Same as "All"
        if is_print == PrintValues.detailed:
            printing_list = [
                "v_F_Piped",
                "v_F_Trucked",
                "v_F_Sourced",
                "v_F_PadStorageIn",
                "v_F_ReuseDestination",
                "v_X_Capacity",
                "v_T_Capacity",
                "v_F_Capacity",
                "v_D_Capacity",
                "v_F_DisposalDestination",
                "v_F_PadStorageOut",
                "v_C_Piped",
                "v_C_Trucked",
                "v_C_Sourced",
                "v_C_Disposal",
                "v_C_Treatment",
                "v_C_Reuse",
                "v_C_Storage",
                "v_C_BeneficialReuse",
                "v_L_Storage",
                "vb_y_Pipeline",
                "vb_y_Disposal",
                "vb_y_Storage",
                "vb_y_Treatment",
                "vb_y_Flow",
                "vb_y_DesalSelected",
                "v_T_Treatment_scaled",
                "v_C_Treatment_site",
                "v_C_TreatmentCapEx_site_time",
                "v_C_TreatmentCapEx_site",
                "recovery",
                "treatment_energy",
                "inlet_salinity",
                "vb_y_flow_ReLU",
                "v_C_Treatment_site_ReLU",
                "vb_y_BeneficialReuse",
                "v_F_Overview",
                "v_S_FracDemand",
                "v_S_Production",
                "v_S_Flowback",
                "v_S_PipelineCapacity",
                "v_S_StorageCapacity",
                "v_S_DisposalCapacity",
                "v_S_TreatmentCapacity",
                "v_S_BeneficialReuseCapacity",
                "v_Q",
            ]

            # PrintValues.nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage + etc.
        elif is_print == PrintValues.nominal:
            printing_list = [
                "v_F_Piped",
                "v_F_Trucked",
                "v_F_Sourced",
                "v_C_Piped",
                "v_C_Trucked",
                "v_C_Sourced",
                "vb_y_Pipeline",
                "vb_y_Disposal",
                "vb_y_Storage",
                "vb_y_Flow",
                "vb_y_Treatment",
                "vb_y_DesalSelected",
                "vb_y_flow_ReLU",
                "v_T_Treatment_scaled",
                "v_C_Treatment_site",
                "v_C_TreatmentCapEx_site_time",
                "v_C_TreatmentCapEx_site",
                "recovery",
                "inlet_salinity",
                "vb_y_BeneficialReuse",
                "v_F_Overview",
            ]

        # PrintValues.essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
        elif is_print == PrintValues.essential:
            printing_list = ["v_F_Overview"]

        else:
            raise Exception(
                f"generate_report: {is_print} not supported for `is_print` argument"
            )

    headers = {
        "v_F_Overview_dict": [("Variable Name", "Documentation", "Unit", "Total")],
        "vb_y_overview_dict": [
            (
                "CAPEX Type",
                "Location",
                "Destination",
                "Capacity",
                "Unit",
                "Technology",
                "First Use",
                "Build Start",
                "Build Lead Time [" + base_model.model_units["time"].to_string() + "s]",
            )
        ],
        "v_F_Piped_dict": [("Origin", "Destination", "Time", "Piped water")],
        "v_C_Piped_dict": [("Origin", "Destination", "Time", "Cost piping")],
        "v_F_Trucked_dict": [("Origin", "Destination", "Time", "Trucked water")],
        "v_C_Trucked_dict": [("Origin", "Destination", "Time", "Cost trucking")],
        "v_F_Sourced_dict": [
            ("External water source", "Completion pad", "Time", "Sourced water")
        ],
        "v_C_Sourced_dict": [
            (
                "External water source",
                "Completion pad",
                "Time",
                "Cost sourced water",
            )
        ],
        "v_F_PadStorageIn_dict": [("Completion pad", "Time", "StorageIn")],
        "v_F_PadStorageOut_dict": [("Completion pad", "Time", "StorageOut")],
        "v_C_Disposal_dict": [("Disposal site", "Time", "Cost of disposal")],
        "v_C_Treatment_dict": [("Treatment site", "Time", "Cost of Treatment")],
        "v_C_Reuse_dict": [("Completion pad", "Time", "Cost of reuse")],
        "v_C_Storage_dict": [("Storage Site", "Time", "Cost of Storage")],
        "v_R_Storage_dict": [
            ("Storage Site", "Time", "Credit of Retrieving Produced Water")
        ],
        "v_C_BeneficialReuse_dict": [
            (
                "Beneficial Reuse",
                "Time",
                "Processing Cost For Sending Water to Beneficial Reuse",
            )
        ],
        "v_R_BeneficialReuse_dict": [
            (
                "Beneficial Reuse",
                "Time",
                "Credit For Sending Water to Beneficial Reuse",
            )
        ],
        "v_L_Storage_dict": [("Storage site", "Time", "Storage Levels")],
        "v_L_PadStorage_dict": [("Completion pad", "Time", "Storage Levels")],
        "vb_y_Pipeline_dict": [
            ("Origin", "Destination", "Pipeline Diameter", "Pipeline Installation")
        ],
        "vb_y_Disposal_dict": [("Disposal Site", "Injection Capacity", "Disposal")],
        "vb_y_Storage_dict": [
            ("Storage Site", "Storage Capacity", "Storage Expansion")
        ],
        "vb_y_Flow_dict": [("Origin", "Destination", "Time", "Flow")],
        "vb_y_Treatment_dict": [
            (
                "Treatment Site",
                "Treatment Technology",
                "Treatment Capacity",
                "Treatment Expansion",
            )
        ],
        "vb_y_DesalSelected_dict": [("Treatment Site", "MVC selection")],
        "v_T_Treatment_scaled_dict": [("Treatment site", "Time", "surrogate cost")],
        "v_C_Treatment_site_dict": [("Treatment site", "Time", "surrogate cost")],
        "recovery_dict": [("Treatment site", "recovery")],
        "inlet_salinity_dict": [("Treatment site", "salinity")],
        "v_C_TreatmentCapEx_site_time_dict": [
            ("Treatment site", "Time", "surrogate cost")
        ],
        "v_C_TreatmentCapEx_site_dict": [("Treatment site", "surrogate cost")],
        "vb_y_flow_ReLU_dict": [("Treatment site", "Time", "Flow")],
        "v_C_Treatment_site_ReLU_dict": [("Treatment site", "Time", "surrogate cost")],
        "vb_y_BeneficialReuse_dict": [("Reuse site", "Time", "Reuse selection")],
        "v_D_Capacity_dict": [("Disposal Site", "Disposal Site Capacity")],
        "v_T_Capacity_dict": [("Treatment Site", "Treatment Capacity")],
        "v_X_Capacity_dict": [("Storage Site", "Storage Site Capacity")],
        "v_F_Capacity_dict": [("Origin", "Destination", "Flow Capacity")],
        "v_F_ReuseDestination_dict": [
            ("Completion Pad", "Time", "Total Deliveries to Completion Pad")
        ],
        "v_F_DisposalDestination_dict": [
            ("Disposal Site", "Time", "Total Deliveries to Disposal Site")
        ],
        "quality.v_Q_dict": [("Location", "Water Component", "Time", "Water Quality")],
        "v_F_DesalinatedWater_dict": [
            ("Treatment site", "Time", "Desalinated water removed from system")
        ],
        "v_F_ResidualWater_dict": [("Treatment site", "Time", "Residual Water")],
        "v_F_TreatedWater_dict": [("Treatment site", "Time", "Treated Water")],
        "v_F_TreatmentFeed_dict": [("Treatment site", "Time", "Treatment Feed")],
        "v_F_TreatmentFeedTech_dict": [
            ("Treatment site", "Treatment technology", "Time", "Treatment Feed")
        ],
        "v_F_StorageEvaporationStream_dict": [
            ("Storage site", "Time", "Evaporated Volume")
        ],
        "v_F_CompletionsDestination_dict": [
            ("Pads", "Time", "Total deliveries to completions pads")
        ],
        "e_TotalTruckingEmissions_dict": [("Component", "Total trucking emissions")],
        "e_TotalPipeOperationsEmissions_dict": [
            ("Component", "Total pipeline operations emissions")
        ],
        "e_TotalPipeInstallEmissions_dict": [
            ("Component", "Total pipeline installation emissions")
        ],
        "e_TotalDisposalEmissions_dict": [("Component", "Total disposal emissions")],
        "e_TotalStorageEmissions_dict": [("Component", "Total storage emissions")],
        "e_TotalTreatmentEmissions_dict": [("Component", "Total treatment emissions")],
        "e_TotalEmissionsByComponent_dict": [
            ("Component", "Total emissions by component")
        ],
        "e_TotalPW_dict": [("Time", "Combined water supply (flowback + production)")],
        "e_MaxPWCapacity_dict": [
            ("Time", "Combined produced water capacity in system")
        ],
        "e_TimePeriodDemand_dict": [("Time", "Total water demand")],
        "e_WaterAvailable_dict": [("Time", "Total PW and external water available")],
        "e_capacity_check_dict": [
            ("Time", "Compare total water supply with total system water capacity")
        ],
        "e_demand_check_dict": [
            (
                "Time",
                "Compare total water demand with total amount of water available",
            )
        ],
        "v_Q_CompletionPad_dict": [
            ("Completion pad", "Water Component", "Time", "Water Quality")
        ],
        "v_DQ_dict": [
            (
                "Location",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                " Water Quality",
            )
        ],
        "v_F_DiscretePiped_dict": [
            (
                "Origin",
                "Destination",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Piped water",
            )
        ],
        "v_F_DiscreteTrucked_dict": [
            (
                "Origin",
                "Destination",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Trucked water",
            )
        ],
        "v_F_DiscreteDisposalDestination_dict": [
            (
                "Disposal Site",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Total Deliveries to Disposal Site",
            )
        ],
        "v_F_DiscreteFlowOutStorage_dict": [
            (
                "Storage Site",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Total outflow storage site",
            )
        ],
        "v_L_DiscreteStorage_dict": [
            (
                "Storage Site",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Storage Levels",
            )
        ],
        "v_F_DiscreteFlowTreatment_dict": [
            (
                "Treatment Site",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Treated water",
            )
        ],
        "v_F_DiscreteFlowOutNode_dict": [
            (
                "Node",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Total outflow node",
            )
        ],
        "v_F_DiscreteBRDestination_dict": [
            (
                "Reuse Location",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Beneficial water",
            )
        ],
        "v_F_DiscreteFlowCPIntermediate_dict": [
            (
                "Completion pad intermediate",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Intermediate water",
            )
        ],
        "v_F_DiscreteFlowCPStorage_dict": [
            (
                "Completion pad storage",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Storage level out",
            )
        ],
        "v_L_DiscretePadStorage_dict": [
            (
                "Completion pad storage",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Storage levels in",
            )
        ],
        "v_F_DiscreteFlowOutPadStorage_dict": [
            (
                "Completion pad storage",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Outflow storage",
            )
        ],
        "v_F_DiscreteFlowInPadStorage_dict": [
            (
                "Completion pad storage",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Inflow storage",
            )
        ],
        "v_F_DiscreteCPDestination_dict": [
            (
                "Completion pad intermediate",
                "Time",
                "Water Component",
                "Discrete Water Quality",
                "Intermediate water completion pad",
            )
        ],
        "v_F_BeneficialReuseDestination_dict": [
            (
                "Beneficial Reuse Site",
                "Time",
                "Total deliveries to beneficial reuse",
            )
        ],
        "v_S_FracDemand_dict": [("Completion pad", "Time", "Slack FracDemand")],
        "v_S_Production_dict": [("Production pad", "Time", "Slack Production")],
        "v_S_Flowback_dict": [("Completion pad", "Time", "Slack Flowback")],
        "v_S_PipelineCapacity_dict": [
            ("Origin", "Destination", "Slack Pipeline Capacity")
        ],
        "v_S_StorageCapacity_dict": [("Storage site", "Slack Storage Capacity")],
        "v_S_DisposalCapacity_dict": [("Storage site", "Slack Disposal Capacity")],
        "v_S_TreatmentCapacity_dict": [("Treatment site", "Slack Treatment Capacity")],
        "v_S_BeneficialReuseCapacity_dict": [("Reuse site", "Slack Reuse Capacity")],
        "Solver_Stats_dict": [("Solution Attribute", "Value")],
    }

    # Infrastructure buildout table

    # Due to tolerances, binaries may not exactly equal 1
    binary_epsilon = 0.1
    # "vb_y_Treatment"
    treatment_data = base_model.vb_y_Treatment._data
    # get units
    from_unit_string = base_model.p_delta_Treatment.get_units().to_string()
    # the display units (to_unit) is defined by output_units from module parameter
    if output_units == OutputUnits.unscaled_model_units:
        to_unit = base_model.model_to_unscaled_model_display_units[from_unit_string]
    elif output_units == OutputUnits.user_units:
        to_unit = base_model.model_to_user_units[from_unit_string]
    for i in treatment_data:
        # add values to output dictionary
        if (
            treatment_data[i].value >= 1 - binary_epsilon
            and treatment_data[i].value <= 1 + binary_epsilon
            and base_model.p_delta_Treatment[(i[1], i[2])].value > 0
        ):
            capacity = pyunits.convert_value(
                base_model.p_delta_Treatment[(i[1], i[2])].value,
                from_units=base_model.p_delta_Treatment.get_units(),
                to_units=to_unit,
            )
            if (
                base_model.config.infrastructure_timing == InfrastructureTiming.true
                and i[0] in base_model.infrastructure_firstUse
            ):
                first_use = base_model.infrastructure_firstUse[i[0]]
                build_start = base_model.infrastructure_buildStart[i[0]]
                lead_time = base_model.infrastructure_leadTime[i[0]]
            else:
                first_use = "--"
                build_start = "--"
                lead_time = "--"
            headers["vb_y_overview_dict"].append(
                (
                    "Treatment Facility",
                    i[0],
                    "--",
                    capacity,
                    to_unit.to_string().replace("oil_bbl", "bbl"),
                    i[1],
                    first_use,
                    build_start,
                    lead_time,
                )
            )

    # vb_y_Disposal
    disposal_data = base_model.vb_y_Disposal._data
    # get units
    from_unit_string = base_model.p_delta_Disposal.get_units().to_string()
    # the display units (to_unit) is defined by output_units from module parameter
    if output_units == OutputUnits.unscaled_model_units:
        to_unit = base_model.model_to_unscaled_model_display_units[from_unit_string]
    elif output_units == OutputUnits.user_units:
        to_unit = base_model.model_to_user_units[from_unit_string]
    for i in disposal_data:
        # Get site name and selected capacity from data
        disposal_site = i[0]
        disposal_capacity = i[1]
        # add values to output dictionary
        if (
            disposal_data[i].value >= 1 - binary_epsilon
            and disposal_data[i].value <= 1 + binary_epsilon
            and base_model.p_delta_Disposal[disposal_site, disposal_capacity].value > 0
        ):
            capacity = pyunits.convert_value(
                base_model.p_delta_Disposal[disposal_site, disposal_capacity].value,
                from_units=base_model.p_delta_Disposal.get_units(),
                to_units=to_unit,
            )
            if (
                base_model.config.infrastructure_timing == InfrastructureTiming.true
                and disposal_site in base_model.infrastructure_firstUse
            ):
                first_use = base_model.infrastructure_firstUse[disposal_site]
                build_start = base_model.infrastructure_buildStart[disposal_site]
                lead_time = base_model.infrastructure_leadTime[disposal_site]
            else:
                first_use = "--"
                build_start = "--"
                lead_time = "--"
            headers["vb_y_overview_dict"].append(
                (
                    "Disposal Facility",
                    disposal_site,
                    "--",
                    capacity,
                    to_unit.to_string().replace("oil_bbl", "bbl"),
                    "--",
                    first_use,
                    build_start,
                    lead_time,
                )
            )

    # vb_y_Storage
    storage_data = base_model.vb_y_Storage._data
    # get units
    from_unit_string = base_model.p_delta_Storage.get_units().to_string()
    # the display units (to_unit) is defined by output_units from module parameter
    if output_units == OutputUnits.unscaled_model_units:
        to_unit = base_model.model_to_unscaled_model_display_units[from_unit_string]
    elif output_units == OutputUnits.user_units:
        to_unit = base_model.model_to_user_units[from_unit_string]
    for i in storage_data:
        # add values to output dictionary
        if (
            storage_data[i].value >= 1 - binary_epsilon
            and storage_data[i].value <= 1 + binary_epsilon
            and base_model.p_delta_Storage[i[1]].value > 0
        ):
            capacity = pyunits.convert_value(
                base_model.p_delta_Storage[i[1]].value,
                from_units=base_model.p_delta_Storage.get_units(),
                to_units=to_unit,
            )
            if (
                base_model.config.infrastructure_timing == InfrastructureTiming.true
                and i[0] in base_model.infrastructure_firstUse
            ):
                first_use = base_model.infrastructure_firstUse[i[0]]
                build_start = base_model.infrastructure_buildStart[i[0]]
                lead_time = base_model.infrastructure_leadTime[i[0]]
            else:
                first_use = "--"
                build_start = "--"
                lead_time = "--"
            headers["vb_y_overview_dict"].append(
                (
                    "Storage Facility",
                    i[0],
                    "--",
                    capacity,
                    to_unit.to_string().replace("oil_bbl", "bbl"),
                    "--",
                    first_use,
                    build_start,
                    lead_time,
                )
            )

    # vb_y_Pipeline
    if base_model.config.pipeline_cost == PipelineCost.distance_based:
        capacity_variable = base_model.p_mu_Pipeline
    elif base_model.config.pipeline_cost == PipelineCost.capacity_based:
        capacity_variable = base_model.p_delta_Pipeline
    pipeline_data = base_model.vb_y_Pipeline._data
    # get units
    from_unit_string = capacity_variable.get_units().to_string()
    # the display units (to_unit) is defined by output_units from module parameter
    if output_units == OutputUnits.unscaled_model_units:
        to_unit = base_model.model_to_unscaled_model_display_units[from_unit_string]
    elif output_units == OutputUnits.user_units:
        to_unit = base_model.model_to_user_units[from_unit_string]
    for i in pipeline_data:
        # add values to output dictionary only if non-zero capacity is selected
        if (
            pipeline_data[i].value >= 1 - binary_epsilon
            and pipeline_data[i].value <= 1 + binary_epsilon
            and capacity_variable[i[2]].value > 0
        ):
            capacity = pyunits.convert_value(
                capacity_variable[i[2]].value,
                from_units=capacity_variable.get_units(),
                to_units=to_unit,
            )
            if (
                base_model.config.infrastructure_timing == InfrastructureTiming.true
                and (i[0], i[1]) in base_model.infrastructure_firstUse
            ):
                first_use = base_model.infrastructure_firstUse[(i[0], i[1])]
                build_start = base_model.infrastructure_buildStart[(i[0], i[1])]
                lead_time = base_model.infrastructure_leadTime[(i[0], i[1])]
            else:
                first_use = "--"
                build_start = "--"
                lead_time = "--"
            headers["vb_y_overview_dict"].append(
                (
                    "Pipeline Construction",
                    i[0],
                    i[1],
                    capacity,
                    to_unit.to_string().replace("oil_bbl", "bbl"),
                    "--",
                    first_use,
                    build_start,
                    lead_time,
                )
            )

    # Hydraulics variables
    headers.update(
        {
            "hydraulics.v_term_dict": [
                (
                    "Location",
                    "Location",
                    "Time",
                    "Term Value",
                )
            ],
            "hydraulics.v_lambdas_dict": [
                (
                    "Location",
                    "Location",
                    "Time",
                    "Piecewise Linear Approximation",
                    "Convex conmination multiplier",
                )
            ],
            "hydraulics.vb_z_dict": [
                (
                    "Location",
                    "Location",
                    "Time",
                    "Piecewise Linear Approximation",
                    "Convex conmination binary",
                )
            ],
            "hydraulics.v_PumpHead_dict": [
                (
                    "Location",
                    "Location",
                    "Time",
                    "Pump Head",
                )
            ],
            "hydraulics.vb_Y_Pump_dict": [
                (
                    "Location",
                    "Location",
                    "Binary Pump Indicator",
                )
            ],
            "hydraulics.v_ValveHead_dict": [
                (
                    "Location",
                    "Location",
                    "Time",
                    "Valve Head",
                )
            ],
            "hydraulics.v_PumpCost_dict": [
                (
                    "Location",
                    "Location",
                    "Pump Cost",
                )
            ],
            "hydraulics.v_Pressure_dict": [
                (
                    "Location",
                    "Time",
                    "Pressure at a Location",
                )
            ],
            "hydraulics.v_HW_loss_dict": [
                (
                    "Location",
                    "Location",
                    "Time",
                    "Hazen-Williams head loss",
                )
            ],
            "hydraulics.v_eff_pipe_diam_dict": [
                (
                    "Location",
                    "Location",
                    "Effective Pipeline Diameter",
                )
            ],
        }
    )

    if base_model.do_subsurface_risk_calcs:
        headers.update(
            {
                "subsurface.vb_y_dist_dict": [("Disposal site", "Proximity", "Value")],
                "subsurface.e_norm_risk_dist_dict": [("Proximity", "Value")],
                "subsurface.e_norm_risk_severity_dict": [("Proximity", "Value")],
                "subsurface.e_risk_metrics_dict": [("Disposal site", "Value")],
            }
        )

    # Loop through all the variables in the model
    for variable in base_model.component_objects(Var, descend_into=True):
        base_name = variable.local_name
        # we may also choose to not convert, additionally not all of our variables have units (binary variables),
        units_true = (
            variable.get_units() is not None
            and variable.get_units().to_string() != "dimensionless"
        )
        # If units are used, determine what the display units should be based off user input
        if units_true:
            from_unit_string = variable.get_units().to_string()
            # the display units (to_unit) is defined by output_units from module parameter
            if output_units == OutputUnits.unscaled_model_units:
                to_unit = base_model.model_to_unscaled_model_display_units[
                    from_unit_string
                ]
            elif output_units == OutputUnits.user_units:
                to_unit = base_model.model_to_user_units[from_unit_string]
            else:
                print(
                    f"WARNING: Report output units selected by user for variable {variable.name} are not valid"
                )
                to_unit = None

            # if variable is indexed, update headers to display unit
            if variable.is_indexed():
                # header = list(headers[str(variable.name) + "_dict"][0])
                key = base_name + "dict"
                if key not in headers:
                    continue
                header = list(headers[key][0])
                header[-1] = (
                    headers[str(variable.name) + "_dict"][0][-1]
                    + " ["
                    + to_unit.to_string().replace("oil_bbl", "bbl")
                    + "]"
                )
                headers[key][0] = tuple(header)

        else:
            to_unit = None

        if variable._data is not None:
            # Loop through the indices of a variable. "i" is a tuple of indices
            for i in variable._data:
                # Convert the value to display units if necessary
                if units_true and variable._data[i].value:
                    var_value = pyunits.convert_value(
                        variable._data[i].value,
                        from_units=variable.get_units(),
                        to_units=to_unit,
                    )
                else:
                    var_value = variable._data[i].value

                if not variable.is_indexed():
                    # Create the overview report with variables that are not indexed, e.g.:
                    # total piped water, total trucked water, total externally sourced water, etc.
                    if to_unit is None:
                        tu = None
                    else:
                        tu = to_unit.to_string().replace("oil_bbl", "bbl")

                    headers["v_F_Overview_dict"].append(
                        (variable.name, variable.doc, tu, var_value)
                    )

                else:
                    # Add indexed variables to their own tab
                    # Omit surrogate costs variables
                    if (
                        len(str(variable.name)) >= 15
                        and str(variable.name)[:15] == "surrogate_costs"
                    ):
                        continue

                    # if a variable contains only one index, then "i" is recognized as a string and not a tuple,
                    # in that case, "i" is redefined by adding a comma so that it becomes a tuple
                    if isinstance(i, str):
                        i = (i,)

                    # replace the discrete qualities by their actual values
                    if str(variable.name) == "v_DQ":
                        var_value = model.p_discrete_quality[i[2], i[3]].value

                    if (
                        var_value is not None
                        and var_value != 0
                        and variable.name
                        not in [
                            "inlet_salinity",
                            "v_C_TreatmentCapEx_site",
                            "v_C_Treatment_site",
                            "v_C_Treatment_site_ReLU",
                            "recovery",
                            "v_C_TreatmentCapEx_site_time",
                            "totalCapex",
                            "v_T_Treatment_scaled",
                            "v_T_Treatment_scaled_ReLU",
                        ]
                    ):
                        # headers[str(variable.name) + "_dict"].append((*i, var_value))
                        key = base_name + "dict"
                        if key not in headers:
                            continue
                        headers[key].append((*i, var_value))

    # Loop through all the expressions in the model
    for expr in base_model.component_objects(Expression, descend_into=True):
        base_name = expr.local_name
        key = base_name + "_dict"
        # The get_units function does not work properly when called on an
        # indexed expression, so we have to grab the units from the first
        # index when we iterate through the expression. When we do that, we
        # mark the units_fetched flag as True so we only do it once.
        if key not in headers:
            continue

        units_fetched = False
        to_unit = None
        from_unit = None
        units_true = False
        # Loop through the indexes of the expression.
        for i in expr:
            if not units_fetched:
                expr_units = pyunits.get_units(expr[i])
                units_true = (
                    pyunits.get_units(expr[i]) is not None
                    and pyunits.get_units(expr[i]).to_string() != "dimensionless"
                )

                # If units are used, determine what the display units should be based off user input
                if units_true:
                    from_unit = expr_units
                    from_unit_string = expr_units.to_string()
                    # the display units (to_unit) is defined by output_units from module parameter
                    if output_units == OutputUnits.unscaled_model_units:
                        to_unit = model.model_to_unscaled_model_display_units[
                            from_unit_string
                        ]
                    elif output_units == OutputUnits.user_units:
                        to_unit = model.model_to_user_units[from_unit_string]
                    else:
                        print(
                            f"WARNING: Report output units selected by user for expression {expr.name} are not valid"
                        )
                        to_unit = None

                    # If expression data is not none and indexed, update headers to display unit
                    # if len(expr) > 1 and list(expr.keys())[0] is not None:
                    if expr.is_indexed():
                        header = list(headers[key][0])
                        header[-1] = (
                            headers[key][0][-1]
                            + " ["
                            + to_unit.to_string().replace("oil_bbl", "bbl")
                            + "]"
                        )
                        headers[key][0] = tuple(header)

                else:
                    to_unit = None

                units_fetched = True

            # Convert the expression value to display units if necessary
            # Use a try/except block to handle any errors in getting the value
            # of the expression (e.g., division by zero)
            try:
                val = value(expr[i])
                if units_true:
                    expr_value = pyunits.convert_value(
                        val,
                        from_units=from_unit,
                        to_units=to_unit,
                    )
                else:
                    expr_value = val

            except:
                expr_value = "Error"

            if not expr.is_indexed():
                # Add non-indexed expressions to the v_F_Overview tab
                if to_unit is None or expr_value == "Error":
                    tu = None
                else:
                    tu = to_unit.to_string().replace("oil_bbl", "bbl")

                headers["v_F_Overview_dict"].append(
                    (base_name, expr.doc, tu, expr_value)
                )
            else:
                # Add indexed expressions to their own tab
                # if an expression contains only one index, then "i" is recognized
                # as a string and not a tuple; in this case, convert to a tuple
                if isinstance(i, str):
                    i = (i,)
                if expr_value is not None and expr_value != "Error" and expr_value != 0:
                    headers[key].append((*i, expr_value))

    # The sites_included result from the subsurface risk module is a bit
    # unique - it's the only result we have that is implemented as a Param. Add
    # it to the results file.
    if base_model.type == "strategic" and base_model.do_subsurface_risk_calcs:
        headers.update({"subsurface.sites_included_dict": [("Disposal site", "Value")]})
        for k in base_model.s_K:
            val = value(base_model.subsurface.sites_included[k])
            if val != 0:
                headers["subsurface.sites_included_dict"].append((k, val))

    if base_model.v_C_Slack.value is not None and base_model.v_C_Slack.value > 0:
        print("!!!ATTENTION!!! One or several slack variables have been triggered!")

    # Loop for printing information on the command prompt
    for i in list(headers.items())[1:]:
        dict_name = i[0][: -len("_dict")]
        if dict_name in printing_list:
            print("\n", "=" * 10, dict_name.upper(), "=" * 10)
            print(i[1][0])
            for j in i[1][1:]:
                print("{0}{1} = {2}".format(dict_name, j[:-1], j[-1]))

    # Loop for printing Overview Information on the command prompt
    for i in list(headers.items())[:1]:
        dict_name = i[0][: -len("_dict")]
        if dict_name in printing_list:
            print("\n", "=" * 10, dict_name.upper(), "=" * 10)
            # print(i[1][1][0])
            for j in i[1][1:]:
                if not j[0]:  # Conditional that checks if a blank line should be added
                    print()
                elif not j[
                    1
                ]:  # Conditional that checks if the header for a section should be added
                    print(j[0].upper())
                else:
                    print("{0} = {1}".format(j[1], j[3]))

    # Printing warning if "proprietary_data" is True
    if len(printing_list) > 0 and base_model.proprietary_data is True:
        print(
            "\n**********************************************************************"
        )
        print("            WARNING: This report contains Proprietary Data            ")
        print("**********************************************************************")

    # Adding a footnote to the each dictionary indicating if the report contains Prorpietary Data
    if base_model.proprietary_data is True:
        for report in headers:
            if len(headers[report]) > 1:
                headers[report].append(("PROPRIETARY DATA",))

    def to_msg(attr):
        """
        Convert an attribute to the appropriate string to print in report
        """
        # If a Pyomo attribute is undefined, just replace with empty string instead
        msg = str(attr)
        if msg == "<undefined>":
            return ""
        return msg

    if results_obj is not None:
        report = "Solver_Stats_dict"
        headers[report].append(
            ("Termination Condition", to_msg(results_obj.solver.termination_condition))
        )
        headers[report].append(
            ("Termination Message", to_msg(results_obj.solver.termination_message))
        )
        headers[report].append(("Lower Bound", to_msg(results_obj.problem.lower_bound)))
        headers[report].append(("Upper Bound", to_msg(results_obj.problem.upper_bound)))
        headers[report].append(
            ("Number of variables", to_msg(results_obj.problem.number_of_variables))
        )
        headers[report].append(
            ("Number of constraints", to_msg(results_obj.problem.number_of_constraints))
        )
        headers[report].append(
            ("Number of nonzeros", to_msg(results_obj.problem.number_of_nonzeros))
        )
        headers[report].append(
            (
                "Number of binary variables",
                to_msg(results_obj.problem.number_of_binary_variables),
            )
        )
        headers[report].append(
            (
                "Number of integer variables",
                to_msg(results_obj.problem.number_of_integer_variables),
            )
        )
        headers[report].append(
            ("Solver wall clock time", to_msg(results_obj.solver.wallclock_time))
        )
        headers[report].append(
            ("Solver CPU time", to_msg(results_obj.solver.system_time))
        )
        headers[report].append(
            (
                "Number of nodes",
                to_msg(
                    results_obj.solver.statistics.branch_and_bound.number_of_bounded_subproblems
                ),
            )
        )

    # Creating the Excel report
    if fname is not None:
        with pd.ExcelWriter(fname) as writer:
            for i in headers:
                df = pd.DataFrame(headers[i][1:], columns=headers[i][0])
                df.fillna("")
                # df.to_excel(
                #     writer, sheet_name=i[: -len("_dict")], index=False, startrow=1
                # )
                sheet_name = i.replace("_dict", "")
                df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)

    return model, headers


# def generate_stochastic_report(
#     scn_block, fname="stochastic_report.xlsx", is_print=PrintValues.essential
# ):

#     results = {}

#     def sanitize_sheet_name(name):
#         # Keep only the variable name, remove block prefix
#         if "." in name:
#             name = name.split(".")[-1]
#         # Remove invalid Excel characters
#         name = re.sub(r"[\[\]\*\?/\\:]", "_", name)
#         return name[:31]  # Excel limit

#     # ---------------------------------------------------------
#     # Collect all variables (indexed + non-indexed)
#     # ---------------------------------------------------------
#     for var in scn_block.component_objects(pyo.Var, descend_into=True):

#         if var.is_indexed():
#             data = {idx: pyo.value(var[idx]) for idx in var}
#         else:
#             data = pyo.value(var)

#         results[var.name] = data

#     # ---------------------------------------------------------
#     # Write to Excel
#     # ---------------------------------------------------------
#     with pd.ExcelWriter(fname) as writer:

#         # --------------------------
#         # 1. OVERVIEW SHEET
#         # --------------------------
#         overview_rows = []
#         for var_name, data in results.items():
#             # scalar variables = non-indexed
#             if not isinstance(data, dict):
#                 short_name = sanitize_sheet_name(var_name)
#                 unit = getattr(scn_block.find_component(var_name), "units", None)
#                 overview_rows.append([short_name, data, unit])

#         if overview_rows:
#             df_overview = pd.DataFrame(
#                 overview_rows, columns=["Variable Name", "Value", "Unit"]
#             )
#             df_overview.to_excel(writer, sheet_name="Overview", index=False)

#         # --------------------------
#         # 2. INDEXED VARIABLES
#         # --------------------------
#         for var_name, data in results.items():
#             if isinstance(data, dict):  # indexed var

#                 short_name = sanitize_sheet_name(var_name)
#                 # Create list of (index, value) pairs
#                 rows = [(idx, val) for idx, val in data.items()]
#                 # Keeping only non-zero entries
#                 rows = [(idx, val) for idx, val in rows if abs(val) > 1e-5]

#                 if not rows:
#                     continue

#                 if rows and isinstance(rows[0][0], tuple):
#                     split_index = pd.DataFrame([list(idx) for idx, _ in rows])
#                     split_index.columns = [
#                         f"Index_{i+1}" for i in range(split_index.shape[1])
#                     ]
#                     values = [val for _, val in rows]
#                     df = split_index.copy()
#                     df["Value"] = values
#                 else:
#                     df = pd.DataFrame(rows, columns=["Index", "Value"])

#                 # y_vars = [
#                 #     "vb_y_Pipeline",
#                 #     "vb_y_Storage",
#                 #     "vb_y_Treatment",
#                 #     "vb_y_Disposal",
#                 #     "vb_y_BeneficialReuse",
#                 # ]
#                 # if any(yname in var_name for yname in y_vars):
#                 #     df = df[df["Value"] > 0.0]

#                 df.to_excel(writer, sheet_name=short_name, index=False)

#     return results
