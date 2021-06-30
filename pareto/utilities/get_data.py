##############################################################################
# 
##############################################################################
"""
Module to read in input data from Excel spreadsheets and convert it into the
format that Pyomo requires

Authors: PARETO Team (Andres J. Calderon, Markus G. Drouven)
"""

from pyomo.environ import Param, Set, ConcreteModel
import pandas as pd


def _read_data(_fname, _set_list, _parameter_list):
    """
    This methods uses Pandas methods to read from an Excel spreadsheet and output a data frame
    Two data frames are created, one that contains all the Sets: _df_sets, and another one that
    contains all the parameters in raw format: _df_parameters
    """
    _df_parameters = {}
    _temp_df_parameters = {}
    _df_sets = pd.read_excel(_fname, sheet_name = _set_list, header=0, index_col=None, usecols='A',
                                squeeze=True, dtype= "string", keep_default_na=False)

    _df_parameters = pd.read_excel(_fname, sheet_name = _parameter_list,
                                        header=1, index_col=None, usecols=None,
                                        squeeze=True, keep_default_na=False)

    # Detect unnamed columns which will be used to reshape the dataframe by defining what columns are indices
    for i in _df_parameters:
        index_col = []
        for j in _df_parameters[i].columns:
            #If the column is unnamed, it is assumed the column is an index and saved in index_col
            if 'Unnamed' in str(j):
                index_col.append(j)

        # If the number of unnamed columns in idex_col is equal to the total columns of the dataframe
        # it means that this is a parameter in column format. Therefore, the indices are defined for all
        # the columns of the dataframe except for the last column which contains the data
        if len(index_col) == len(_df_parameters[i].columns):
            data_column = index_col.pop()

        _df_parameters[i].set_index(index_col, inplace=True)

    return [_df_sets, _df_parameters]


def _cleanup_data(_df_parameters):
    """
    This method does two things:
    1) It replaces blank cells with zeros
    2) It formats the headers and column names as strings
    """
    for i in _df_parameters:
        _df_parameters[i].replace('', 0, inplace=True)
        _df_parameters[i].columns = _df_parameters[i].columns.astype(str)

    return _df_parameters


def _df_to_param(data_frame):
    """
    This module converts the data frame that contains Parameters into the adequate 
    format that Pyomo expects for paramerters:
    Input_parameter = {(column_index, row_header): value}
    """
    _df_parameters={}
    _temp_df_parameters={}
    for i in data_frame:

        # If the data frame has one unnamed column it means the dataframe corresponds to
        # a parameter in column format. In this case, the dataframe is converted directly
        # to a dictionary.
        if 'Unnamed' in str(data_frame[i].columns[0]):
            data_column = data_frame[i].columns[0]
            _temp_df_parameters[i] = data_frame[i].to_dict()
            _df_parameters[i] = _temp_df_parameters[i][data_column]
        else:
            _df_parameters[i] = data_frame[i].stack().to_dict()

    return _df_parameters


def get_data(fname, set_list, parameter_list):
    """
    This module uses Pandas methods to read data for Sets and Parameters from excel spreadsheets.
    - Sets are assumed to not have neither a header nor an index column. In addition, the data
      should be placed in column A, row 2
    - Parameters are assumed to have a header and an index column whose elements should be contained
      in a Set. The header should start in cell B2, and the index column should start in cell A3

    To use this method:

    [df_sets, df_parameters] = get_data(fname='path\\to\\excel\\file\\INPUT_DATA.xlsx')

        ###############################################################################
                                     SET DEFINITION
        ###############################################################################
        model.p = Set(initialize=_df_sets['ProductionPads'].values,doc='Production Pads')
        model.c = Set(initialize=_df_sets['CompletionsPads'].values,doc='Completions Pads')
        model.d = Set(initialize=_df_sets['SWDSites'].values,doc='SWD Sites')
        model.t = Set(initialize=_df_sets['TimePeriods'].values, doc='planning weeks')
        model.l = Set(initialize=model.p | model.c | model.d, doc='Superset that contains all locations')

        ###############################################################################
        #                           PARAMETER DEFINITION
        ###############################################################################
        model.drive_times = Param(model.l, model.l, initialize=df_parameters['DriveTimes'],
                                    doc="Driving times between locations")
        model.completion_demand = Param(model.c, model.t, initialize=df_parameters['CompletionsDemand'],
                                        doc="Water demand for completion operations")
        model.flowback_rates = Param(model.c, model.t, initialize=df_parameters['FlowbackRates'],
                                     doc="Water flowback rate")

    It is worth highlighting that the Set for time periods "model.t" is derived by the method based on the
    Parameter: CompletionsDemand which is indexed by T
    """
    # Reading raw data, two data frames are output, one for Sets, and another one for Parameters
    [_df_sets, _df_parameters] = _read_data(fname, set_list, parameter_list)

    # Parameters are cleaned up, e.g. blank cells are replaced by zeros
    _df_parameters = _cleanup_data(_df_parameters)
    
    # The set for time periods is defined based on the columns of the parameter for Completions Demand
    # This is done so the user does not have to add an extra tab in the spreadsheet for the time period set
    _df_sets['TimePeriods'] = _df_parameters['CompletionsDemand'].columns.to_series()

    # The data frame for Parameters is preprocessed to match the format required by Pyomo
    _df_parameters = _df_to_param(_df_parameters)

    return [_df_sets, _df_parameters]
