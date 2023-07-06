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
from pareto.utilities.get_data import get_data
from pareto.utilities.results import plot_bars
from importlib import resources
import pytest


@pytest.fixture(scope="module")
def input_data():
    set_list = []
    parameter_list = ["test_plot_bar"]

    with resources.path("pareto.tests", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var": df_parameters["test_plot_bar"],
        "labels": [("Origin", "Destination", "Time", "Value")],
    }


@pytest.fixture(scope="module")
def input_data_static():
    set_list = []
    parameter_list = ["test_plot_bar_static"]

    with resources.path("pareto.tests", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var": df_parameters["test_plot_bar_static"],
        "labels": [("Origin", "Destination", "Value")],
    }


@pytest.fixture
def plot_args():
    return {
        "plot_title": "Test Data",
        "output_file": "first_bar.html",
        "group_by": "Destination",
        "print_data": True,
    }  # 'jpg', 'jpeg', 'pdf', 'png', 'svg', 'html'


@pytest.fixture
def plot_args_incorrect_file_format():
    return {
        "plot_title": "Test Data",
        "output_file": "first_bar.htlm",
        "group_by": "Destination",
        "print_data": True,
    }


def test_plot_bars(input_data, plot_args):
    plot_bars(input_data, args=plot_args)


def test_plot_bars_incorrect_file_format(input_data, plot_args_incorrect_file_format):
    with pytest.raises(Exception):
        plot_bars(input_data, args=plot_args_incorrect_file_format)


def test_plot_bars_static(input_data_static, plot_args):
    plot_bars(input_data_static, args=plot_args)


def test_plot_bars_static_incorrect_file_format(
    input_data_static, plot_args_incorrect_file_format
):
    with pytest.raises(Exception):
        plot_bars(input_data_static, args=plot_args_incorrect_file_format)
