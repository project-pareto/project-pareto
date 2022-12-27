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
"""


Authors: PARETO Team 
"""
from pareto.operational_water_management.operational_produced_water_optimization_model import (
    ProdTank,
    WaterQuality,
)
from pyomo.environ import Var, units as pyunits, value
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from enum import Enum
from plotly.offline import init_notebook_mode, iplot


class PrintValues(Enum):
    detailed = 0
    nominal = 1
    essential = 2


class OutputUnits(Enum):
    # All output units are defined by user
    user_units = 0
    # All output units are defined by user EXCEPT time which is determined by the decision period discretization
    unscaled_model_units = 1


def generate_report(
    model, is_print=[], output_units=OutputUnits.user_units, fname=None
):
    """
    This method identifies the type of model: [strategic, operational], create a printing list based on is_print,
    and creates a dictionary that contains headers for all the variables that will be included in an Excel report.
    IMPORTANT: If an indexed variable is added or removed from a model, the printing lists and headers should be updated
    accrodingly.
    """
    # Printing model sets, parameters, constraints, variable values

    printing_list = []

    if model.type == "strategic":
        if len(is_print) == 0:
            printing_list = []
        else:
            # PrintValues.detailed: Slacks values included, Same as "All"
            if is_print[0].value == 0:
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
                    "v_C_Reuse",
                    "v_L_Storage",
                    "vb_y_Pipeline",
                    "vb_y_Disposal",
                    "vb_y_Storage",
                    "vb_y_Treatment",
                    "vb_y_FLow",
                    "v_F_Overview",
                    "v_S_FracDemand",
                    "v_S_Production",
                    "v_S_Flowback",
                    "v_S_PipelineCapacity",
                    "v_S_StorageCapacity",
                    "v_S_DisposalCapacity",
                    "v_S_TreatmentCapacity",
                    "v_S_ReuseCapacity",
                    "v_Q",
                ]

            # PrintValues.nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage + etc.
            elif is_print[0].value == 1:
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
                    "v_F_Overview",
                ]

            # PrintValues.essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
            elif is_print[0].value == 2:
                printing_list = ["v_F_Overview"]

            else:
                raise Exception("Report {0} not supported".format(is_print))

        headers = {
            "v_F_Overview_dict": [("Variable Name", "Documentation", "Unit", "Total")],
            "v_F_Piped_dict": [("Origin", "Destination", "Time", "Piped water")],
            "v_C_Piped_dict": [("Origin", "Destination", "Time", "Cost piping")],
            "v_F_Trucked_dict": [("Origin", "Destination", "Time", "Trucked water")],
            "v_C_Trucked_dict": [("Origin", "Destination", "Time", "Cost trucking")],
            "v_F_Sourced_dict": [
                ("Fresh water source", "Completion pad", "Time", "Sourced water")
            ],
            "v_C_Sourced_dict": [
                ("Fresh water source", "Completion pad", "Time", "Cost sourced water")
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
            "quality.v_Q_dict": [
                ("Location", "Water Component", "Time", "Water Quality")
            ],
            "v_F_DesalinatedWater_dict": [
                ("Treatment site", "Time", "Desalinated water removed from system")
            ],
            "v_F_ResidualWater_dict": [("Treatment site", "Time", "Residual Water")],
            "v_F_TreatedWater_dict": [("Treatment site", "Time", "Treated Water")],
            "v_F_StorageEvaporationStream_dict": [
                ("Storage site", "Time", "Evaporated Volume")
            ],
            "v_F_CompletionsDestination_dict": [
                ("Pads", "Time", "Total deliveries to completions pads")
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
            "v_S_TreatmentCapacity_dict": [
                ("Treatment site", "Slack Treatment Capacity")
            ],
            "v_S_ReuseCapacity_dict": [("Reuse site", "Slack Reuse Capacity")],
        }

        # Defining KPIs for strategic model
        model.reuse_WaterKPI = Var(doc="Reuse Fraction Produced Water [%]")
        if model.p_beta_TotalProd.value and model.v_F_TotalReused.value:
            reuseWater_value = value(
                (model.v_F_TotalReused / model.p_beta_TotalProd) * 100
            )
        else:
            reuseWater_value = 0
        model.reuse_WaterKPI.value = reuseWater_value

        model.disposal_WaterKPI = Var(doc="Disposal Fraction Produced Water [%]")
        if model.v_F_TotalDisposed.value and model.p_beta_TotalProd.value:
            disposalWater_value = value(
                (model.v_F_TotalDisposed / model.p_beta_TotalProd) * 100
            )
        else:
            disposalWater_value = 0
        model.disposal_WaterKPI.value = disposalWater_value

        model.fresh_CompletionsDemandKPI = Var(
            doc="Fresh Fraction Completions Demand [%]"
        )
        if model.v_F_TotalSourced.value and model.p_gamma_TotalDemand.value:
            freshDemand_value = value(
                (model.v_F_TotalSourced / model.p_gamma_TotalDemand) * 100
            )
        else:
            freshDemand_value = 0
        model.fresh_CompletionsDemandKPI.value = freshDemand_value

        model.reuse_CompletionsDemandKPI = Var(
            doc="Reuse Fraction Completions Demand [%]"
        )
        if model.v_F_TotalReused.value and model.p_gamma_TotalDemand.value:
            reuseDemand_value = value(
                (model.v_F_TotalReused / model.p_gamma_TotalDemand) * 100
            )
        else:
            reuseDemand_value = 0
        model.reuse_CompletionsDemandKPI.value = reuseDemand_value

    elif model.type == "operational":
        if len(is_print) == 0:
            printing_list = []
        else:
            # PrintValues.detailed: Slacks values included, Same as "All"
            if is_print[0].value == 0:
                printing_list = [
                    "v_F_Piped",
                    "v_F_Trucked",
                    "v_F_Sourced",
                    "v_F_PadStorageIn",
                    "v_L_ProdTank",
                    "v_F_PadStorageOut",
                    "v_C_Piped",
                    "v_C_Trucked",
                    "v_C_Sourced",
                    "v_C_Disposal",
                    "v_C_Reuse",
                    "v_L_Storage",
                    "vb_y_Pipeline",
                    "vb_y_Disposal",
                    "vb_y_Storage",
                    "vb_y_Truck",
                    "v_F_Drain",
                    "v_B_Production",
                    "vb_y_FLow",
                    "v_F_Overview",
                    "v_L_PadStorage",
                    "v_C_Treatment",
                    "v_C_Storage",
                    "v_R_Storage",
                    "v_S_FracDemand",
                    "v_S_Production",
                    "v_S_Flowback",
                    "v_S_PipelineCapacity",
                    "v_S_StorageCapacity",
                    "v_S_DisposalCapacity",
                    "v_S_TreatmentCapacity",
                    "v_S_ReuseCapacity",
                    "v_D_Capacity",
                    "v_X_Capacity",
                    "v_F_Capacity",
                ]

            # PrintValues.nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage
            elif is_print[0].value == 1:
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
                    "vb_y_Truck",
                    "vb_z_PadStorage",
                    "v_F_Overview",
                ]

            # PrintValues.essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
            elif is_print[0].value == 2:
                printing_list = ["v_F_Overview"]

            else:
                raise Exception("Report {0} not supported".format(is_print))

        headers = {
            "v_F_Overview_dict": [("Variable Name", "Documentation", "Unit", "Total")],
            "v_F_Piped_dict": [("Origin", "Destination", "Time", "Piped water")],
            "v_C_Piped_dict": [("Origin", "Destination", "Time", "Cost piping")],
            "v_F_Trucked_dict": [("Origin", "Destination", "Time", "Trucked water")],
            "v_C_Trucked_dict": [("Origin", "Destination", "Time", "Cost trucking")],
            "v_F_Sourced_dict": [
                ("Fresh water source", "Completion pad", "Time", "Sourced water")
            ],
            "v_C_Sourced_dict": [
                ("Fresh water source", "Completion pad", "Time", "Cost sourced water")
            ],
            "v_F_PadStorageIn_dict": [("Completion pad", "Time", "StorageIn")],
            "v_F_PadStorageOut_dict": [("Completion pad", "Time", "StorageOut")],
            "v_C_Disposal_dict": [("Disposal site", "Time", "Cost of disposal")],
            "v_C_Treatment_dict": [("Treatment site", "Time", "Cost of Treatment")],
            "v_C_Reuse_dict": [("Completions pad", "Time", "Cost of reuse")],
            "v_C_Storage_dict": [("Storage Site", "Time", "Cost of Storage")],
            "v_R_Storage_dict": [
                ("Storage Site", "Time", "Credit of Retrieving Produced Water")
            ],
            "v_C_PadStorage_dict": [("Completions Pad", "Time", "Cost of Pad Storage")],
            "v_L_Storage_dict": [("Storage site", "Time", "Storage Levels")],
            "v_L_PadStorage_dict": [("Completion pad", "Time", "Storage Levels")],
            "vb_y_Pipeline_dict": [
                ("Origin", "Destination", "Pipeline Diameter", "Pipeline Installation")
            ],
            "vb_y_Disposal_dict": [("Disposal Site", "Injection Capacity", "Disposal")],
            "vb_y_Storage_dict": [
                ("Storage Site", "Storage Capacity", "Storage Expansion")
            ],
            "vb_z_PadStorage_dict": [("Completions Pad", "Time", "Storage Use")],
            "vb_y_Flow_dict": [("Origin", "Destination", "Time", "Flow")],
            "vb_y_Truck_dict": [("Origin", "Destination", "Time", "Truck")],
            "v_D_Capacity_dict": [("Disposal Site", "Disposal Site Capacity")],
            "v_X_Capacity_dict": [("Storage Site", "Storage Site Capacity")],
            "v_F_Capacity_dict": [("Origin", "Destination", "Flow Capacity")],
            "v_F_ReuseDestination_dict": [
                ("Completion Pad", "Time", "Total Deliveries to Completion Pad")
            ],
            "v_F_DisposalDestination_dict": [
                ("Disposal Site", "Time", "Total Deliveries to Disposal Site")
            ],
            "v_F_TreatmentDestination_dict": [
                ("Disposal Site", "Time", "Total Deliveries to Disposal Site")
            ],
            "v_B_Production_dict": [
                ("Pads", "Time", "Produced Water For Transport From Pad")
            ],
            "v_F_UnusedTreatedWater_dict": [
                ("Treatment site", "Time", "Treatment Waste Water")
            ],
            "v_S_FracDemand_dict": [("Completion pad", "Time", "Slack FracDemand")],
            "v_S_Production_dict": [("Production pad", "Time", "Slack Production")],
            "v_S_Flowback_dict": [("Completion pad", "Time", "Slack Flowback")],
            "v_S_PipelineCapacity_dict": [
                ("Origin", "Destination", "Slack Pipeline Capacity")
            ],
            "v_S_StorageCapacity_dict": [("Storage site", "Slack Storage Capacity")],
            "v_S_DisposalCapacity_dict": [("Storage site", "Slack Disposal Capacity")],
            "v_S_TreatmentCapacity_dict": [
                ("Treatment site", "Slack Treatment Capacity")
            ],
            "v_S_ReuseCapacity_dict": [("Reuse site", "Slack Reuse Capacity")],
        }
        # Detect if the model has equalized or individual production tanks
        if model.config.production_tanks == ProdTank.equalized:
            headers.update(
                {"v_L_ProdTank_dict": [("Pads", "Time", "Production Tank Water Level")]}
            )
            headers.update(
                {
                    "v_F_Drain_dict": [
                        ("Pads", "Time", "Produced Water Drained From Production Tank")
                    ]
                }
            )
        elif model.config.production_tanks == ProdTank.individual:
            headers.update(
                {
                    "v_L_ProdTank_dict": [
                        ("Pads", "Tank", "Time", "Production Tank Water Level")
                    ]
                }
            )
            headers.update(
                {
                    "v_F_Drain_dict": [
                        (
                            "Pads",
                            "Tank",
                            "Time",
                            "Produced Water Drained From Production Tank",
                        )
                    ]
                }
            )
        else:
            raise Exception(
                "Tank Type {0} is not supported".format(model.config.production_tanks)
            )
        if model.config.water_quality == WaterQuality.discrete:
            headers.update(
                {
                    "v_DQ_dict": [
                        (
                            "Location",
                            "Time",
                            "Water Component",
                            "Discrete Water Quality",
                            "Water Quality",
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
                    "v_Q_CompletionPad_dict": [
                        (
                            "Completion pad",
                            "Water Component",
                            "Time",
                        )
                    ],
                }
            )
        elif model.config.water_quality == WaterQuality.post_process:
            headers.update(
                {
                    "v_Q_dict": [
                        ("Location", "Water Component", "Time", "Water Quality")
                    ],
                }
            )
    else:
        raise Exception("Model type {0} is not supported".format(model.type))

    # Loop through all the variables in the model
    for variable in model.component_objects(Var):
        # Not all of our variables have units (binary variables)
        units_true = variable.get_units() is not None
        # If units are used, determine what the display units should be based off user input
        if units_true:
            from_unit_string = variable.get_units().to_string()
            # the display units (to_unit) is defined by output_units from module parameter
            if output_units == OutputUnits.unscaled_model_units:
                to_unit = model.model_to_unscaled_model_display_units[from_unit_string]
            elif output_units == OutputUnits.user_units:
                to_unit = model.model_to_user_units[from_unit_string]
            else:
                print("ERROR: Report output units selected by user is not valid")
            # if variable data is not none and indexed, update headers to display unit
            if len(variable._data) > 1 and list(variable._data.keys())[0] is not None:
                header = list(headers[str(variable.name) + "_dict"][0])
                header[-1] = (
                    headers[str(variable.name) + "_dict"][0][-1]
                    + " ["
                    + to_unit.to_string().replace("oil_bbl", "bbl")
                    + "]"
                )
                headers[str(variable.name) + "_dict"][0] = tuple(header)
        else:
            to_unit = None
        if variable._data is not None:
            # Loop through the indices of a variable. "i" is a tuple of indices
            for i in variable._data:
                # convert the value to display units
                if units_true and variable._data[i].value:
                    var_value = pyunits.convert_value(
                        variable._data[i].value,
                        from_units=variable.get_units(),
                        to_units=to_unit,
                    )
                else:
                    var_value = variable._data[i].value

                if i is None:
                    # Create the overview report with variables that are not indexed, e.g.:
                    # total piped water, total trucked water, total fresh water, etc.
                    if to_unit is not None:
                        headers["v_F_Overview_dict"].append(
                            (
                                variable.name,
                                variable.doc,
                                to_unit.to_string().replace("oil_bbl", "bbl"),
                                var_value,
                            )
                        )
                    else:
                        headers["v_F_Overview_dict"].append(
                            (variable.name, variable.doc, to_unit, var_value)
                        )

                # if a variable contains only one index, then "i" is recognized as a string and not a tuple,
                # in that case, "i" is redefined by adding a comma so that it becomes a tuple
                elif i is not None and isinstance(i, str):
                    i = (i,)
                # replace the discrete qualities by their actual values
                if str(variable.name) == "v_DQ" and var_value > 0:
                    var_value = model.p_discrete_quality[i[2], i[3]].value
                if i is not None and var_value is not None and var_value > 0:
                    headers[str(variable.name) + "_dict"].append((*i, var_value))

    if model.v_C_Slack.value is not None and model.v_C_Slack.value > 0:
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
    if len(printing_list) > 0 and model.proprietary_data is True:
        print(
            "\n**********************************************************************"
        )
        print("            WARNING: This report contains Proprietary Data            ")
        print("**********************************************************************")

    # Adding a footnote to the each dictionary indicating if the report contains Prorpietary Data
    if model.proprietary_data is True:
        for report in headers:
            if len(headers[report]) > 1:
                headers[report].append(("PROPRIETARY DATA",))

    # Creating the Excel report
    if fname is None:
        fname = "PARETO_report.xlsx"

    with pd.ExcelWriter(fname) as writer:
        for i in headers:
            df = pd.DataFrame(headers[i][1:], columns=headers[i][0])
            df.fillna("")
            df.to_excel(writer, sheet_name=i[: -len("_dict")], index=False, startrow=1)

    return model, headers


def plot_sankey(input_data={}, args=None):

    """
    This method receives data in the form of 3 separate lists (origin, destination, value lists), generate_report dictionary
    output format, or get_data dictionary output format. It then places this data into 4 lists of unique elements so that
    proper indexes can be assigned for each list so that the elements will correspond with each other based off of the indexes.
    These lists are then passed into the outlet_flow method which gives an output which is passed into the method to generate the
    sankey diagram.
    """
    # Suppress SettingWithCopyWarning because of false positives
    pd.options.mode.chained_assignment = None

    label = []
    check_list = ["source", "destination", "value"]
    is_sections = False

    if all(x in input_data.keys() for x in check_list):
        input_data["type_of_data"] = "Labels"
    elif "pareto_var" in input_data.keys():
        input_data["type_of_data"] = None
        variable = input_data["pareto_var"]
    else:
        raise Exception(
            "Input data is not valid. Either provide source, destination, value, or a pareto_var assigned to the key pareto_var"
        )

    if "sections" in input_data.keys():
        is_sections = True

    # Taking in the lists and assigning them to list variables to be used in the method
    if input_data["type_of_data"] == "Labels":
        source = input_data["source"]
        destination = input_data["destination"]
        value = input_data["value"]

        # Checking if a source and destination are the same and giving the destination a new name for uniqueness
        for n in range(len(source)):
            if source[n] == destination[n]:
                destination[n] = "{0}{1}".format(destination[n], "_TILDE")

    elif input_data["type_of_data"] is None and isinstance(variable, list):

        source = []
        destination = []
        value = []
        temp_variable = []
        temp_variable.append(variable[0])

        # Searching for the keyword "PROPRIETARY DATA"
        if "PROPRIETARY DATA" in variable[-1]:
            variable.pop()

        # Deleting zero values
        for i in variable[1:]:
            if i[-1] > 0:
                temp_variable.append(i)

        variable = temp_variable

        # # Calling handle_time method handles user input for specific time_periods and if the variable is indexed by time
        variable_updated = handle_time(variable, input_data)

        # Loop through dictionaries to be included in sankey diagrams
        for i in variable_updated[1:]:
            source.append(i[0])  # Add sources, values, and destinations to lists
            value.append(i[-1])
            if i[0] == i[1]:
                destination.append(
                    "{0}{1}".format(i[1], "_TILDE")
                )  # Add onto duplicate names so that they can be given a unique index

            else:
                destination.append(i[1])

    elif input_data["type_of_data"] is None and isinstance(variable, dict):
        source = []
        destination = []
        value = []

        formatted_list = []
        temp_variable = {}

        # Deleting zero values
        for key, val in variable.items():
            if val > 0:
                temp_variable.update({key: val})

        variable = temp_variable

        # Calling handle_time method handles user input for specific time_periods and if the variable is indexed by time
        variable_updated = handle_time(variable, input_data)

        # Formatting data into a list of tuples
        for v in variable_updated:
            formatted_list.append((*v, variable_updated[v]))

        if "PROPRIETARY DATA" in formatted_list[-1]:
            formatted_list.pop()

        # Adding sources, destinations, and values to respective lists from tuples
        for i in formatted_list:
            source.append(i[0])
            value.append(i[-1])
            if i[0] == i[1]:
                destination.append(
                    "{0}{1}".format(i[1], "_TILDE")
                )  # Add onto duplicate names so that they can be given a unique index
            else:
                destination.append(i[1])

    else:
        raise Exception(
            "Type of data {0} is not supported. Available options are Labels, get_data format, and generate_report format".format(
                type(variable)
            )
        )

    # Combine locations and cut out duplicates while maintaining same order
    total_labels = source + destination
    label = sorted(set(total_labels), key=total_labels.index)

    all_labels = label.copy()

    for s in source:
        for l in label:
            if s == l:
                s_index = label.index(l)
                for n, k in enumerate(source):
                    if k == s:
                        source[n] = s_index

    for d in destination:
        for l in label:
            if d == l:
                d_index = label.index(l)
                for m, j in enumerate(destination):
                    if j == d:
                        destination[m] = d_index

    # Remove added string from affected names before passing them into sankey method
    for t, x in enumerate(label):
        if x.endswith("_TILDE"):
            label[t] = x[: -len("_TILDE")]

    sum_dict = {"source": source, "destination": destination, "value": value}
    sum_df = pd.DataFrame(sum_dict)

    # Finding duplicates in dataframe and dropping them
    df_dup = sum_df[sum_df.duplicated(subset=["source", "destination"], keep=False)]
    df_dup = df_dup.drop_duplicates(subset=["source", "destination"], keep="first")

    # Looping through dataframe and summing the total values of each node and assigning it to its instance
    for index, row in df_dup.iterrows():
        new_value = 0
        new_value = sum_df.loc[
            (sum_df["source"] == row["source"])
            & (sum_df["destination"] == row["destination"]),
            "value",
        ].sum()
        sum_df.at[index, "value"] = new_value

    df_updated = sum_df.drop_duplicates(subset=["source", "destination"], keep="first")

    if is_sections:
        for key, val in input_data["sections"].items():
            for i, v in enumerate(val):
                try:
                    v_index = label.index(v)
                    val[i] = v_index
                except:
                    print(
                        "WARNING: {0} does not have a value for every specified time period and may not be shown in the sankey diagram.".format(
                            val[i]
                        )
                    )
                    pass

            val = [x for x in val if not isinstance(x, str)]
            df_section = df_updated[
                (df_updated["source"].isin(val) | df_updated["destination"].isin(val))
            ]
            source = df_section["source"].to_list()
            destination = df_section["destination"].to_list()
            value = df_section["value"].to_list()

            updated_label = outlet_flow(source, destination, label, value)

            args["section_name"] = key

            generate_sankey(source, destination, value, updated_label, args)
    else:
        source = df_updated["source"].to_list()
        destination = df_updated["destination"].to_list()
        value = df_updated["value"].to_list()

        updated_label = outlet_flow(source, destination, label, value)

        generate_sankey(source, destination, value, updated_label, args)


def handle_time(variable, input_data):
    """
    The handle_time method checks if a variable is indexed by time and checks if a user
    has passed in certain time periods they would like to use for the data. It then appends
    those rows of data with the specified time value to a new list which is returned in the
    plot_sankey method.
    """
    # Checks the type of data that is passed in and if it is indexed by time
    indexed_by_time = False
    if isinstance(variable, list):
        time_var = []
        for i in variable[:1]:
            i = [j.title() for j in i]
            if "Time" in i:
                indexed_by_time = True
        if indexed_by_time == True:
            if (
                "time_period" in input_data.keys()
            ):  # Checks if user passes in specific time periods they want used in the diagram, if none passed in then it returns original list
                for y in variable[1:]:
                    if y[-2] in input_data["time_period"]:
                        time_var.append((y))
                if len(time_var) == 0:
                    raise Exception(
                        "The time period the user provided does not exist in the data"
                    )
                else:
                    return time_var
            else:
                return variable
        else:
            return variable
    else:
        time_var = {}
        if "labels" in input_data:
            for i in input_data["labels"]:
                i = [j.title() for j in i]
                if "Time" in i:
                    indexed_by_time = True
            if indexed_by_time == True:
                if (
                    "time_period" in input_data.keys()
                ):  # Checks if user passes in specific time periods they want used in the diagram, if none passed in then it returns original dictionary
                    for key, y in variable.items():
                        if key[-1] in input_data["time_period"]:
                            time_var.update({key: y})
                    if len(time_var) == 0:
                        raise Exception(
                            "The time period the user provided does not exist in the data"
                        )
                    else:
                        return time_var
                else:
                    return variable
            else:
                return variable
        else:
            raise Exception("User must provide labels when using Get_data format.")


def outlet_flow(source=[], destination=[], label=[], value=[], qualityDict=[]):
    """
    The outlet_flow method receives source, destination, label, and value lists and
    sums the total value for each label. This value is then added to the label string and
    updated label lists so that it can be displayed on each node as "label:value". This updated label
    list is output to be used in the generate_sankey method.
    """
    static_label = label.copy()

    # Loop through each list finding where labels match sources and destination and totaling/rounding their values to be used in updated label list
    for x, l in enumerate(label):
        output = 0
        v_count = []
        for s, g in enumerate(source):
            if g == x:
                v_count.append(s)
        if len(v_count) == 0:
            for d, h in enumerate(destination):
                if h == x:
                    v_count.append(d)
            if len(v_count) == 0:
                continue
        for v in v_count:
            output = output + float(value[v])
            rounded_output = round(output, 0)
            integer_output = int(rounded_output)

        value_length = len(str(integer_output))
        if value_length >= 4 and value_length <= 7:
            integer_output = str(int(int(rounded_output) / 1000)) + "k"
        elif value_length >= 8:
            integer_output = str(int(integer_output / 1000000)) + "M"
        label_string = "{0}:{1}".format(l, integer_output)
        if qualityDict:
            quality_output = str(int(qualityDict[l] / 1000)) + "k"
            label_string = "{0}:{1} TDS:{2}".format(l, integer_output, quality_output)

        static_label[x] = "{0}:{1}".format(l, integer_output)

    return static_label


def generate_sankey(source=[], destination=[], value=[], label=[], args=None):
    """
    This method receives the final lists for source, destination, value, and labels to be used
    in generating the plotly sankey diagram. It also receives arguments that determine font size and
    plot titles. It outputs the sankey diagram in an html format that is automatically opened
    in a browser.
    """
    format_checklist = ["jpg", "jpeg", "pdf", "png", "svg"]
    figure_output = ""

    # Checking arguments and assigning appropriate values
    if args is None:
        font_size = 20
        plot_title = "Sankey Diagram"
        figure_output = "first_sankey.html"
        jupyter_notebook = False
    else:
        if "font_size" not in args.keys() or args["font_size"] is None:
            font_size = 20
        else:
            font_size = args["font_size"]

        if "plot_title" not in args.keys() or args["plot_title"] is None:
            if "section_name" in args:
                plot_title = args["section_name"]
            else:
                plot_title = "Sankey Diagram"
        else:
            if "section_name" in args:
                plot_title = args["section_name"] + " " + args["plot_title"]
            else:
                plot_title = args["plot_title"]

        if "output_file" not in args.keys() or args["output_file"] is None:
            if "section_name" in args:
                figure_output = args["section_name"] + "_sankey.html"
            else:
                figure_output = "first_sankey.html"
        else:
            if "section_name" in args:
                figure_output = args["section_name"] + "_" + args["output_file"]
            else:
                figure_output = args["output_file"]

        if "jupyter_notebook" not in args.keys() or args["jupyter_notebook"] is None:
            jupyter_notebook = False
        else:
            jupyter_notebook = args["jupyter_notebook"]

    # Creating links and nodes based on the passed in lists to be used as the data for generating the sankey diagram
    link = dict(source=source, target=destination, value=value)
    node = dict(label=label, pad=30, thickness=15, line=dict(color="black", width=0.5))
    data = go.Sankey(link=link, node=node)

    # Assigning sankey diagram to fig variable
    fig = go.Figure(data)

    # Updating the layout of the sankey and formatting based on user passed in arguments
    fig.update_layout(
        title_font_size=font_size * 2,
        title_text=plot_title,
        title_x=0.5,
        font_size=font_size,
    )

    if ".html" in figure_output:
        fig.write_html(figure_output, auto_open=False)
    elif any(x in figure_output for x in format_checklist):
        fig.write_image(figure_output, height=850, width=1800)
    else:
        exception_string = ""
        for x in format_checklist:
            exception_string = exception_string + ", " + x
        raise Exception(
            "The file format provided is not supported. Please use either html{}.".format(
                exception_string
            )
        )
    if jupyter_notebook:
        iplot({"data": fig, "layout": fig.layout})


def plot_bars(input_data, args):
    """
    This method creates a bar chart based on a user passed in dictionary or list that is created from the get_data or generate_report methods.
    The dictionary or list is assigned to the key 'pareto_var' of the input_data dictionary and the method then determines the type of variable
    and proceeds accordingly. These variables are checked if they are indexed by time, if true then an animated bar chart is created, if false then
    a static bar chart is created. In addition to the input_data dictionary, another dictionary named 'args' is passed in containing arguments for customizing
    the bar chart. The args dictionary keys are 'plot_title', 'y_axis', 'group_by', and 'labels' which is only required if the variable is of get_data format(dictionary).
    The 'y_axis' key is optional and accepts the value 'log' which will take the logarithm of the y axis. If 'y_axis' is not passed in then the axis will default to linear.
    The 'group_by' key accepts a value that is equal to a column name of the variable data, this will specify which column to use for the x axis. Finally, the 'labels'
    key accepts a tuple of labels to be assigned to the get_data format(list) variable since no labels are provided from the get_data method.
    """
    # Suppress SettingWithCopyWarning because of false positives
    pd.options.mode.chained_assignment = None

    y_range = []
    tick_text = []
    time_list = []
    indexed_by_time = False
    date_time = False
    print_data = False
    format_checklist = ["jpg", "jpeg", "pdf", "png", "svg"]
    figure_output = ""
    jupyter_notebook = False

    if "output_file" not in args.keys() or args["output_file"] is None:
        figure_output = "first_bar.html"
    else:
        figure_output = args["output_file"]

    # Check for variable data and throw exception if no data is provided
    if "pareto_var" in input_data.keys():
        variable = input_data["pareto_var"]
    else:
        raise Exception(
            "Input data is not valid. Provide a pareto_var assigned to the key pareto_var"
        )

    # Give group_by a value of None/"" if it is not provided
    if "group_by" not in args.keys():
        args["group_by"] = None

    # Assign print_data to the user passed in value
    if "print_data" in args.keys():
        print_data = args["print_data"]

    if "plot_title" not in args.keys() or args["plot_title"] is None:
        plot_title = ""
    else:
        plot_title = args["plot_title"]

    # Check if log was passed in as an option for the y axis and create a boolean for it
    if "y_axis" not in args.keys():
        log_y = False
        yaxis_type = "linear"
    elif args["y_axis"] == "log":
        log_y = True
        yaxis_type = "log"
    else:
        raise Warning("Y axis type {} is not supported".format(args["y_axis"]))

    if "jupyter_notebook" not in args.keys() or args["jupyter_notebook"] is None:
        jupyter_notebook = False
    else:
        jupyter_notebook = args["jupyter_notebook"]

    # Check the type of variable passed in and assign labels/Check for time indexing
    if isinstance(variable, list):
        for i in variable[:1]:
            i = [j.title() for j in i]
            if args["group_by"] == "" or args["group_by"] is None:
                x_title = i[0]
                y_title = i[-1]
            elif args["group_by"].title() in i:  # add default group_by as first column
                y_title = i[-1]
                x_title = args["group_by"].title()
            if "Time" in i:
                indexed_by_time = True
                time = "Time"

        # Searching for the keyword "PROPRIETARY DATA"
        if "PROPRIETARY DATA" in variable[-1]:
            variable.pop()

        formatted_variable = variable[1:]
    elif isinstance(variable, dict):
        formatted_list = []

        for v in variable:
            formatted_list.append((*v, variable[v]))

        if input_data["labels"] is not None:
            for i in input_data["labels"]:
                i = [j.title() for j in i]
                if args["group_by"] == "" or args["group_by"] is None:
                    x_title = i[0]
                    y_title = i[-1]
                elif args["group_by"].title() in i:
                    y_title = i[-1]
                    x_title = args["group_by"].title()
                if "Time" in i:
                    indexed_by_time = True
                    time = "Time"
        else:
            raise Exception("User must provide labels when using Get_data format.")

        formatted_variable = formatted_list
    else:
        raise Exception(
            "Type of data {0} is not supported. Valid data formats are list and dictionary".format(
                type(variable)
            )
        )

    if indexed_by_time:
        # Create dataframes for use in the method
        df = pd.DataFrame(columns=i)
        df_bar = df[[x_title, time, y_title]]

        df_new = pd.DataFrame(formatted_variable, columns=i)
        df_new = df_new.round(0)
        df_modified = df_new[[x_title, time, y_title]]

        char_checklist = ["/", "-"]
        removed_char = ""
        if any(x in df_modified[time][0] for x in char_checklist):
            df_modified[time] = pd.to_datetime(df_modified[time]).dt.date
            date_time = True
        else:
            removed_char = df_modified[time][0][:1]
            df_modified[time] = df_modified[time].apply(lambda x: x.strip(removed_char))
            df_modified[time] = df_modified[time].apply(lambda x: pd.to_numeric(x))

        for d, y in df_modified.iterrows():
            time_list.append(y[time])
        time_loop = set(time_list)
        time_loop = sorted(time_loop)

        # Loop through time list and give any nodes without a value for that time a 0
        for ind, x in df_modified.iterrows():
            time_value = df_modified.loc[df_modified[x_title] == x[x_title], time]
            for t in time_loop:
                if t not in time_value.values:
                    df_modified.loc[len(df_modified.index)] = [x[x_title], t, 1e-10]

        # Take the sums of flows from nodes to destinations that have the same time period and locations
        df_dup = df_modified[df_modified.duplicated(subset=[x_title, time], keep=False)]
        df_dup = df_dup.drop_duplicates(subset=[x_title, time], keep="first")
        for index, row in df_dup.iterrows():
            new_value = 0
            new_value = df_modified.loc[
                (df_modified[x_title] == row[x_title])
                & (df_modified[time] == row[time]),
                y_title,
            ].sum()
            df_modified.at[index, y_title] = new_value

        df_bar = df_modified.drop_duplicates(subset=[x_title, time], keep="first")

        # Get all y values and then calculate the max for the y axis range
        for a, b in df_bar.iterrows():
            y_range.append(b[y_title])
            tick_text.append(b[x_title])

        for y, x in enumerate(y_range):
            y_range[y] = float(x)

        max_y = max(y_range)

        # Sort by time and x values
        df_time_sort = df_bar.sort_values(by=[time, x_title])

        # If time is of type datetime, convert to string for figure processing
        if date_time:
            df_time_sort[time] = df_time_sort[time].apply(lambda x: str(x))
        else:
            df_time_sort[time] = df_time_sort[time].apply(
                lambda x: removed_char + str(x)
            )

        # Create bar chart with provided data and parameters
        fig = px.bar(
            df_time_sort,
            x=x_title,
            y=y_title,
            color=x_title,
            animation_frame=time,
            range_y=[1, max_y * 1.02],
            title=plot_title,
            log_y=log_y,
        )

        fig.update_layout(
            font_color="#fff",
            paper_bgcolor="#333",
            plot_bgcolor="#ccc",
        )

        # Update animation settings
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 800
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["redraw"] = False
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 1000
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["easing"] = "linear"

        if print_data:
            # Printing dataframe that is used in bar chart
            with pd.option_context(
                "display.max_rows",
                None,
                "display.max_columns",
                None,
                "display.precision",
                1,
            ):
                print(df_time_sort)

        # Write the figure to html format and open in the browser
        if ".html" in figure_output:
            fig.write_html(figure_output, auto_open=False, auto_play=False)
        elif any(x in figure_output for x in format_checklist):
            fig.write_image(figure_output, height=850, width=1800)
        else:
            exception_string = ""
            for x in format_checklist:
                exception_string = exception_string + ", " + x
            raise Exception(
                "The file format provided is not supported. Please use either html{}.".format(
                    exception_string
                )
            )
        if jupyter_notebook:
            iplot({"data": fig, "layout": fig.layout}, auto_play=False)
    else:

        # Create dataframe for use in the method
        df_new = pd.DataFrame(formatted_variable, columns=i)

        # Take the sums of flows from nodes to destinations that have the same locations
        df_modified = df_new[df_new.duplicated(subset=[x_title], keep=False)]
        for index, row in df_modified.iterrows():
            new_value = 0
            new_value = df_modified.loc[
                df_modified[x_title] == row[x_title], y_title
            ].sum()
            df_new.at[index, y_title] = new_value

        df_new_updated = df_new.drop_duplicates(subset=[x_title], keep="first")

        # Get all values and then calculate the max for the y axis range
        for a, b in df_new_updated.iterrows():
            y_range.append(b[y_title])

        for y, x in enumerate(y_range):
            y_range[y] = float(x)

        max_y = max(y_range)

        # Create bar chart with provided data and parameters
        fig = px.bar(
            df_new_updated,
            x=x_title,
            y=y_title,
            range_y=[0, max_y * 1.02],
            color=x_title,
            title=plot_title,
            text=y_title,
        )

        fig.update_layout(
            font_color="#fff",
            paper_bgcolor="#333",
            plot_bgcolor="#ccc",
            yaxis_type=yaxis_type,
        )

        if print_data:
            # Printing dataframe that is used in bar chart
            with pd.option_context(
                "display.max_rows",
                None,
                "display.max_columns",
                None,
                "display.precision",
                1,
            ):
                print(df_new_updated)

        if ".html" in figure_output:
            fig.write_html(figure_output, auto_open=False)
        elif any(x in figure_output for x in format_checklist):
            fig.write_image(figure_output, height=850, width=1800)
        else:
            exception_string = ""
            for x in format_checklist:
                exception_string = exception_string + ", " + x
            raise Exception(
                "The file format provided is not supported. Please use either html{}.".format(
                    exception_string
                )
            )
        if jupyter_notebook:
            iplot({"data": fig, "layout": fig.layout})


def plot_scatter(input_data, args):

    """
    The plot_scatter method creates a scatter plot based on two variables that are assigned to x and y,
    and a dictionary of arguments including labels, size specifications, group by and chart title. The variables
    that are passed in can be of type list (generate_report format) and of type dictionary (get_data format). Labels and
    size arguments are then interpreted/assigned appropriately to create the scatter plots. This method will produce two different
    kinds of scatter plots depending on if the variables are indexed by time or not. If they are indexed by time, an animated plot
    will be created, if they are not indexed by time, a static plot will be created. Before the manipulation and framing of this data
    is completed, missing values in the datasets are detected and mitigated by giving them a value of 0 if none is provided. The size argument
    is then sorted out either by calculating the ratio that the user provided as 'y/x' or 'x/y', or taking the variable that was provided
    for the size argument and assigning those size values to their respective rows. Once these data modifications are completed, the scatter plot
    is created with the data and arguments that are provided.
    """
    # Suppress SettingWithCopyWarning because of false positives
    pd.options.mode.chained_assignment = None

    y_range = []
    x_range = []
    time_list = []
    category_list = []
    indexed_by_time = False
    provided_size = False
    is_list = False
    is_dict = False
    s_variable = None
    date_time = False
    print_data = False
    group_by_category = False
    category_variable = None
    size = "Size"
    format_checklist = ["jpg", "jpeg", "pdf", "png", "svg"]
    figure_output = ""
    jupyter_notebook = False

    # Checks if output_file has been passed in as a user argument
    if "output_file" not in args.keys() or args["output_file"] is None:
        figure_output = "first_scatter_plot.html"
    else:
        figure_output = args["output_file"]

    # Give group_by and plot_title a value of None/"" if it is not provided
    if "group_by" not in args.keys():
        args["group_by"] = None

    if "plot_title" not in args.keys() or args["plot_title"] is None:
        plot_title = ""
    else:
        plot_title = args["plot_title"]

    # Assigns boolean variable to True if labels have been provided in the arguments
    check_list = ["labels_x", "labels_y"]
    if all(x in input_data.keys() for x in check_list):
        has_labels = True
    else:
        has_labels = False

    # Assign print_data to the user passed in value
    if "print_data" in args.keys():
        print_data = args["print_data"]

    # Checking for size argument and checking the type
    if "size" in input_data.keys():
        s_variable = input_data["size"]
        provided_size = True
        if isinstance(s_variable, list):
            is_list = True
        elif isinstance(s_variable, dict):
            is_dict = True

    # Check if group by category argument was provided
    if "group_by_category" in args.keys():
        if isinstance(args["group_by_category"], bool):
            group_by_category = args["group_by_category"]
        elif isinstance(args["group_by_category"], dict):
            category_variable = args["group_by_category"]
            for c in category_variable:
                category_list.append((c, category_variable[c]))
            df_category = pd.DataFrame(category_list, columns=["Node", "Category"])
        elif isinstance(args["group_by_category"], list):
            category_variable = args["group_by_category"][1:]
            df_category = pd.DataFrame(category_variable, columns=["Node", "Category"])
        else:
            raise Exception(
                'Invalid type for argument "group_by_category". Must be of type boolean, list variable or dictionary variable.'
            )

    if "jupyter_notebook" not in args.keys() or args["jupyter_notebook"] is None:
        jupyter_notebook = False
    else:
        jupyter_notebook = args["jupyter_notebook"]

    variable_x = input_data["pareto_var_x"]
    variable_y = input_data["pareto_var_y"]

    if isinstance(variable_x, list) and isinstance(variable_y, list):
        for i, g in zip(variable_x[:1], variable_y[:1]):
            i = [j.title() for j in i]
            g = [l.title() for l in g]
        x_title = i[-1]
        y_title = g[-1]
        if args["group_by"] is not None:
            col_1 = args["group_by"]
        else:
            col_1 = i[0]
        if "Time" in i and "Time" in g:
            indexed_by_time = True
            time = "Time"
        elif "Time" not in i and "Time" not in g:
            indexed_by_time = False
        else:
            raise Exception(
                "Cannot create scatter plot unless BOTH variables are/are not indexed by time"
            )

        # Searching for the keyword "PROPRIETARY DATA"
        if "PROPRIETARY DATA" in variable_x[-1]:
            variable_x.pop()

        # Searching for the keyword "PROPRIETARY DATA"
        if "PROPRIETARY DATA" in variable_y[-1]:
            variable_y.pop()

        formatted_variable_x = variable_x[1:]
        formatted_variable_y = variable_y[1:]

        # If size is provided in the form of a list, grab labels for size and check if indexed by time compared to x and y variables
        if provided_size and is_list:
            for s in s_variable[:1]:
                s = [j.title() for j in s]
            s_title = s[-1]
            if indexed_by_time and "Time" not in s:
                raise Exception(
                    "Both x and y variables are indexed by time. Size variable must also be indexed by time to create scatter plot."
                )
            s_variable = s_variable[1:]
    elif isinstance(variable_x, dict) and isinstance(variable_y, dict):
        formatted_list_x = []
        formatted_list_y = []
        v_tuples = []

        # Get a list of tuples which are the keys from both variables, Example => ('N01','N05','T01')
        for t in variable_x:
            v_tuples.append(t)
        for u in variable_y:
            v_tuples.append(u)

        v_tuples = list(set(v_tuples))

        # Use list of tuples to find any missing rows and assign value of 0
        for tup in v_tuples:
            if tup not in variable_x:
                variable_x[tup] = 0
            if tup not in variable_y:
                variable_y[tup] = 0

        for l, k in zip(variable_x, variable_y):
            formatted_list_x.append((*l, variable_x[l]))
            formatted_list_y.append((*k, variable_y[k]))
        if has_labels:
            for i in input_data["labels_x"]:
                i = [j.title() for j in i]
            x_title = i[-1]
            for g in input_data["labels_y"]:
                g = [r.title() for r in g]
            y_title = g[-1]
            if args["group_by"] is not None:
                col_1 = args["group_by"]
            else:
                col_1 = i[0]
            if "Time" in i and "Time" in g:
                indexed_by_time = True
                time = "Time"
            elif "Time" not in i and "Time" not in g:
                indexed_by_time = False
            else:
                raise Exception(
                    "Cannot create scatter plot unless BOTH variables are/are not indexed by time"
                )
        else:
            raise Exception(
                "User must provide labels for both x and y when using Get_data format."
            )
        formatted_variable_x = formatted_list_x
        formatted_variable_y = formatted_list_y

        # If size is provided in the form of a dictionary, grab labels for size and check if indexed by time compared to x and y variables
        if provided_size and is_dict:
            size_list = []
            for v in s_variable:
                size_list.append((*v, s_variable[v]))
            s_variable = size_list
            if "labels_size" in input_data.keys():
                for s in input_data["labels_size"]:
                    s = [k.title() for k in s]
                s_title = s[-1]
                if indexed_by_time and "Time" not in s:
                    raise Exception(
                        "Both x and y variables are indexed by time. Size variable must also be indexed by time to create scatter plot."
                    )
            else:
                raise Exception("User must provide labels for the size variable ")
    else:
        raise Exception(
            "Type of data {0} or {1} is not supported. Available options are list and dictionary. Both variables must be the same type of data.".format(
                type(variable_x), type(variable_y)
            )
        )

    if indexed_by_time:

        # Creating dataframe based on the passed in variable and rounding the values
        df_new_x = pd.DataFrame(formatted_variable_x, columns=i)
        df_new_x = df_new_x.round(0)
        df_modified_x = df_new_x[[col_1, time, x_title]]

        df_new_y = pd.DataFrame(formatted_variable_y, columns=g)
        df_new_y = df_new_y.round(0)
        df_modified_y = df_new_y[[col_1, time, y_title]]

        # Check if time period is in datetime format or in letter number format
        char_checklist = ["/", "-"]
        removed_char = ""
        if any(x in df_modified_x[time][0] for x in char_checklist):
            df_modified_x[time] = pd.to_datetime(df_modified_x[time]).dt.date
            df_modified_y[time] = pd.to_datetime(df_modified_y[time]).dt.date
            date_time = True
        else:
            removed_char = df_modified_x[time][0][:1]
            df_modified_x[time] = df_modified_x[time].apply(
                lambda x: x.strip(removed_char)
            )
            df_modified_y[time] = df_modified_y[time].apply(
                lambda x: x.strip(removed_char)
            )

            df_modified_x[time] = df_modified_x[time].apply(lambda x: pd.to_numeric(x))
            df_modified_y[time] = df_modified_y[time].apply(lambda x: pd.to_numeric(x))

        # Creates time list from data frame to be used to assign values to nodes without values for each time frame
        for d, y in df_modified_x.iterrows():
            time_list.append(y[time])
        for c, f in df_modified_y.iterrows():
            time_list.append(f[time])

        time_loop = set(time_list)
        time_loop = sorted(time_loop)

        # Loop through time list and give any nodes without a value for that time a value of 0
        for x_ind, x in df_modified_x.iterrows():
            time_value = df_modified_x.loc[df_modified_x[col_1] == x[col_1], time]
            x_vals = [z for z in time_loop if z not in time_value.values]
            for t in x_vals:
                df_modified_x.loc[len(df_modified_x.index)] = [x[col_1], t, 0.0]

        for y_ind, u in df_modified_y.iterrows():
            time_value = df_modified_y.loc[df_modified_y[col_1] == u[col_1], time]
            y_vals = [z for z in time_loop if z not in time_value.values]
            for t in y_vals:
                df_modified_y.loc[len(df_modified_y.index)] = [u[col_1], t, 0.0]

        # Finding duplicates in dataframe and dropping them
        df_dup_x = df_modified_x[
            df_modified_x.duplicated(subset=[col_1, time], keep=False)
        ]
        df_dup_y = df_modified_y[
            df_modified_y.duplicated(subset=[col_1, time], keep=False)
        ]

        df_dup_x = df_dup_x.drop_duplicates(subset=[col_1, time], keep="first")
        df_dup_y = df_dup_y.drop_duplicates(subset=[col_1, time], keep="first")

        # Looping through dataframe and summing the total values of each node and assigning it to its instance
        for index, row in df_dup_x.iterrows():
            new_x_value = 0
            new_x_value = df_modified_x.loc[
                (df_modified_x[col_1] == row[col_1])
                & (df_modified_x[time] == row[time]),
                x_title,
            ].sum()
            df_modified_x.at[index, x_title] = new_x_value

        for y_index, y_row in df_dup_y.iterrows():
            new_y_value = 0
            new_y_value = df_modified_y.loc[
                (df_modified_y[col_1] == y_row[col_1])
                & (df_modified_y[time] == y_row[time]),
                y_title,
            ].sum()
            df_modified_y.at[y_index, y_title] = new_y_value

        # Dropping new duplicates
        df_modified_x = df_modified_x.drop_duplicates(
            subset=[col_1, time], keep="first"
        )
        df_modified_y = df_modified_y.drop_duplicates(
            subset=[col_1, time], keep="first"
        )

        # Add y value column then add the value for that node
        df_modified_x[y_title] = 0
        for x_indx, x_df_row in df_modified_x.iterrows():
            y_value = 0
            y_value = df_modified_y.loc[
                (df_modified_y[col_1] == x_df_row[col_1])
                & (df_modified_y[time] == x_df_row[time]),
                y_title,
            ]
            df_modified_x.at[x_indx, y_title] = y_value

        # Add size column and calculate the ratio or grab the size from the variable passed in for size
        df_modified_x[size] = 0
        if isinstance(s_variable, str):  # provided_size == False or
            for s_indx, s_df_row in df_modified_x.iterrows():
                s_value = 0
                s_xvalue = 0
                s_yvalue = 0
                s_xvalue = df_modified_x.loc[
                    (df_modified_x[col_1] == s_df_row[col_1])
                    & (df_modified_x[time] == s_df_row[time]),
                    x_title,
                ]
                s_yvalue = df_modified_x.loc[
                    (df_modified_x[col_1] == s_df_row[col_1])
                    & (df_modified_x[time] == s_df_row[time]),
                    y_title,
                ]
                if s_variable == "y/x":
                    if float(s_xvalue) == 0 and float(s_yvalue) == 0:
                        s_value = 0.0
                    elif float(s_xvalue) == float(s_yvalue):
                        s_value = s_value + 1
                    else:
                        if float(s_xvalue) > float(s_yvalue):
                            s_value = s_value + (s_yvalue / s_xvalue) * 1000
                        else:
                            s_value = s_value + (s_yvalue / s_xvalue)
                elif s_variable == "x/y":
                    if float(s_xvalue) == 0 and float(s_yvalue) == 0:
                        s_value = 0.0
                    elif float(s_xvalue) == float(s_yvalue):
                        s_value = s_value + 1
                    else:
                        if float(s_yvalue) > float(s_xvalue):
                            s_value = s_value + (s_xvalue / s_yvalue) * 1000
                        else:
                            s_value = s_value + (s_xvalue / s_yvalue)
                else:
                    raise Exception(
                        "Possible size options are y/x or x/y to compute the size ratio. Provide a valid size ratio option or a variable to be used for the size."
                    )
                try:
                    df_modified_x.at[s_indx, size] = s_value
                except:
                    raise Exception(
                        "Size value returned an error or was not properly calculated based on {0} ratio provided. Please review size data provided or enter a new ratio.".format(
                            s_variable
                        )
                    )

        elif is_dict or is_list:
            df_size = pd.DataFrame(s_variable, columns=s)
            df_size = df_size.round(0)
            df_modified_size = df_size[[col_1, time, s_title]]

            if any(x in df_modified_size[time][0] for x in char_checklist):
                df_modified_size[time] = pd.to_datetime(df_modified_size[time]).dt.date
            else:
                df_modified_size[time] = df_modified_size[time].apply(
                    lambda x: x.strip(removed_char)
                )
                df_modified_size[time] = df_modified_size[time].apply(
                    lambda x: pd.to_numeric(x)
                )

            # Finding duplicates in dataframe and dropping them
            df_dup_size = df_modified_size[
                df_modified_size.duplicated(subset=[col_1, time], keep=False)
            ]

            df_dup_size = df_dup_size.drop_duplicates(
                subset=[col_1, time], keep="first"
            )

            # Looping through dataframe and summing the total values of each node and assigning it to its instance
            for size_index, size_row in df_dup_size.iterrows():
                new_size_value = 0
                new_size_value = df_modified_size.loc[
                    (df_modified_size[col_1] == size_row[col_1])
                    & (df_modified_size[time] == size_row[time]),
                    s_title,
                ].sum()
                df_modified_size.at[size_index, s_title] = new_size_value

            # Dropping new duplicates
            df_modified_size = df_modified_size.drop_duplicates(
                subset=[col_1, time], keep="first"
            )

            # Assigning new size value to the correct row in the modified x variable dataframe
            for s_indx, s_df_row in df_modified_size.iterrows():
                s_value = 0
                s_value = df_modified_size.loc[
                    (df_modified_size[col_1] == s_df_row[col_1])
                    & (df_modified_size[time] == s_df_row[time]),
                    s_title,
                ].values[0]
                x_index = df_modified_x.loc[
                    (df_modified_x[col_1] == s_df_row[col_1])
                    & (df_modified_x[time] == s_df_row[time])
                ].index
                df_modified_x.at[x_index, size] = s_value

        # Looping through updated dataframe and assigning all y and x values to a list
        for a, b in df_modified_x.iterrows():
            y_range.append(b[y_title])
            x_range.append(b[x_title])

        # Converting y values to a float data type
        for y, x in enumerate(y_range):
            y_range[y] = float(x)

        # Converting x values to a float data type
        for z, w in enumerate(x_range):
            x_range[z] = float(w)

        # Getting the max y and x value from y and x value lists
        max_y = max(y_range)
        max_x = max(x_range)

        # Sorting dataframe by time so that the animation plays in order
        df_scatter = df_modified_x.sort_values(by=[time, col_1])

        # Convert time periods to strings and append removed letter if time is not of type datetime
        if date_time:
            df_scatter[time] = df_scatter[time].apply(lambda x: str(x))
        else:
            df_scatter[time] = df_scatter[time].apply(lambda x: removed_char + str(x))

        # Categorize by color
        if category_variable is not None:
            df_category["Category"] = df_category["Category"].apply(lambda x: str(x))
            df_scatter["Color"] = ""
            for c_index, c_df_row in df_category.iterrows():
                category_num = c_df_row["Category"]
                scatter_indxs = df_scatter.loc[
                    df_scatter[col_1] == c_df_row["Node"]
                ].index.tolist()
                for s_index in scatter_indxs:
                    df_scatter.at[s_index, "Color"] = category_num
        else:
            if group_by_category:
                df_scatter["Color"] = ""
                category_char = ""
                for row_ind, row in df_scatter.iterrows():
                    category_char = row[col_1][:1]
                    df_scatter.at[row_ind, "Color"] = category_char
            else:
                df_scatter["Color"] = col_1

        # Make sure all values in the Color column are of type string
        df_scatter["Color"] = df_scatter["Color"].apply(lambda x: str(x))

        fig = px.scatter(
            df_scatter,
            x=x_title,
            y=y_title,
            animation_frame=time,
            animation_group=col_1,
            size=size,
            size_max=65,
            opacity=0.8,
            color="Color",
            color_discrete_sequence=px.colors.qualitative.T10,
            hover_name=col_1,
            range_x=[0, max_x * 1.02],
            range_y=[0, max_y * 1.02],
            title=plot_title,
        )

        # Formatting the colors of the layout
        fig.update_layout(font_color="#fff", paper_bgcolor="#333", plot_bgcolor="#ccc")

        # Update the size of the markers if user did not provide size
        if provided_size == False:
            for x in fig.frames:
                for i in x.data:
                    i["marker"]["size"] = 30

        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 800
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["redraw"] = False
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 1000
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["easing"] = "linear"

        if print_data:
            # Printing dataframe that is used in scatter plot
            with pd.option_context(
                "display.max_rows",
                None,
                "display.max_columns",
                None,
                "display.precision",
                1,
            ):
                print(df_scatter)

        # Writing figure to desired format
        if ".html" in figure_output:
            fig.write_html(figure_output, auto_open=False, auto_play=False)
        elif any(x in figure_output for x in format_checklist):
            fig.write_image(figure_output, height=850, width=1800)
        else:
            exception_string = ""
            for x in format_checklist:
                exception_string = exception_string + ", " + x
            raise Exception(
                "The file format provided is not supported. Please use either html{}.".format(
                    exception_string
                )
            )
        if jupyter_notebook:
            iplot({"data": fig, "layout": fig.layout}, auto_play=False)

    else:
        # Creating dataframe based on the passed in variable and rounding the values
        df_new_x = pd.DataFrame(formatted_variable_x, columns=i)
        df_new_x = df_new_x.round(0)
        df_modified_x = df_new_x[[col_1, x_title]]

        df_new_y = pd.DataFrame(formatted_variable_y, columns=g)
        df_new_y = df_new_y.round(0)
        df_modified_y = df_new_y[[col_1, y_title]]

        # Looping through dataframe and summing the total values of each node and assigning it to its instance
        df_dup_x = df_modified_x[df_modified_x.duplicated(subset=[col_1], keep=False)]
        df_dup_y = df_modified_y[df_modified_y.duplicated(subset=[col_1], keep=False)]

        df_dup_x = df_dup_x.drop_duplicates(subset=[col_1], keep="first")
        df_dup_y = df_dup_y.drop_duplicates(subset=[col_1], keep="first")

        # Looping through dataframe and summing the total values of each node and assigning it to its instance
        for index, row in df_dup_x.iterrows():
            new_x_value = 0
            new_x_value = df_modified_x.loc[
                (df_modified_x[col_1] == row[col_1]), x_title
            ].sum()
            df_modified_x.at[index, x_title] = new_x_value

        for y_index, y_row in df_dup_y.iterrows():
            new_y_value = 0
            new_y_value = df_modified_y.loc[
                (df_modified_y[col_1] == y_row[col_1]), y_title
            ].sum()
            df_modified_y.at[y_index, y_title] = new_y_value

        # Dropping new duplicates
        df_modified_x = df_modified_x.drop_duplicates(subset=[col_1], keep="first")
        df_modified_y = df_modified_y.drop_duplicates(subset=[col_1], keep="first")

        # Add y value column then add the value for that node
        df_modified_x[y_title] = 0
        for x_indx, x_df_row in df_modified_x.iterrows():
            y_value = 0
            y_value = df_modified_y.loc[
                (df_modified_y[col_1] == x_df_row[col_1]), y_title
            ]
            df_modified_x.at[x_indx, y_title] = y_value

        # Add size column and calculate the ratio
        df_modified_x[size] = 0
        if isinstance(s_variable, str):
            for s_indx, s_df_row in df_modified_x.iterrows():
                s_value = 0
                s_xvalue = 0
                s_yvalue = 0
                s_xvalue = df_modified_x.loc[
                    (df_modified_x[col_1] == s_df_row[col_1]), x_title
                ]
                s_yvalue = df_modified_x.loc[
                    (df_modified_x[col_1] == s_df_row[col_1]), y_title
                ]
                if s_variable == "y/x":
                    if float(s_xvalue) == 0 and float(s_yvalue) == 0:
                        s_value = 0.0
                    elif float(s_xvalue) == float(s_yvalue):
                        s_value = s_value + 1
                    else:
                        if float(s_xvalue) > float(s_yvalue):
                            s_value = s_value + (s_yvalue / s_xvalue) * 1000
                        else:
                            s_value = s_value + (s_yvalue / s_xvalue)
                elif s_variable == "x/y":
                    if float(s_xvalue) == 0 and float(s_yvalue) == 0:
                        s_value = 0.0
                    elif float(s_xvalue) == float(s_yvalue):
                        s_value = s_value + 1
                    else:
                        if float(s_yvalue) > float(s_xvalue):
                            s_value = s_value + (s_xvalue / s_yvalue) * 1000
                        else:
                            s_value = s_value + (s_xvalue / s_yvalue)
                else:
                    raise Exception(
                        "Possible size options are y/x or x/y to compute the size ratio. Provide a valid size ratio option or a variable to be used for the size."
                    )
                try:
                    df_modified_x.at[s_indx, size] = s_value
                except:
                    raise Exception(
                        "Size value returned an error or was not properly calculated based on {0} ratio provided. Please review size data provided or enter a new ratio.".format(
                            s_variable
                        )
                    )

        elif is_dict or is_list:
            df_size = pd.DataFrame(s_variable, columns=s)
            df_size = df_size.round(0)
            df_modified_size = df_size[[col_1, s_title]]

            # Finding duplicates in dataframe and dropping them
            df_dup_size = df_modified_size[
                df_modified_size.duplicated(subset=[col_1], keep=False)
            ]

            df_dup_size = df_dup_size.drop_duplicates(subset=[col_1], keep="first")

            # Looping through dataframe and summing the total values of each node and assigning it to its instance
            for size_index, size_row in df_dup_size.iterrows():
                new_size_value = 0
                new_size_value = df_modified_size.loc[
                    (df_modified_size[col_1] == size_row[col_1]), s_title
                ].sum()
                df_modified_size.at[size_index, s_title] = new_size_value

            # Dropping new duplicates
            df_modified_size = df_modified_size.drop_duplicates(
                subset=[col_1], keep="first"
            )

            # Assigning new size value to the correct row in the modified x variable dataframe
            for s_indx, s_df_row in df_modified_size.iterrows():
                s_value = df_modified_size.loc[
                    (df_modified_size[col_1] == s_df_row[col_1]), s_title
                ]
                x_index = df_modified_x.loc[
                    (df_modified_x[col_1] == s_df_row[col_1])
                ].index
                df_modified_x.at[x_index, size] = s_value

        # Looping through updated dataframe and assigning all y and x values to a list
        for a, b in df_modified_x.iterrows():
            y_range.append(b[y_title])
            x_range.append(b[x_title])

        # Converting y values to a float data type
        for y, x in enumerate(y_range):
            y_range[y] = float(x)

        # Converting x values to a float data type
        for z, w in enumerate(x_range):
            x_range[z] = float(w)

        # Getting the max y and x value from y and x value lists
        max_y = max(y_range)
        max_x = max(x_range)

        # Sorting dataframe by time so that the animation plays in order
        df_scatter = df_modified_x.sort_values(by=[col_1])

        # Categorize by color
        if category_variable is not None:
            df_category["Category"] = df_category["Category"].apply(lambda x: str(x))
            df_scatter["Color"] = ""
            for c_index, c_df_row in df_category.iterrows():
                category_num = c_df_row["Category"]
                scatter_indxs = df_scatter.loc[
                    df_scatter[col_1] == c_df_row["Node"]
                ].index.tolist()
                for s_index in scatter_indxs:
                    df_scatter.at[s_index, "Color"] = category_num
        else:
            if group_by_category:
                df_scatter["Color"] = ""
                category_char = ""
                for row_ind, row in df_scatter.iterrows():
                    category_char = row[col_1][:1]
                    df_scatter.at[row_ind, "Color"] = category_char
            else:
                df_scatter["Color"] = col_1

        # Make sure all values in the Color column are of type string
        df_scatter["Color"] = df_scatter["Color"].apply(lambda x: str(x))

        fig = px.scatter(
            df_scatter,
            x=x_title,
            y=y_title,
            size=size,
            size_max=65,
            opacity=0.8,
            color="Color",
            color_discrete_sequence=px.colors.qualitative.T10,
            hover_name=col_1,
            range_x=[0, max_x * 1.02],
            range_y=[0, max_y * 1.02],
            title=plot_title,
        )

        # Formatting the colors of the layout
        fig.update_layout(font_color="#fff", paper_bgcolor="#333", plot_bgcolor="#ccc")

        # Update the size of the markers if user did not provide size
        if provided_size == False:
            fig.update_traces(marker=dict(size=24))

        if print_data:
            # Printing dataframe that is used in scatter plot
            with pd.option_context(
                "display.max_rows",
                None,
                "display.max_columns",
                None,
                "display.precision",
                1,
            ):
                print(df_scatter)

        # Writing figure to desired format
        if ".html" in figure_output:
            fig.write_html(figure_output, auto_open=False)
        elif any(x in figure_output for x in format_checklist):
            fig.write_image(figure_output, height=850, width=1800)
        else:
            exception_string = ""
            for x in format_checklist:
                exception_string = exception_string + ", " + x
            raise Exception(
                "The file format provided is not supported. Please use either html{}.".format(
                    exception_string
                )
            )
        if jupyter_notebook:
            iplot({"data": fig, "layout": fig.layout})
