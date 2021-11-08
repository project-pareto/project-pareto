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
)
from pyomo.environ import Var
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from enum import Enum


class PrintValues(Enum):
    Detailed = 0
    Nominal = 1
    Essential = 2


def generate_report(model, is_print=[], fname=None):
    # ## Printing model sets, parameters, constraints, variable values ##

    printing_list = []

    if model.type == "strategic":
        if len(is_print) == 0:
            printing_list = []
        else:
            # PrintValues.Detailed: Slacks values included, Same as "All"
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
                ]

            # PrintValues.Nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage + etc.
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

            # PrintValues.Essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
            elif is_print[0].value == 2:
                printing_list = ["v_F_Overview"]

            else:
                raise Exception("Report {0} not supported".format(is_print))

        headers = {
            "v_F_Overview_dict": [("Variable Name", "Documentation", "Total")],
            "v_F_Piped_dict": [("Origin", "destination", "Time", "Piped water")],
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
                ("Treatment Site", "Treatment Capacity", "Treatment Expansion")
            ],
            "v_D_Capacity_dict": [("Disposal Site", "Disposal Site Capacity")],
            "v_T_Capacity_dict": [("Treatment Site", "Treatment Capacity")],
            "v_X_Capacity_dict": [("Storage Site", "Storage Site Capacity")],
            "v_F_Capacity_dict": [("Origin", "Destination", "Flow Capacity")],
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
            "v_F_ReuseDestination_dict": [
                ("Completion Pad", "Time", "Total Deliveries to Completion Pad")
            ],
            "v_F_DisposalDestination_dict": [
                ("Disposal Site", "Time", "Total Deliveries to Disposal Site")
            ],
        }

        # Defining KPIs for strategic model
        model.reuse_WaterKPI = Var(doc="Reuse Fraction Produced Water = [%]")
        reuseWater_value = (
            (model.v_F_TotalReused.value) / (model.p_beta_TotalProd.value) * 100
        )
        model.reuse_WaterKPI.value = reuseWater_value

        model.disposal_WaterKPI = Var(doc="Disposal Fraction Produced Water = [%]")
        disposalWater_value = (
            (model.v_F_TotalDisposed.value) / (model.p_beta_TotalProd.value) * 100
        )
        model.disposal_WaterKPI.value = disposalWater_value

        model.fresh_CompletionsDemandKPI = Var(
            doc="Fresh Fraction Completions Demand = [%]"
        )
        freshDemand_value = (
            (model.v_F_TotalSourced.value) / (model.p_gamma_TotalDemand.value) * 100
        )
        model.fresh_CompletionsDemandKPI.value = freshDemand_value

        model.reuse_CompletionsDemandKPI = Var(
            doc="Reuse Fraction Completions Demand = [%]"
        )
        reuseDemand_value = (
            (model.v_F_TotalReused.value) / (model.p_gamma_TotalDemand.value) * 100
        )
        model.reuse_CompletionsDemandKPI.value = reuseDemand_value

    elif model.type == "operational":
        if len(is_print) == 0:
            printing_list = []
        else:
            # PrintValues.Detailed: Slacks values included, Same as "All"
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

            # PrintValues.Nominal: Essential + Trucked water + Piped Water + Sourced water + vb_y_pipeline + vb_y_disposal + vb_y_storage
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
                    "v_F_Overview",
                ]

            # PrintValues.Essential: Just message about slacks, "Check detailed results", Overview, Economics, KPIs
            elif is_print[0].value == 2:
                printing_list = ["v_F_Overview"]

            else:
                raise Exception("Report {0} not supported".format(is_print))

        headers = {
            "v_F_Overview_dict": [("Variable Name", "Documentation", "Total")],
            "v_F_Piped_dict": [("Origin", "destination", "Time", "Piped water")],
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
            "vb_y_Truck_dict": [("Origin", "Destination", "Time", "Truck")],
            "v_D_Capacity_dict": [("Disposal Site", "Disposal Site Capacity")],
            "v_X_Capacity_dict": [("Storage Site", "Storage Site Capacity")],
            "v_F_Capacity_dict": [("Origin", "Destination", "Flow Capacity")],
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
        }

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

    else:
        raise Exception("Model type {0} is not supported".format(model.type))

    for variable in model.component_objects(Var):
        if variable._data is not None:
            for i in variable._data:
                var_value = variable._data[i].value
                if i is None:
                    headers["v_F_Overview_dict"].append(
                        (variable.name, variable.doc, var_value)
                    )
                elif i is not None and isinstance(i, str):
                    i = (i,)
                if i is not None and var_value is not None and var_value > 0:
                    headers[str(variable.name) + "_dict"].append((*i, var_value))

    if model.v_C_Slack.value is not None and model.v_C_Slack.value > 0:
        print("!!!ATTENTION!!! One or several slack variables have been triggered!")

    for i in list(headers.items())[1:]:
        dict_name = i[0][: -len("_dict")]
        if dict_name in printing_list:
            print("\n", "=" * 10, dict_name.upper(), "=" * 10)
            print(i[1][0])
            for j in i[1][1:]:
                print("{0}{1} = {2}".format(dict_name, j[:-1], j[-1]))

    # Loop for printing Overview Information
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
                    print("{0} = {1}".format(j[1], j[2]))

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


def plot_bars(input_data, args):

    y_range = []
    tick_text = []
    time_list = []
    indexed_by_time = False

    if "pareto_var" in input_data.keys():
        variable = input_data["pareto_var"]
    else:
        raise Exception(
            "Input data is not valid. Provide a pareto_var assigned to the key pareto_var"
        )

    if "group_by" not in args.keys():
        args["group_by"] = None

    if args["chart_title"] == "" or args["group_by"] is None:
        chart_title = ""
    else:
        chart_title = args["chart_title"]

    if "y_axis" not in args.keys():
        log_y = False
        yaxis_type = "linear"
    elif args["y_axis"] == "log":
        log_y = True
        yaxis_type = "log"
    else:
        raise Warning("Y axis type {} is not supported".format(args["y_axis"]))

    if isinstance(variable, list):
        for i in variable[:1]:
            i = [j.title() for j in i]
            if args["group_by"] == "" or args["group_by"] is None:
                x_title = i[0]
                y_title = i[-1]
                if "Time" in i:
                    indexed_by_time = True
                    time = "Time"
            elif args["group_by"].title() in i:  # add default group_by as first column
                y_title = i[-1]
                x_title = args["group_by"].title()
                if "Time" in i:
                    indexed_by_time = True
                    time = "Time"
        formatted_variable = variable[1:]
    elif isinstance(variable, dict):
        formatted_list = []

        for v in variable:
            formatted_list.append((*v, variable[v]))

        if args["labels"] is not None:
            for i in args["labels"]:
                i = [j.title() for j in i]
                x_title = i[0]
                y_title = i[-1]
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

        df = pd.DataFrame(columns=i)
        df_bar = df[[x_title, time, y_title]]

        df_new = pd.DataFrame(formatted_variable, columns=i)
        df_new = df_new.round(0)
        df_modified = df_new[[x_title, time, y_title]]

        for d, y in df_new.iterrows():
            time_list.append(y[time])
        time_loop = set(time_list)
        time_loop = sorted(time_loop)

        # Loop through time list and give any nodes without a value for that time a 0
        for ind, x in df_modified.iterrows():
            time_value = df_modified.loc[df_modified[x_title] == x[x_title], time]
            for t in time_loop:
                if t not in time_value.values:
                    df_modified.loc[len(df_modified.index)] = [x[x_title], t, 1e-10]

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

        for a, b in df_bar.iterrows():
            y_range.append(b[y_title])
            tick_text.append(b[x_title])

        for y, x in enumerate(y_range):
            y_range[y] = float(x)

        max_y = max(y_range)

        df_time_sort = df_bar.sort_values(by=[time, x_title])

        fig = px.bar(
            df_time_sort,
            x=x_title,
            y=y_title,
            color=x_title,
            animation_frame=time,
            range_y=[1, max_y * 1.02],
            title=chart_title,
            log_y=log_y,
        )

        fig.update_layout(
            font_color="#fff",
            paper_bgcolor="#333",
            plot_bgcolor="#ccc",
        )

        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 200
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["redraw"] = False
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 1000
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["easing"] = "linear"

        fig.write_html("first_bar.html", auto_open=True, auto_play=False)
    else:

        df_new = pd.DataFrame(variable[1:], columns=i)

        df_modified = df_new[df_new.duplicated(subset=[x_title], keep=False)]
        for index, row in df_modified.iterrows():
            new_value = 0
            new_value = df_modified.loc[
                df_modified[x_title] == row[x_title], y_title
            ].sum()
            df_new.at[index, y_title] = new_value

        df_new_updated = df_new.drop_duplicates(subset=[x_title], keep="first")

        for a, b in df_new_updated.iterrows():
            y_range.append(b[y_title])

        for y, x in enumerate(y_range):
            y_range[y] = float(x)

        max_y = max(y_range)

        fig = px.bar(
            df_new_updated,
            x=x_title,
            y=y_title,
            range_y=[0, max_y * 1.02],
            color=x_title,
            title=chart_title,
            text=y_title,
        )

        fig.update_layout(
            font_color="#fff",
            paper_bgcolor="#333",
            plot_bgcolor="#ccc",
            yaxis_type=yaxis_type,
        )

        fig.write_html("first_bar.html", auto_open=True)