##############################################################################
#
##############################################################################
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


def plot_sankey(input_data={}, args=None):

    """
    This method receives data in the form of 3 seperate lists (origin, destination, value lists), generate_report dictionary
    output format, or get_data dictionary output format. It then places this data into 4 lists of unique elements so that
    proper indexes can be assigned for each list so that the elements will correspond with each other based off of the indexes.
    These lists are then passed into the outlet_flow method which gives an output which is passed into the method to generate the
    sankey diagram.
    """
    label = []
    check_list = ["source", "destination", "value"]
    if all(x in input_data.keys() for x in check_list):
        input_data["type_of_data"] = "Labels"

    elif "pareto_var" in input_data.keys():
        input_data["type_of_data"] = None
        variable = input_data["pareto_var"]

    else:
        raise Exception(
            "Input data is not valid. Either provide source, destination, value, or a pareto_var assigned to the key pareto_var"
        )

    # if "plot_title" in args.keys():
    #     if "time_period" in input_data.keys():
    #         args["plot_title"] = "{0} for {1}".format(
    #             args["plot_title"], input_data["time_period"]
    #         )

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

    # Loop through source and destination lists and replace values with proper index indicated from the label list
    for s in source:
        for d in destination:
            for l in label:
                if s == l:
                    s_index = label.index(l)
                    for n, k in enumerate(source):
                        if k == s:
                            source[n] = s_index
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


def outlet_flow(source=[], destination=[], label=[], value=[]):
    """
    The outlet_flow method receives source, destination, label, and value lists and
    sums the total value for each label. This value is then added to the label string and
    updated label lists so that it can be displayed on each node as "label:value". This updated label
    list is output to be used in the generate_sankey method.
    """
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
        for v in v_count:
            output = output + float(value[v])
            rounded_output = round(output, 0)
            integer_output = int(rounded_output)

        value_length = len(str(integer_output))
        if value_length >=4 and value_length<=7:
            integer_output = str(int(integer_output/1000)) + 'k'
        elif value_length >= 8:
            integer_output = str(int(integer_output/1000000)) + 'M'

        label[x] = "{0}:{1}".format(l, integer_output)

    return label


def generate_sankey(source=[], destination=[], value=[], label=[], args=None):
    """
    This method receives the final lists for source, destination, value, and labels to be used
    in generating the plotly sankey diagram. It also receives arguments that determine font size and
    plot titles. It outputs the sankey diagram in an html format that is automatically opened
    in a browser.
    """
    # Checking arguments and assigning appropriate values
    if args is None:
        font_size = 20
        plot_title = "Sankey Diagram"
    elif args["font_size"] is None:
        font_size = 20
    elif args["plot_title"] is None:
        plot_title = "Sankey Diagram"
    else:
        font_size = args["font_size"]
        plot_title = args["plot_title"]

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

    fig.write_html("first_figure.html", auto_open=True)


def plot_bars(variable, args):

    y_range = []
    tick_text = []
    time_list = []
    indexed_by_time = False

    if "group_by" not in args.keys():
        args["group_by"] = None

    if args["chart_title"] == '' or args["group_by"] is None:
        chart_title = ''
    else:
        chart_title = args["chart_title"]


    if args['labels'] is None:
        for i in variable[:1]:
            i = [j.title() for j in i]
            if args["group_by"] == '' or args["group_by"] is None:
                x_title = i[0]
                y_title = i[-1]
                if 'Time' in i:
                    indexed_by_time = True
                    time = 'Time'
            elif args["group_by"].title() in i:     # add default group_by as first column
                y_title = i[-1]
                x_title = args["group_by"].title()
                if 'Time' in i:
                    indexed_by_time = True
                    time = 'Time'
        formatted_variable = variable[1:]
    else:
        formatted_list = []

        for v in variable:
            formatted_list.append((*v, variable[v]))

        for i in args['labels']:
            i = [j.title() for j in i]
            x_title = i[0]
            y_title = i[-1]
            if 'Time' in i:
                indexed_by_time = True
                time = 'Time'

        formatted_variable = formatted_list

    
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

        #Loop through time list and give any nodes without a value for that time a 0
        for ind, x in df_modified.iterrows():
            time_value = df_modified.loc[df_modified[x_title] == x[x_title], time]
            for t in time_loop:
                if t not in time_value.values:
                    df_modified.loc[len(df_modified.index)] = [x[x_title], t, 0.0] 

        df_dup = df_modified[df_modified.duplicated(subset=[x_title,time], keep=False)]
        df_dup = df_dup.drop_duplicates(subset=[x_title, time], keep='first')
        for index, row in df_dup.iterrows():
            new_value = 0
            new_value = df_modified.loc[(df_modified[x_title] == row[x_title]) & (df_modified[time] == row[time]), y_title].sum()
            df_modified.at[index, y_title] = new_value

        df_bar = df_modified.drop_duplicates(subset=[x_title, time], keep='first')

        for a, b in df_bar.iterrows():
                y_range.append(b[y_title])
                tick_text.append(b[x_title])

        for y,x in enumerate(y_range):
            y_range[y] = float(x)

        max_y = max(y_range)

        df_time_sort = df_bar.sort_values(by=[time, x_title])

        fig = px.bar(df_time_sort, x=x_title, y=y_title, color=x_title, animation_frame=time, text=y_title, 
            range_y=[0, max_y*1.02], title=chart_title)

        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside', textfont_color='black', textfont_size=16)

        fig.update_layout(font_color='#fff', paper_bgcolor='#333', plot_bgcolor='#ccc') 
        
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 200  
        # fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["easing"] = 'linear' 
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["redraw"] = False                          
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 1000   
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["easing"] = 'linear'                      

        # with pd.option_context('display.max_rows', None, 'display.max_columns', None,'display.precision', 1):  
        #     print(df_time_sort)

        fig.write_html('first_bar.html', auto_open=True, auto_play=False)
    else:

        df_new = pd.DataFrame(variable[1:], columns=i)

        df_modified = df_new[df_new.duplicated(subset=[x_title], keep=False)]
        for index, row in df_modified.iterrows():
            new_value = 0
            new_value = df_modified.loc[df_modified[x_title] == row[x_title], y_title].sum()
            df_new.at[index, y_title] = new_value

        df_new_updated = df_new.drop_duplicates(subset=[x_title], keep='first')

        for a, b in df_new_updated.iterrows():
                y_range.append(b[y_title])

        for y,x in enumerate(y_range):
            y_range[y] = float(x)

        max_y = max(y_range)

        fig = px.bar(df_new_updated, x=x_title, y=y_title, range_y=[0, max_y*1.02], color=x_title, title=chart_title, text=y_title)

        fig.update_layout(font_color='#fff', paper_bgcolor='#333', plot_bgcolor='#ccc')

        # with pd.option_context('display.max_rows', None, 'display.max_columns', None,'display.precision', 1):  
        #     print(df_new_updated)

        fig.write_html('first_bar.html', auto_open=True)