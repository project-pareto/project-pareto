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
from pareto.utilities.results import plot_sankey
from pareto.utilities.get_data import get_data
from importlib import resources

headers_test = {}
source = []
destination = []
value = []

# input_data = {'source': source, 'destination': destination, 'value': value, 'pareto_var': df_parameters["test_sankey_diagram"]}

# Calling plot_sankey using the get_data format
# User needs to provide a tuple with labels for each column of the pareto_var
set_list = []
parameter_list = ["test_plot_sankey"]

with resources.path("pareto.case_studies", "visualization_test_data.xlsx") as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

# Creating a Sankey diagram
args = {"font_size": 15, "plot_title": "Total Flows"}
input_data = {
    "pareto_var": df_parameters["test_plot_sankey"],
    "labels": [("Origin", "Destination", "Time", "Value")],
}
plot_sankey(input_data, args)

# One or more specific time periods can be selected. plot_sankey calculates the totals and create the plot
args = {"font_size": 15, "plot_title": "Flow for T01"}
input_data = {
    "pareto_var": df_parameters["test_plot_sankey"],
    "labels": [("Origin", "Destination", "Time", "Value")],
    "time_period": ["T01"],
}
plot_sankey(input_data, args)
