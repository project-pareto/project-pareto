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
Run utilities:
Functions mainly used in run_optimal_desalination.py
This also contains the solving function.
"""

import numpy as np
import pyomo.environ as pyo
from pareto.models_extra.CM_module.models.qcp_br import build_qcp_br

from pareto.utilities.get_data import get_data
from pareto.models_extra.CM_module.cm_utils.gen_utils import (
    report_results_to_excel,
    alter_nonlinear_cons,
)
from pareto.models_extra.CM_module.cm_utils.data_parser import data_parser, _tolist

from importlib import resources
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import sys
from pareto.utilities.solvers import get_solver


def load_data(fpath):
    # importing data
    [df_sets, df_parameters] = get_data(fpath, model_type="critical_mineral")

    data = data_parser(df_sets, df_parameters)
    return data


def print_results_summary(model):
    print(f"Arc cost:                       {pyo.value(model.arc_cost):>12.0f}")
    print(f"Disposal cost:                  {pyo.value(model.disp_cost):>12.0f}")
    print(f"Freshwater cost:                {pyo.value(model.fresh_cost):>12.0f}")
    print(f"Treatment cost:                 {pyo.value(model.treat_cost):>12.0f}")
    print(f"Storage cost:                   {pyo.value(model.stor_cost):>12.0f}")
    print(f"Storage revenue:                {pyo.value(model.stor_rev):>12.0f}")
    print(f"Critical Mineral revenue:       {pyo.value(model.treat_rev):>12.0f}")
    print(
        f"Beneficial Reuse Revenue:       {(pyo.value(model.ben_reuse_net_cost)*(-1)):>12.0f}"
    )
    print(f"Net cost:                       {pyo.value(model.total_cost_w_br):>12.0f}")


def plot_compare_nodes(values, stat_type, axis):
    """
    Creates a bar graph comparing nodes for different model statistics,
    sorted based on total cost

    Function Arguments:
    values: a tuple (node_name, value) consisting of the name of the node (node_name) and its associated value
    for the given statistic (value)
    stat_type: a string describing which kind of statistic this graph is about (Arc cost, Disposal cost, etc.)
    axis: the matplotlib bar graph where the data will be represented

    Function Outputs:
    None
    """

    labels, counts = [node[0] for node in values], [node[1] for node in values]

    # creates gradient of colors
    multip = 1 / len(values)
    colors = [(x * multip, 0, 1 - x * multip, 1) for x in range(len(values))]

    axis.bar(labels, counts, color=colors)
    xticks = np.arange(len(labels))
    axis.set_xticks(xticks, labels, rotation="vertical")
    axis.set_title(stat_type)
    axis.set_ylabel("Dollars")

    # adjusting break in y-axis depending on maximum and minimum values
    if min(counts) < 0:
        axis.set_ylim(bottom=min(counts) * 1.02, top=max(counts) * 0.95)
    else:
        axis.set_ylim(min(counts) * 0.98)

    # red symbolizes lowest total cost, blue represents highest
    red_patch = mpatches.Patch(color="blue", label="Lowest Total Cost")
    blue_patch = mpatches.Patch(color="red", label="Highest Total Cost")
    axis.legend(handles=[red_patch, blue_patch])


def plot_comparisons(values, sorted_total_costs):
    """
    creates a large plot that consists of all the different model statistics based on different
    nodes chosen

    Function Arguments:
    values: a dictionary {node_num : {statistic : value}} consisting of node numbers and their
    associated statistics (arc cost, disposal cost, etc.) and values
    sorted_total_costs: a list of tuples [(node_num, total_cost_with_node)] consisting of the node numbers
    and their associated total costs

    Function Outputs:
    None
    """

    # create 8 plots
    figs, axs = plt.subplots(2, 4)
    figs.set_size_inches(27, 15)

    plot_titles = [
        "Arc cost",
        "Disposal cost",
        "Freshwater cost",
        "Treatment cost",
        "Storage cost",
        "Storage revenue",
        "Critical Mineral revenue",
        "\nNet cost",
    ]

    sorted_total_costs_dict = {x[0]: x[1] for x in sorted_total_costs}

    # creates the invidiual plots based on chosen model stat
    for plot_row in range(2):
        for plot_col in range(4):
            current_title = plot_titles[plot_row * 4 + plot_col]

            # create list of tuples with (node_number, value) for associated statistic, then sort based
            # on arrangement of nodes when sorted for total cost
            cost_type_values = [
                (node_num, values[node_num][current_title]) for node_num in values
            ]
            sorted_station_values = sorted(
                cost_type_values, key=lambda x: sorted_total_costs_dict[x[0]]
            )

            plot_compare_nodes(
                sorted_station_values, current_title, axs[plot_row][plot_col]
            )

    plt.tight_layout()
    plt.savefig("desal_comparison_plot.png")


def change_piping_connection(data, base, old, new, pipe_in):
    """
    changes the piping connection to a different location through editing the data

    Function Arguments:
    data: the dictionary comprised of the values taken from an excel sheet
    base: a string with the name of the location that will not be changed
    old: a string with the name of the old location, which base will no longer be connected to
    new: a string with the name of the new location, which base will now be connected to
    pipe_in: a bool that determines whether base is getting piped into or piped out of

    Function Outputs:
    data: updated dictionary with the changes reflected
    """

    pipe_in = True
    suffix = "A"

    # case for when the arc that is being changed is being piped into the base
    if pipe_in:
        # edit arc data
        new_arc = new[0] + base[0] + suffix
        old_arc = old[0] + base[0] + suffix
        data[new_arc][(new, base)] = 1
        data[old_arc].pop((old, base))

        # edit operational cost data
        data["PipelineOperationalCost"][(new, base)] = data["PipelineOperationalCost"][
            (old, base)
        ]
        data["PipelineOperationalCost"][(old, base)] = 0

        # edit initial pipeline capacity data
        data["InitialPipelineCapacity"][new, base] = data["InitialPipelineCapacity"][
            old, base
        ]
        data["InitialPipelineCapacity"][old, base] = 0

    # case for when the arc that is being changed is being piped out of the base
    else:
        # edit arc data
        new_arc = base[0] + new[0] + suffix
        old_arc = base[0] + old[0] + suffix
        data[new_arc][(base, new)] = 1
        data[old_arc].pop((base, old))

        # edit operational cost data
        data["PipelineOperationalCost"][(base, new)] = data["PipelineOperationalCost"][
            (base, old)
        ]
        data["PipelineOperationalCost"][(base, old)] = 0

        # edit initial pipeline capacity data
        data["InitialPipelineCapacity"][base, new] = data["InitialPipelineCapacity"][
            base, old
        ]
        data["InitialPipelineCapacity"][base, old] = 0

    return data


def node_rerun(df_sets, df_parameters, treatment_site="R01", max_iterations=3000):
    """
    builds the models with different arc connections and runs them through the solver, printing
    the resutls and displaying a graph for comparison

    Function Arguments:
    df_sets: a dictionary containing the various sets and their respective sites found within the model
    df_parameters: a dictionary containing the parameters of the model, including the arcs, capacities, and costs
    treatment_site: the selected treatment site that will have its connections changed

    Function Outputs:
    min_node: returns the node which resulted in the smallest total cost for the model
    models: a dictionary containing entries with node_number and their corresponding models
    """

    data = data_parser(df_sets, df_parameters)

    # building model
    model = build_qcp_br(data)
    models = dict()

    print("\n\n\nmaking new models\n")

    prev_node = model.s_Ain[treatment_site + "_IN"][0][0]  # calling previous node

    # Looping through all the treatment sites and changing which node is being used
    for node in df_sets["NetworkNodes"].tolist():
        print(f"model {node} being made...")
        # creates new paramter data with the selected node
        new_param_data = change_piping_connection(
            df_parameters, treatment_site, prev_node, node, pipe_in=True
        )
        new_data = data_parser(df_sets, new_param_data)
        new_model = build_qcp_br(new_data)
        # adds the new_model to the list of models
        models[node] = new_model
        # sets previous node to the
        prev_node = node

    print("\nmodels generated\n\n\n")

    final_values = dict()
    for node_num in models:
        print(f"\n\nRunning {node_num}\n")
        # runs each model through and solves for optimal solution
        solved_model, values = solving(models[node_num], max_iterations)
        # appends final data to be displayed later
        final_values[node_num] = values

    for node_num, model in models.items():
        print(f"\n---- Treatment at node: {node_num} ----\n")
        if pyo.check_optimal_termination(model.status):
            print_results_summary(model)
        else:
            print(f"... no feasible solution found in {max_iterations} iterations")

    # grabs total cost of every node
    total_costs = [(value, final_values[value]["\nNet cost"]) for value in final_values]
    sorted_costs = sorted(total_costs, key=lambda x: x[1])

    sorted_costs_nozero = [
        (value, total_cost) for (value, total_cost) in sorted_costs if total_cost > 1e-4
    ]
    min_node, min_cost = sorted_costs_nozero[0]

    # plot comparisons between nodes
    plot_comparisons(final_values, sorted_costs)

    # plot schematic

    # print node with smallest total cost
    print(
        f"\nNode {min_node} had the smallest total cost, which amounted to {min_cost}."
    )

    return min_node, models


def solving(
    model,
    max_iterations=3000,
    tee=False,
    inf_recs=False,
):
    """
    This function solves the model in the following manner:
    Flow LP -> bilinear NLP
    After solving a summary report of the cost breakdown
    and the model itself is returned.

    Conc LP and 0 flows fixed NLP solves have been commented out.
    If required these sections can be uncommented and used to initialize
    to the final bilinear NLP

    Arguments:
    model: The model to run
    max_iterations: The maximum number of iterations ipopt will run for

    Returns:
    model: Solved model
    values: Dictionary of broken down costs
    """
    # # ------------------------------Flow based LP------------------------------------

    # fixing concentration and making the model linear
    model = alter_nonlinear_cons(model, deactivate=True)

    # running linear flow model
    print("\nDeveloping an initialization...")
    opt = get_solver("ipopt")
    status = opt.solve(model, tee=False)
    term_cond = pyo.check_optimal_termination(status)
    if not term_cond:
        print(
            "Linear model is infeasible. This likely means the production flow exceeds the disposal and treatment capacities."
        )

    # unfixing all the initialized variables
    model = alter_nonlinear_cons(model, deactivate=False)

    # running bilinear model
    print("\nSolving bilinear problem...")
    opt = get_solver("ipopt")

    opt.options["max_iter"] = max_iterations
    status = opt.solve(model, tee=tee)
    model.status = status

    # ------------------------------Results------------------------------------

    # showing results
    term_cond = pyo.check_optimal_termination(status)
    if term_cond == True:
        print("\n Successfully solved model")
        # Displaying specific broken down costs
        print_results_summary(model)

        # returning specific broken down costs
        value_strings = [
            "Arc cost",
            "Disposal cost",
            "Freshwater cost",
            "Treatment cost",
            "Storage cost",
            "Storage revenue",
            "Critical Mineral revenue",
            "\nNet cost",
        ]

        values = [
            model.arc_cost,
            model.disp_cost,
            model.fresh_cost,
            model.treat_cost,
            model.stor_cost,
            model.stor_rev,
            model.treat_rev,
            model.br_obj() * 1000,
        ]
        values = [pyo.value(x) for x in values]
        values = {name: value for name, value in zip(value_strings, values)}
        return model, values

    # returning values of 0s if model was not feasible
    else:
        print("Model is Infeasible")
        value_strings = [
            "Arc cost",
            "Disposal cost",
            "Freshwater cost",
            "Treatment cost",
            "Storage cost",
            "Storage revenue",
            "Critical Mineral revenue",
            "\nNet cost",
        ]

        values = [0, 0, 0, 0, 0, 0, 0, 0 * 1000]

        if inf_recs:
            print(
                "The model is infeasible. Some possible reasons for infeasibility:\n"
                "1. The minimum CM recovery concentration is too high given the existing infrastructure and parameters\n"
                "2. The produced water concentration is too low to meet minimum CM concentration requirements\n"
                "3. The treatment efficiency is not sufficient to meet the minimum CM concentration\n"
                "Suggestion to improve feasibility: Allow installation of pipelines for direct transportation of water from high CM concentration production pads to desalination sites\n"
            )

        return model, {name: value for name, value in zip(value_strings, values)}
