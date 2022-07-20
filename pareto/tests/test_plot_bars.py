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
from pareto.utilities.get_data import get_data
from pareto.utilities.results import plot_bars
from importlib import resources
import pytest


@pytest.fixture(scope="module")
def input_data():
    set_list = []
    parameter_list = ["test_plot_bar"]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var": df_parameters["test_plot_bar"],
        "labels": [("Origin", "Destination", "Time", "Value")],
    }


@pytest.fixture
def plot_args():
    return {
        "plot_title": "Test Data",
        "output_file": "first_bar.html",
        "group_by": "Destination",
        "print_data": True,
        "jupyter_notebook": False,
    }  # 'jpg', 'jpeg', 'pdf', 'png', 'svg', 'html'


def test_plot_bars(input_data, plot_args):
    plot_bars(input_data, args=plot_args)
