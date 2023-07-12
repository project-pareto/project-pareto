#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2023 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################
from pareto.utilities.results import plot_sankey
from pareto.utilities.get_data import get_data
from importlib import resources
import pytest

headers_test = {}
source = []
destination = []
value = []


@pytest.fixture(scope="module")
def input_data():
    # Calling plot_sankey using the get_data format
    # User needs to provide a tuple with labels for each column of the pareto_var
    set_list = []
    parameter_list = ["test_plot_sankey"]

    with resources.path("pareto.tests", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var": df_parameters["test_plot_sankey"],
        "labels": [("Origin", "Destination", "Time", "Value")],
    }


@pytest.fixture
def plot_args():
    return {
        "font_size": 15,
        "plot_title": "Total Flows",
        "output_file": "first_sankey.html",
    }  # 'jpg', 'jpeg', 'pdf', 'png', 'svg', 'html'


def test_plot_sankey_aggregated(input_data, plot_args):
    plot_sankey(input_data, args=plot_args)


@pytest.fixture
def plot_args_incorrect_file_format():
    return {
        "font_size": 15,
        "plot_title": "Total Flows",
        "output_file": "first_sankey.htlm",
    }


def test_plot_sankey_incorrect_file_format(input_data, plot_args_incorrect_file_format):
    with pytest.raises(Exception):
        plot_sankey(input_data, args=plot_args_incorrect_file_format)


@pytest.fixture(scope="module")
def input_data_single_period():
    # Calling plot_sankey using the get_data format
    # User needs to provide a tuple with labels for each column of the pareto_var
    set_list = []
    parameter_list = ["test_plot_sankey"]

    with resources.path("pareto.tests", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    # One or more specific time periods can be selected. plot_sankey calculates the totals and create the plot
    return {
        "pareto_var": df_parameters["test_plot_sankey"],
        "labels": [("Origin", "Destination", "Time", "Value")],
        "time_period": ["T01"],
    }


@pytest.fixture
def plot_args_single_period():
    return {
        "font_size": 15,
        "plot_title": "Flow for T01",
        "output_file": "first_sankey.html",
    }


def test_plot_sankey_single_period(input_data_single_period, plot_args_single_period):
    plot_sankey(input_data_single_period, args=plot_args_single_period)


@pytest.fixture(scope="module")
def input_data_multi_regions():
    # Calling plot_sankey using the get_data format
    # User needs to provide a tuple with labels for each column of the pareto_var
    set_list = []
    parameter_list = ["test_plot_sankey"]

    with resources.path("pareto.tests", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    # One or more specific time periods can be selected. plot_sankey calculates the totals and create the plot
    return {
        "pareto_var": df_parameters["test_plot_sankey"],
        "sections": {
            "Region_1": ["Appalachia", "West Virginia", "Ohio"],
            "Region_2": ["Washington, PA", "Company A", "Company B"],
        },
        "labels": [("Origin", "Destination", "Time", "Value")],
        "time_period": ["T01"],
    }


@pytest.fixture
def plot_args_multi_regions():
    return {
        "font_size": 15,
        "plot_title": "Flow for T01",
        "output_file": "first_sankey.html",
    }


def test_plot_sankey_multi_regions(input_data_multi_regions, plot_args_multi_regions):
    plot_sankey(input_data_multi_regions, args=plot_args_multi_regions)
