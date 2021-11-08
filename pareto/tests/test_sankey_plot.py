# from pareto.operational_water_management.run_operational_model import (
#     main,
# )
from pareto.utilities.results import plot_sankey
from pareto.utilities.get_data import get_data
from importlib import resources

headers_test = {}
source = []
destination = []
value = []

# input_data = {'source': source, 'destination': destination, 'value': value, 'pareto_var': df_parameters["test_sankey_diagram"]}

# Calling plot_sankey using the get_data format
# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
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
