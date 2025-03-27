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
Determining Optimal Desalination Location Run
This file looks to find the optimal location of the desalination facility within the network.

This file runs the model in the following order:
1. Run for treatment site attached for different nodes in the network
2. Display cost results plots
3. Display cost summary for best network
"""
import pyomo.environ as pyo
from pareto.utilities.get_data import get_data
from pareto.models_extra.CM_module.cm_utils.gen_utils import report_results_to_excel
from pareto.models_extra.CM_module.cm_utils.data_parser import data_parser
from pareto.models_extra.CM_module.cm_utils.run_utils import (
    node_rerun,
    print_results_summary,
)
from importlib import resources

# -------------------------Loading data and model------------------------------
"""
Purpose of each of the files:
CM_large_permian.xlsx: This file is the large permian case study with no TDS concentrations.
CM_small_permian.xlsx: This file is the small permian case study with LI and TDS concentrations.
"""

fname = "CM_small_permian"
with resources.path(
    "pareto.models_extra.CM_module.case_studies",
    "CM_small_permian.xlsx",
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, model_type="critical_mineral")


print(f"running case study {fname}.")

# --------------Running treatment sites attached to different nodes-------------
print("\n\nSolving for different nodes in the network\n\n")
min_node, models = node_rerun(
    df_sets, df_parameters, treatment_site="R01", max_iterations=5000
)

# -----------------------------Generating report---------------------------
# generating final report of variables for the best model
final_model = models[min_node]
print("\n\nGenerating report\n\n")
report_results_to_excel(
    final_model, filename=f"{fname}_results.xlsx", split_var={"s_A": 3}
)


print()
print(f"*** Lowest cost location for treatment ***")

# Displaying specific broken down costs
print_results_summary(final_model)
