##############################################################################
# 
##############################################################################
"""
Module to with methods to get data from Excel spreadsheets and convert it in
a format that Pyomo requires

Authors: Andres Calderon
"""

from pyomo.environ import Param, Set, ConcreteModel
import pandas as pd


def df_to_param(data_frame):
    """
    This module converts a data frame that contains headers and an index column
    to the adequate format that Pyomo expects for paramerter:
    Input_parameter = {(column_index, row_header): value}
    """
    df_param = {}
    for i in data_frame.index:
        for j in data_frame.columns:
            tuple_index_col = (i, j)
            df_param[tuple_index_col] = data_frame.loc[i,j]

    return df_param

def get_data(fname):
    """
    This module uses Pandas methods to read data for Sets and Parameters from excel spreadsheets.
    - Sets are assumed to not have neither a header nor an index column. In addition, the data
      should be placed in column A, row 2
    - Parameters are assumed to have a header and an index column whose elements should be contained
      in a Set. The header should start in cell B2, and the index column should start in cell A3
    """
    set_list = ['ProductionPads', 'CompletionsPads', 'SWDSites']
    parameter_list = ['DriveTimes', 'CompletionsDemand', 'FlowbackRates']

    _df_sets = pd.read_excel(fname, sheet_name = set_list, header=0, index_col=None, usecols='A',
                        squeeze=True, dtype= "string", keep_default_na=False)

    _df_parameters = pd.read_excel( fname, sheet_name = parameter_list,
                                    header=1, index_col=0, usecols=None,
                                    squeeze=True, keep_default_na=False)

    for i in _df_parameters:
        _df_parameters[i].replace('', 0, inplace=True)
        _df_parameters[i].columns = _df_parameters[i].columns.astype(str)

    return [_df_sets, _df_parameters]

def create_model(_df_sets, _df_parameters):
    """
    This module takes data frame for Sets and Parameters and input arguments,
    populate Pyomo Set and Param, and outputs a Concrete Pyomo Model
    """
    model=ConcreteModel()

    ###############################################################################
    #                             SET DEFINITION
    ###############################################################################
    model.p = Set(initialize=_df_sets['ProductionPads'].values,doc='Production Pads')
    model.c = Set(initialize=_df_sets['CompletionsPads'].values,doc='Completions Pads')
    model.d = Set(initialize=_df_sets['SWDSites'].values,doc='SWD Sites')
    model.t = Set(initialize=_df_parameters['CompletionsDemand'].columns, doc='plannning weeks')

    ###############################################################################
    #                           PARAMETER DEFINITION
    ###############################################################################
    dict_drive_times = df_to_param(_df_parameters['DriveTimes'])
    dict_completions_demand = df_to_param(_df_parameters['CompletionsDemand'])
    dict_flowback_rates = df_to_param(_df_parameters['FlowbackRates'])

    print(dict_drive_times)
    print(dict_completions_demand)
    print(dict_flowback_rates)
    model.completion_demand = Param(model.c, model.t, initialize=dict_completions_demand,
                                    doc="Water demand for completion operations")
    model.flowback_rates = Param(   model.c, model.t, initialize=dict_flowback_rates,
                                    doc="Waer flowback rate")

    model.p.display()
    model.c.display()
    model.d.display()
    model.t.display()
    model.completion_demand.display()
    model.flowback_rates.display()

    return model


if __name__ == '__main__':

    [df_sets, df_parameters] = get_data(fname='input_data_produced_water_optimization_v3_test.xlsx')

    strategic_model = create_model(df_sets, df_parameters)
