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
General Utilities
This file contains any utility functions that would help processing data,
generating reports, etc.
"""

import pyomo.environ as pyo
import pandas as pd
import sys


def report_results_to_excel(
    model: pyo.ConcreteModel, filename: str, split_var: dict = {}
) -> None:
    counter = 0
    for var_name, var in model.component_map(pyo.Var, active=True).items():
        # creating the columns for the excel file
        set_names = []
        for index_set in var.index_set().subsets(expand_all_set_operators=False):
            if index_set.name in list(split_var.keys()):
                num_splits = split_var[index_set.name]
                for i in range(1, num_splits + 1):
                    set_names.append(index_set.name + str(i))
            else:
                set_names.append(index_set.name)
        set_names.append("Values")

        # assigning values to the data frame
        df = pd.DataFrame(columns=set_names)
        k = 0
        for i in list(var.keys()):
            row = list(i)
            row.append(var[i].value)
            df.loc[k] = row
            k += 1

        # adding variable sheet to the excel
        if counter == 0:
            with pd.ExcelWriter(filename, mode="w") as writer:
                df.to_excel(writer, sheet_name=var.name)
        else:
            with pd.ExcelWriter(filename, mode="a") as writer:
                df.to_excel(writer, sheet_name=var.name)
        counter += 1


# Function to turn off certain variables and constraints
def obj_fix(model: pyo.ConcreteModel, vars=[], activate=[], deactivate=[]):
    # Fixing and unfixing specified variables
    for var_name, var in model.component_map(pyo.Var, active=True).items():
        # fixing variables if they are specified by user
        if var_name in vars:
            for i in list(var.keys()):
                var[i].fix()
        # unfixing remaining variables
        else:
            var.unfix()

    for con in activate:
        con.activate()
    for con in deactivate:
        con.deactivate()

    return model


def alter_nonlinear_cons(model: pyo.ConcreteModel, deactivate=False):
    for con in model.component_data_objects(ctype=pyo.Constraint, descend_into=True):
        degree = con.body.polynomial_degree()
        if degree != 0 and degree != 1:
            assert degree == 2
            con.deactivate() if deactivate else con.activate()

    return model
