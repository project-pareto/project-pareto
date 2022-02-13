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
from importlib import resources

from pareto.utilities.get_data import get_data, set_consistency_check, od_matrix

from pyomo.environ import Var, Param, Set, ConcreteModel, Constraint, NonNegativeReals


def create_model(df_sets, df_parameters):
    """
    This example shows how to read data from a Spreadsheet and define Sets and Parameters
    """
    model = ConcreteModel()

    ###############################################################################
    #                             SET DEFINITION
    ###############################################################################
    model.p = Set(initialize=df_sets["ProductionPads"], doc="Production Pads")
    model.c = Set(initialize=df_sets["CompletionsPads"], doc="Completions Pads")
    model.a = Set(initialize=df_sets["ProductionTanks"], doc="Production tanks")
    model.d = Set(initialize=df_sets["SWDSites"], doc="Disposal Sites")
    model.t = Set(initialize=df_sets["TimePeriods"], doc="plannning weeks")
    model.l = Set(
        initialize=model.p | model.c | model.a | model.d,
        doc="Superset that contains all locations",
    )

    ###############################################################################
    #                           PARAMETER DEFINITION
    ###############################################################################
    model.p_drive_times = Param(
        model.l,
        model.l,
        default=0,
        initialize=df_parameters["DriveTimes"],
        doc="Driving times between locations",
    )
    model.p_completion_demand = Param(
        model.c,
        model.t,
        default=0,
        initialize=df_parameters["CompletionsDemand"],
        doc="Water demand for completion operations",
    )
    model.p_flowback_rates = Param(
        model.c,
        model.t,
        default=0,
        initialize=df_parameters["FlowbackRates"],
        doc="Water flowback rate",
    )
    model.p_production_rates = Param(
        model.p,
        model.a,
        model.t,
        default=0,
        initialize=df_parameters["ProductionRates"],
        doc="Production Rate Forecasts by Tanks and Pads",
    )
    model.p_initial_disposal_capacity = Param(
        model.d,
        default=0,
        initialize=df_parameters["InitialDisposalCapacity"],
        doc="Initial disposal capacity",
    )
    model.p_two_index_column = Param(
        model.d,
        model.d,
        default=0,
        initialize=df_parameters["TwoIndexColumnParam"],
        doc="Parameter with two indices in column format",
    )

    ###############################################################################
    #                           VARIABLES DEFINITION
    ###############################################################################
    model.v_drive_times = Var(
        within=NonNegativeReals, doc="Total driving times between locations"
    )
    model.v_completion_demand = Var(
        model.t,
        within=NonNegativeReals,
        doc="Total water demand for completion operations",
    )
    model.v_flowback_rates = Var(
        within=NonNegativeReals, doc="Total water flowback rate"
    )
    model.v_production_rates = Var(
        within=NonNegativeReals, doc="Total production Rate Forecasts by Tanks and Pads"
    )
    model.v_disposal_capacity = Var(
        within=NonNegativeReals, doc="Total disposal capacity"
    )
    model.v_two_index_param = Var(
        model.d,
        within=NonNegativeReals,
        doc="Variable to test two-index column parameters",
    )

    ###############################################################################
    #                              TEST EQUATIONS
    ###############################################################################
    def DriveTimesEquationRule(model):
        return model.v_drive_times == sum(
            sum(model.p_drive_times[l, ll] for l in model.l) for ll in model.l
        )

    model.e_drive_times = Constraint(
        rule=DriveTimesEquationRule, doc="Calculation of total drive times"
    )

    def CompletionDemandRule(model, t):
        return model.v_completion_demand[t] == sum(
            model.p_completion_demand[c, t] for c in model.c
        )

    model.e_completion_demand = Constraint(
        model.t, rule=CompletionDemandRule, doc="Calculation of total water demand"
    )

    def FlowBackRatesRule(model):
        return model.v_flowback_rates == sum(
            sum(model.p_flowback_rates[c, t] for c in model.c) for t in model.t
        )

    model.e_flowback_rates = Constraint(
        rule=FlowBackRatesRule, doc="Calculation of total flowback"
    )

    def ProductionRatesRule(model):
        return model.v_production_rates == sum(
            sum(
                sum(model.p_production_rates[p, a, t] for p in model.p) for a in model.a
            )
            for t in model.t
        )

    model.e_production_rates = Constraint(
        rule=ProductionRatesRule, doc="Calculation of total production rates"
    )

    def DisposalCapacityRule(model):
        return model.v_disposal_capacity == sum(
            model.p_initial_disposal_capacity[d] for d in model.d
        )

    model.e_disposal_capacity = Constraint(
        rule=DisposalCapacityRule, doc="Calculation of total initial disposal capacity"
    )

    def TwoIndexColumnParameterRule(model, d):
        return model.v_two_index_param[d] == sum(
            model.p_two_index_column[d, dd] for dd in model.d
        )

    model.e_two_index_column_param = Constraint(
        model.d,
        rule=TwoIndexColumnParameterRule,
        doc="Equation to test reading parameters with two indices in column format",
    )

    return model


if __name__ == "__main__":

    # Tabs in the input Excel spreadsheet
    set_list = ["ProductionPads", "CompletionsPads", "SWDSites", "ProductionTanks"]
    parameter_list = [
        "Coordinates",
        "CompletionsDemand",
        "FlowbackRates",
        "ProductionRates",
        "InitialDisposalCapacity",
        "TwoIndexColumnParam",
    ]
    with resources.path("pareto.case_studies", "toy_case_study.xlsx") as fpath:
        print(f"Reading file from {fpath}")
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    # Set the path, including the file name, where you would like to save the output excel file that contains drive times and drive distances
    # If not path is provided, the od_matrix method will save the excel file in the currect directory

    od_matrix_input = {
        "origin": df_parameters["Coordinates"],
        "api": "open_street_map",
        "output": "time",
        "api_key": None,
        "fpath": "test_od.xlsx",
    }

    df_parameters["DriveTimes"] = od_matrix(od_matrix_input)

    set_consistency_check(
        df_parameters["ProductionRates"],
        df_sets["ProductionPads"],
        df_sets["ProductionTanks"],
        df_sets["TimePeriods"],
    )
    set_consistency_check(df_parameters["InitialDisposalCapacity"], df_sets["SWDSites"])

    strategic_model = create_model(df_sets, df_parameters)
