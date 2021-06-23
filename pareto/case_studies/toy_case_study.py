from pareto.utilities.get_data import get_data, df_to_param

from pyomo.environ import Param, Set, ConcreteModel

def create_model(df_sets, df_parameters):
    """
    This example shows how to read data from a Spreadsheet and define Sets and Parameters
    """
    model=ConcreteModel()

    ###############################################################################
    #                             SET DEFINITION
    ###############################################################################
    model.p = Set(initialize=df_sets['ProductionPads'].values,doc='Production Pads')
    model.c = Set(initialize=df_sets['CompletionsPads'].values,doc='Completions Pads')
    model.d = Set(initialize=df_sets['SWDSites'].values,doc='SWD Sites')
    model.t = Set(initialize=df_sets['TimePeriods'].values, doc='plannning weeks')
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

    return model

if __name__ == '__main__':

    [df_sets, df_parameters] = get_data(fname='C:\\path\\to\\project-pareto\\pareto\\case_studies\\EXAMPLE_INPUT_DATA_FILE_mod.xlsx')
    strategic_model = create_model(df_sets, df_parameters)