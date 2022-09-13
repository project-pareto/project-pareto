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
from pareto.utilities.results import plot_scatter
from importlib import resources
import pytest


@pytest.fixture(scope="module")
def input_data_animated_1():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var_x": df_parameters["plot_scatter_vFPiped"],
        "pareto_var_y": df_parameters["plot_scatter_vCPiped"],
        "size": df_parameters[
            "plot_scatter_vSize"
        ],  #'x/y', 'y/x', df_parameters["test_plot_scatter_y"]
        "labels_x": [("Origin", "Destination", "Time", "Trucked Water (bbl)")],
        "labels_y": [("Origin", "Destination", "Time", "Cost of Trucked Water ($)")],
        "labels_size": [("Origin", "Destination", "Time", "Size")],
    }


@pytest.fixture(scope="module")
def input_data_animated_2():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var_x": df_parameters["plot_scatter_vFPiped"],
        "pareto_var_y": df_parameters["plot_scatter_vCPiped"],
        "size": "x/y",  #'x/y', 'y/x', df_parameters["test_plot_scatter_y"]
        "labels_x": [("Origin", "Destination", "Time", "Trucked Water (bbl)")],
        "labels_y": [("Origin", "Destination", "Time", "Cost of Trucked Water ($)")],
        "labels_size": [("Origin", "Destination", "Time", "Size")],
    }


@pytest.fixture(scope="module")
def input_data_animated_3():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var_x": df_parameters["plot_scatter_vFPiped"],
        "pareto_var_y": df_parameters["plot_scatter_vCPiped"],
        "size": "y/x",  #'x/y', 'y/x', df_parameters["test_plot_scatter_y"]
        "labels_x": [("Origin", "Destination", "Time", "Trucked Water (bbl)")],
        "labels_y": [("Origin", "Destination", "Time", "Cost of Trucked Water ($)")],
        "labels_size": [("Origin", "Destination", "Time", "Size")],
    }


@pytest.fixture(scope="module")
def input_data_animated_4():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var_x": df_parameters["plot_scatter_vFPiped"],
        "pareto_var_y": df_parameters["plot_scatter_vCPiped"],
        "labels_x": [("Origin", "Destination", "Time", "Trucked Water (bbl)")],
        "labels_y": [("Origin", "Destination", "Time", "Cost of Trucked Water ($)")],
    }


@pytest.fixture(scope="module")
def input_data_static_1():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var_x": df_parameters["test_plot_scatter_x_static"],
        "pareto_var_y": df_parameters["test_plot_scatter_y_static"],
        "size": df_parameters[
            "test_plot_scatter_size_static"
        ],  #'x/y', 'y/x', df_parameters["test_plot_scatter_y"]
        "labels_x": [("Origin", "Destination", "Trucked Water (bbl)")],
        "labels_y": [("Origin", "Destination", "Cost of Trucked Water ($)")],
        "labels_size": [("Origin", "Destination", "Size")],
    }


@pytest.fixture(scope="module")
def input_data_static_2():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var_x": df_parameters["test_plot_scatter_x_static"],
        "pareto_var_y": df_parameters["test_plot_scatter_y_static"],
        "size": "x/y",  #'x/y', 'y/x', df_parameters["test_plot_scatter_y"]
        "labels_x": [("Origin", "Destination", "Trucked Water (bbl)")],
        "labels_y": [("Origin", "Destination", "Cost of Trucked Water ($)")],
        "labels_size": [("Origin", "Destination", "Size")],
    }


@pytest.fixture(scope="module")
def input_data_static_3():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var_x": df_parameters["test_plot_scatter_x_static"],
        "pareto_var_y": df_parameters["test_plot_scatter_y_static"],
        "size": "y/x",  #'x/y', 'y/x', df_parameters["test_plot_scatter_y"]
        "labels_x": [("Origin", "Destination", "Trucked Water (bbl)")],
        "labels_y": [("Origin", "Destination", "Cost of Trucked Water ($)")],
        "labels_size": [("Origin", "Destination", "Size")],
    }


@pytest.fixture(scope="module")
def input_data_static_4():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    return {
        "pareto_var_x": df_parameters["test_plot_scatter_x_static"],
        "pareto_var_y": df_parameters["test_plot_scatter_y_static"],
        "labels_x": [("Origin", "Destination", "Trucked Water (bbl)")],
        "labels_y": [("Origin", "Destination", "Cost of Trucked Water ($)")],
    }


@pytest.fixture(scope="module")
def plot_args1():
    return {
        "plot_title": "Test Data",
        "group_by": "Destination",
        "output_file": "first_scatter.html",
        "print_data": True,
        "group_by_category": True,
        "jupyter_notebook": False,
    }  # 'jpg', 'jpeg', 'pdf', 'png', 'svg', 'html'


@pytest.fixture(scope="module")
def plot_args2():
    return {
        "plot_title": "Test Data",
        "group_by": "Destination",
        "output_file": "first_scatter.html",
        "print_data": True,
        "group_by_category": False,
        "jupyter_notebook": False,
    }  # 'jpg', 'jpeg', 'pdf', 'png', 'svg', 'html'


@pytest.fixture(scope="module")
def plot_args3():
    return {
        "plot_title": "Test Data",
        "group_by": "Origin",
        "output_file": "first_scatter.html",
        "print_data": True,
        "group_by_category": False,
        "jupyter_notebook": False,
    }  # 'jpg', 'jpeg', 'pdf', 'png', 'svg', 'html'


@pytest.fixture(scope="module")
def plot_args4():
    return {
        "plot_title": "Test Data",
        "group_by": "Origin",
        "output_file": "first_scatter.html",
        "print_data": True,
        "group_by_category": True,
        "jupyter_notebook": False,
    }  # 'jpg', 'jpeg', 'pdf', 'png', 'svg', 'html'


@pytest.fixture(scope="module")
def plot_args5():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)
    return {
        "plot_title": "Test Data",
        "group_by": "Origin",
        "output_file": "first_scatter.html",
        "print_data": True,
        "group_by_category": df_parameters["plot_scatter_Categories"],
        "jupyter_notebook": False,
    }  # 'jpg', 'jpeg', 'pdf', 'png', 'svg', 'html'


@pytest.fixture(scope="module")
def plot_args5_static():
    set_list = []
    parameter_list = [
        "test_plot_scatter_y",
        "test_plot_scatter_x",
        "test_plot_scatter_y_static",
        "test_plot_scatter_x_static",
        "test_plot_scatter_size",
        "plot_scatter_vFPiped",
        "plot_scatter_vCPiped",
        "plot_scatter_vSize",
        "plot_scatter_Categories",
        "plot_scatter_static_Categories",
        "test_plot_scatter_size_static",
    ]

    with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)
    return {
        "plot_title": "Test Data",
        "group_by": "Origin",
        "output_file": "first_scatter.html",
        "print_data": True,
        "group_by_category": df_parameters["plot_scatter_static_Categories"],
        "jupyter_notebook": False,
    }  # 'jpg', 'jpeg', 'pdf', 'png', 'svg', 'html'


@pytest.mark.unit
def test_plot_scatter1(input_data_animated_1, plot_args1):
    plot_scatter(input_data_animated_1, args=plot_args1)


def test_plot_scatter2(input_data_animated_1, plot_args2):
    plot_scatter(input_data_animated_1, args=plot_args2)


def test_plot_scatter3(input_data_animated_1, plot_args3):
    plot_scatter(input_data_animated_1, args=plot_args3)


def test_plot_scatte4r(input_data_animated_1, plot_args4):
    plot_scatter(input_data_animated_1, args=plot_args4)


def test_plot_scatter5(input_data_animated_1, plot_args5):
    plot_scatter(input_data_animated_1, args=plot_args5)


def test_plot_scatter6(input_data_animated_2, plot_args1):
    plot_scatter(input_data_animated_2, args=plot_args1)


def test_plot_scatter7(input_data_animated_2, plot_args2):
    plot_scatter(input_data_animated_2, args=plot_args2)


def test_plot_scatter8(input_data_animated_2, plot_args3):
    plot_scatter(input_data_animated_2, args=plot_args3)


def test_plot_scatter9(input_data_animated_2, plot_args4):
    plot_scatter(input_data_animated_2, args=plot_args4)


def test_plot_scatter10(input_data_animated_3, plot_args5):
    plot_scatter(input_data_animated_3, args=plot_args5)


def test_plot_scatter11(input_data_animated_3, plot_args1):
    plot_scatter(input_data_animated_3, args=plot_args1)


def test_plot_scatter12(input_data_animated_3, plot_args2):
    plot_scatter(input_data_animated_3, args=plot_args2)


def test_plot_scatter13(input_data_animated_3, plot_args3):
    plot_scatter(input_data_animated_3, args=plot_args3)


def test_plot_scatter14(input_data_animated_3, plot_args4):
    plot_scatter(input_data_animated_3, args=plot_args4)


def test_plot_scatter15(input_data_animated_3, plot_args5):
    plot_scatter(input_data_animated_3, args=plot_args5)


def test_plot_scatter16(input_data_animated_4, plot_args1):
    plot_scatter(input_data_animated_4, args=plot_args1)


def test_plot_scatter17(input_data_animated_4, plot_args2):
    plot_scatter(input_data_animated_4, args=plot_args2)


def test_plot_scatter18(input_data_animated_4, plot_args3):
    plot_scatter(input_data_animated_4, args=plot_args3)


def test_plot_scatter19(input_data_animated_4, plot_args4):
    plot_scatter(input_data_animated_4, args=plot_args4)


def test_plot_scatter20(input_data_animated_4, plot_args5):
    plot_scatter(input_data_animated_4, args=plot_args5)


def test_plot_scatter21(input_data_static_1, plot_args1):
    plot_scatter(input_data_static_1, args=plot_args1)


def test_plot_scatter22(input_data_static_1, plot_args2):
    plot_scatter(input_data_static_1, args=plot_args2)


def test_plot_scatter23(input_data_static_1, plot_args3):
    plot_scatter(input_data_static_1, args=plot_args3)


def test_plot_scatter24(input_data_static_1, plot_args4):
    plot_scatter(input_data_static_1, args=plot_args4)


def test_plot_scatter25(input_data_static_1, plot_args5_static):
    plot_scatter(input_data_static_1, args=plot_args5_static)


def test_plot_scatter26(input_data_static_2, plot_args1):
    plot_scatter(input_data_static_2, args=plot_args1)


def test_plot_scatter27(input_data_static_2, plot_args2):
    plot_scatter(input_data_static_2, args=plot_args2)


def test_plot_scatter28(input_data_static_2, plot_args3):
    plot_scatter(input_data_static_2, args=plot_args3)


def test_plot_scatter29(input_data_static_2, plot_args4):
    plot_scatter(input_data_static_2, args=plot_args4)


def test_plot_scatter30(input_data_static_2, plot_args5_static):
    plot_scatter(input_data_static_2, args=plot_args5_static)


def test_plot_scatter31(input_data_static_3, plot_args1):
    with pytest.raises(Exception) as e_info:
        plot_scatter(input_data_static_3, args=plot_args1)


def test_plot_scatter32(input_data_static_3, plot_args2):
    with pytest.raises(Exception) as e_info:
        plot_scatter(input_data_static_3, args=plot_args2)


def test_plot_scatter33(input_data_static_3, plot_args3):
    plot_scatter(input_data_static_3, args=plot_args3)


def test_plot_scatter34(input_data_static_3, plot_args4):
    plot_scatter(input_data_static_3, args=plot_args4)


def test_plot_scatter35(input_data_static_3, plot_args5_static):
    plot_scatter(input_data_static_3, args=plot_args5_static)


def test_plot_scatter36(input_data_static_4, plot_args1):
    plot_scatter(input_data_static_4, args=plot_args1)


def test_plot_scatter37(input_data_static_4, plot_args2):
    plot_scatter(input_data_static_4, args=plot_args2)


def test_plot_scatter38(input_data_static_4, plot_args3):
    plot_scatter(input_data_static_4, args=plot_args3)


def test_plot_scatter39(input_data_static_4, plot_args4):
    plot_scatter(input_data_static_4, args=plot_args4)


def test_plot_scatter40(input_data_static_4, plot_args5_static):
    plot_scatter(input_data_static_4, args=plot_args5_static)
