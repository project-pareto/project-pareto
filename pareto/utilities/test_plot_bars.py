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

set_list = []
parameter_list = ["test_plot_bar"]

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

# Calling plot_bars using the get_data format
args = {
    "chart_title": "Test Data",
    "labels": [("Origin", "Destination", "Time", "Value")],
}
input_data = {"pareto_var": df_parameters["test_plot_bar"]}
plot_bars(input_data, args=args)
