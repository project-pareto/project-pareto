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


"""
Runs and reports cost optimal operation and lithium revenue recovery opportunities
"""
import pyomo.environ as pyo
from pareto.utilities.get_data import get_data
from pareto.utilities.cm_utils.gen_utils import report_results_to_excel
from pareto.utilities.cm_utils.opt_utils import (
    max_theoretical_recovery_flow,
    max_theoretical_recovery_flow_opt,
    cost_optimal,
    max_recovery_with_infrastructure,
)
from pareto.utilities.cm_utils.run_utils import print_results_summary
from pareto.utilities.cm_utils.data_parser import data_parser

from importlib import resources
from set_param_list import set_list, parameter_list


# load the case study
# case_study_name = 'large_case_study_Li'
case_study_name = "small_case_study_Li"

with resources.path(
    "pareto.case_studies",
    "small_case_study_Li.xlsx",
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

data = data_parser(df_sets, df_parameters)

print("--- Running cost optimal solution ---")
model = cost_optimal(data)

print("--- Running max treatment with infrastructure ---")
max_inf_model = max_recovery_with_infrastructure(data)

print("--- Runnning max theoretical treatment revenue ---")
max_recovery = max_theoretical_recovery_flow_opt(
    model, treatment_unit="R01_IN", desired_li_conc=100
)

print()
print("--- Results Summary: Cost Optimal ---")
print_results_summary(model)
# output results to excel
results_fname = f"{case_study_name}_results.xlsx"
print(f"... reporting cost optimal results to {results_fname}")
report_results_to_excel(model, results_fname, {"s_A": 3})  # generating report

print()
print("--- Results Summary: Maximum treatment revenue ---")
print_results_summary(max_inf_model)
print()
print(
    f"Max. treatment revenue with\n existing infrastructure:  "
    f"{pyo.value(max_inf_model.treat_rev):>8.0f}"
)
print()
print(
    f"Max theoretical treatment revenue\n (ignoring infrastructure): "
    f"{max_recovery:>8.0f}"
)
print()
print()
