"""
This file checks whether a certain tab is present in the case study or not
"""

import pandas as pd
from xlrd import XLRDError


# try catch to see if sheet exists
def sheet_exists(sheet_name, fpath):
    try:
        df = pd.read_excel(fpath, sheet_name=sheet_name)
    except XLRDError:
        return False
    else:
        return True

# returns two tuples, one tuple with the list of sets that are used and are not used,
# and one with the list of parameters that are used and are not used
def data_checker(fpath, set_list, parameter_list):
    set_list_found, set_list_empty = [], []
    parameter_list_found, parameter_list_empty = [], []

    for set in set_list:
        if sheet_exists(set, fpath): set_list_found.append(set)
        else: set_list_empty.append(set)

    for param in parameter_list:
        if sheet_exists(param, fpath): parameter_list_found.append(param)
        else: parameter_list_empty.append(param)

    return (set_list_found, set_list_empty), (parameter_list_found, parameter_list_empty)

    