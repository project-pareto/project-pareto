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
Test utilities
"""

from pareto.strategic_water_management.strategic_produced_water_optimization import (
    create_model,
    solve_model,
    CONFIG,
)
from pareto.utilities.enums import (
    WaterQuality,
    Objectives,
    PipelineCost,
    PipelineCapacity,
    Hydraulics,
    RemovalEfficiencyMethod,
    InfrastructureTiming,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import is_feasible, nostdout
from importlib import resources

import pyomo.environ as pyo
from pyomo.environ import value
import pytest

# Modules to test:
from pareto.utilities.bounding_functions import VariableBounds
from pareto.utilities.model_modifications import free_variables
from pareto.utilities.model_modifications import deactivate_slacks
from pareto.utilities.model_modifications import fix_vars
from pareto.utilities.process_data import (
    check_required_data,
    MissingDataError,
    DataInfeasibilityError,
)
from pareto.utilities.visualize import plot_network
from contextlib import nullcontext as does_not_raise


############################
def fetch_strategic_model(config_dict):
    # user needs to provide the path to the case study data file
    # for example: 'C:\\user\\Documents\\myfile.xlsx'
    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.case_studies",
        "strategic_toy_case_study.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath)

    # create mathematical model
    """Valid values of config arguments for the default parameter in the create_model() call
    objective: [Objectives.cost, Objectives.reuse, Objectives.subsurface_risk]
    pipeline_cost: [PipelineCost.distance_based, PipelineCost.capacity_based]
    pipeline_capacity: [PipelineCapacity.input, PipelineCapacity.calculated]
    node_capacity: [True, False]
    water_quality: [WaterQuality.false, WaterQuality.post_process, WaterQuality.discrete]
    removal_efficiency_method: [RemovalEfficiencyMethod.concentration_based, RemovalEfficiencyMethod.load_based]
    """

    strategic_model = create_model(
        df_sets,
        df_parameters,
        default=config_dict,
    )

    options = {
        "deactivate_slacks": True,
        "scale_model": False,
        "scaling_factor": 1000,
        "running_time": 600,
        "gap": 0,
    }

    results = solve_model(model=strategic_model, options=options)

    return strategic_model, options, results


############################
def test_utilities_wout_quality():
    config_dict = {
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": True,
        "water_quality": WaterQuality.false,
        "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
    }
    model, _, _ = fetch_strategic_model(config_dict)

    # Add bounds and check to confirm that bounds have been added
    model = VariableBounds(model)
    check_01 = not all(
        model.v_F_Piped[ll, t].upper is None for ll in model.s_LLA for t in model.s_T
    )
    assert check_01
    if __name__ == "__main__":
        print(
            "After VariableBounds: Not all v_F_Piped upper bounds are None: ", check_01
        )

    # Free variables with exception list and test that variables have NOT been freed
    free_variables(model, exception_list=["v_F_Piped"])
    check_02 = not all(
        model.v_F_Piped[ll, t].upper is None for ll in model.s_LLA for t in model.s_T
    )
    assert check_02
    if __name__ == "__main__":
        print(
            "After free_variables with v_F_Piped in exception_list: Not all v_F_Piped upper bounds are None: ",
            check_02,
        )

    # Free variables and test that variables have been freed
    free_variables(model)
    check_03 = all(
        model.v_F_Piped[ll, t].upper is None for ll in model.s_LLA for t in model.s_T
    )
    assert check_03
    if __name__ == "__main__":
        print(
            "After free_variables with no exception_list: All v_F_Piped upper bounds are None: ",
            check_03,
        )

    # Deactivate slacks and test that slacks have been set to zero
    deactivate_slacks(model)
    check_04 = all(
        [
            all(
                value(model.v_S_FracDemand[p, t]) == 0
                for p in model.s_CP
                for t in model.s_T
            ),
            all(
                value(model.v_S_Production[p, t]) == 0
                for p in model.s_PP
                for t in model.s_T
            ),
            all(
                value(model.v_S_Flowback[p, t]) == 0
                for p in model.s_CP
                for t in model.s_T
            ),
            all(
                value(model.v_S_PipelineCapacity[l1, l2]) == 0
                for l1 in model.s_L
                for l2 in model.s_L
            ),
            all(value(model.v_S_StorageCapacity[s]) == 0 for s in model.s_S),
            all(value(model.v_S_DisposalCapacity[k]) == 0 for k in model.s_K),
            all(value(model.v_S_TreatmentCapacity[r]) == 0 for r in model.s_R),
            all(value(model.v_S_BeneficialReuseCapacity[o]) == 0 for o in model.s_O),
        ]
    )
    assert check_04
    if __name__ == "__main__":
        print("After deactivate_slacks: All slack variables are 0: ", check_04)


############################
def test_utilities_w_post_quality():
    config_dict = {
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": True,
        "water_quality": WaterQuality.post_process,
        "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
    }
    model, _, _ = fetch_strategic_model(config_dict)

    # Add bounds and check to confirm that bounds have been added
    model = VariableBounds(model)
    check_01 = not all(
        model.quality.v_Q[n, q, t].upper is None
        for n in model.quality.s_WQL
        for q in model.s_QC
        for t in model.s_T
    )
    assert check_01
    if __name__ == "__main__":
        print("After VariableBounds: Not all v_Q upper bounds are None: ", check_01)

    # Free variables with exception list and test that variables have NOT been freed
    free_variables(model, exception_list=["quality.v_Q"])
    check_02 = not all(
        model.quality.v_Q[n, q, t].upper is None
        for n in model.quality.s_WQL
        for q in model.s_QC
        for t in model.s_T
    )
    assert check_02
    if __name__ == "__main__":
        print(
            "After free_variables with v_Q in exception_list: Not all v_Q upper bounds are None: ",
            check_02,
        )

    # Free variables and test that variables have been freed
    free_variables(model)
    check_03 = all(
        model.quality.v_Q[n, q, t].upper is None
        for n in model.quality.s_WQL
        for q in model.s_QC
        for t in model.s_T
    )
    assert check_03
    if __name__ == "__main__":
        print(
            "After free_variables with no exception_list: All v_Q upper bounds are None: ",
            check_03,
        )


############################
def test_utilities_w_discrete_quality():
    config_dict = {
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": True,
        "water_quality": WaterQuality.discrete,
        "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
    }
    model, _, _ = fetch_strategic_model(config_dict)

    # Add bounds and check to confirm that bounds have been added
    model = VariableBounds(model)
    check_01 = not all(
        model.v_F_DiscretePiped[key, t, w, q].upper is None
        for key in model.s_NonPLP
        for t in model.s_T
        for w in model.s_QC
        for q in model.s_Q
    )
    assert check_01
    if __name__ == "__main__":
        print(
            "After VariableBounds: Not all v_F_DiscretePiped upper bounds are None: ",
            check_01,
        )


############################
def test_fix_vars():
    config_dict = {
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "hydraulics": Hydraulics.false,
        "node_capacity": True,
        "water_quality": WaterQuality.false,
        "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
        "infrastructure_timing": InfrastructureTiming.false,
    }
    model, options, results = fetch_strategic_model(config_dict)
    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok

    fix_vars(model, ["vb_y_Treatment"], ("R01", "MVC", "J2"), 1)
    solve_model(model=model, options=options)
    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    assert model.vb_y_Treatment["R01", "MVC", "J2"].value == 1
    assert model.vb_y_Treatment["R01", "MD", "J3"].value == 0
    with nostdout():
        assert is_feasible(model)

    model.vb_y_Treatment["R01", "MVC", "J2"].unfix()

    fix_vars(model, ["vb_y_Treatment"], ("R01", "MD", "J3"), 1)
    solve_model(model=model, options=options)
    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    assert model.vb_y_Treatment["R01", "MVC", "J2"].value == 0
    assert model.vb_y_Treatment["R01", "MD", "J3"].value == 1
    with nostdout():
        assert is_feasible(model)


############################
def test_data_check():
    # Check that MissingDataError is correctly raised
    # This input sheet is missing the following tabs:
    # 'Units', 'ProductionPads', 'CompletionsPads',
    # 'ExternalWaterSources', and 'PipelineCapexCapacityBased'
    # (the latter of which is required for the PipelineCost.capacity_based option)
    with resources.path(
        "pareto.tests",
        "strategic_toy_case_study_data_error.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath)

        with pytest.raises(MissingDataError) as error_record:
            default = {
                "objective": Objectives.cost,
                "pipeline_cost": PipelineCost.capacity_based,
                "pipeline_capacity": PipelineCapacity.input,
                "hydraulics": Hydraulics.false,
                "node_capacity": True,
                "water_quality": WaterQuality.false,
                "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
                "infrastructure_timing": InfrastructureTiming.true,
            }
            check_required_data(df_sets, df_parameters, CONFIG(default))
        # Note sets are not ordered, so cannot compare the exact error message
        assert (
            "Essential data is incomplete. Please add the following missing data tabs: Units, One of tabs "
            in str(error_record.value)
        )
        assert (
            "The following inputs are missing and required for the selected config option PipelineCost.capacity_based: {'PipelineCapexCapacityBased'}"
            in str(error_record.value)
        )

    # Check a secondary case that MissingDataError is correctly raised
    # This input sheet is missing the tab "CompletionsPads", while still including subsequent tabs that depend on this Set
    with resources.path(
        "pareto.tests",
        "strategic_toy_case_study_data_error2.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath)

        with pytest.raises(MissingDataError) as error2_record:
            default = {
                "objective": Objectives.cost,
                "pipeline_cost": PipelineCost.capacity_based,
                "pipeline_capacity": PipelineCapacity.input,
                "hydraulics": Hydraulics.false,
                "node_capacity": True,
                "water_quality": WaterQuality.false,
                "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
                "infrastructure_timing": InfrastructureTiming.true,
            }
            check_required_data(df_sets, df_parameters, CONFIG(default))
        # Note sets are not ordered, so cannot compare the exact error message
        assert (
            'Essential data is incomplete. Parameter data for CompletionsPads is given, but the "CompletionsPads" Set is missing. Please add and complete the following tab(s): CompletionsPads, or remove the following Parameters:'
            in str(error2_record.value)
        )

    # Check that warnings are correctly raised
    # This input sheet is missing the tabs "TruckingTime", "CompletionsDemand", "CNA", "CCA", "CST", "CCT","CKT","CRT", and "Economics"
    # Three warnings should be raised
    with resources.path(
        "pareto.tests",
        "strategic_toy_case_study_data_warning.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath)

        with pytest.warns(UserWarning) as warning_record:
            default = {
                "objective": Objectives.cost,
                "pipeline_cost": PipelineCost.capacity_based,
                "pipeline_capacity": PipelineCapacity.input,
                "hydraulics": Hydraulics.false,
                "node_capacity": True,
                "water_quality": WaterQuality.false,
                "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
                "infrastructure_timing": InfrastructureTiming.true,
            }
            check_required_data(df_sets, df_parameters, CONFIG(default))
        # check that only one warning was raised
        assert len(warning_record) == 5
        # check that the message matches
        assert (
            warning_record[0].message.args[0]
            == "CompletionsPads are given, but CompletionsPads data is missing. Inputs for the following tabs have been set to default values: {'CompletionsDemand'}"
        )
        assert (
            warning_record[1].message.args[0]
            == "CompletionsPads are given, but some piping and trucking arcs are missing. At least one of the following arcs are required (missing sets have been assumed to be empty): ['CNA', 'CCA', 'CST', 'CCT', 'CKT', 'CRT']"
        )
        assert (
            "StorageSites are given, but StorageSites data is missing. Inputs for the following tabs have been set to default values:"
            in warning_record[2].message.args[0]
        )
        assert (
            warning_record[3].message.args[0]
            == "Trucking arcs are given, but some trucking parameters are missing. The following missing parameters have been set to default values: {'TruckingTime'}"
        )
        assert (
            "The following parameters were missing and default values were substituted: ['AirEmissionsComponents', 'Economics', 'DesalinationSurrogate', 'AirEmissionCoefficients', 'TreatmentEmissionCoefficients']"
            in warning_record[4].message.args[0]
        )


############################
def test_infeasibility_check():
    # Check that DataInfeasibilityError is correctly raised for system capacity and demand infeasibilities
    # This input sheet has a very high volume of flowback water in T01
    with resources.path(
        "pareto.tests",
        "strategic_toy_case_study_infeasibility_capacity.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath)

        with pytest.raises(DataInfeasibilityError) as error_record:
            config_dict = {
                "objective": Objectives.cost,
                "pipeline_cost": PipelineCost.capacity_based,
                "pipeline_capacity": PipelineCapacity.input,
                "hydraulics": Hydraulics.false,
                "node_capacity": True,
                "water_quality": WaterQuality.false,
                "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
                "infrastructure_timing": InfrastructureTiming.true,
            }
            # model_infeasibility_detection() is called within create_model, after all constraints have been added
            strategic_model = create_model(
                df_sets,
                df_parameters,
                default=config_dict,
            )

        assert (
            "An infeasibility in the input data has been detected. The following time periods have larger volumes of produced water than capacity in the system: T01 (700196 total koil_bbls PW vs 3089 koil_bbls PW capacity)"
            == str(error_record.value)
        )

    # This input sheet has a very high completions demand in T01
    with resources.path(
        "pareto.tests",
        "strategic_toy_case_study_infeasibility_demand.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath)

        with pytest.raises(DataInfeasibilityError) as error_record:
            config_dict = {
                "objective": Objectives.cost,
                "pipeline_cost": PipelineCost.capacity_based,
                "pipeline_capacity": PipelineCapacity.input,
                "hydraulics": Hydraulics.false,
                "node_capacity": True,
                "water_quality": WaterQuality.false,
                "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
                "infrastructure_timing": InfrastructureTiming.true,
            }
            # model_infeasibility_detection() is called within create_model, after all constraints have been added
            strategic_model = create_model(
                df_sets,
                df_parameters,
                default=config_dict,
            )

        assert (
            "An infeasibility in the input data has been detected. The following time periods have higher demand than volume of produced water and externally sourced water available: T01 (70000 koil_bbls demand vs 756 koil_bbls available water)"
            == str(error_record.value)
        )


def test_plot_network():
    with resources.path(
        "pareto.case_studies",
        "strategic_toy_case_study.xlsx",
    ) as fpath:
        # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
        [df_sets, df_parameters] = get_data(fpath, model_type="strategic")
    strategic_model = create_model(
        df_sets,
        df_parameters,
        default={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "hydraulics": Hydraulics.false,
            "node_capacity": True,
            "water_quality": WaterQuality.false,
            "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
            "infrastructure_timing": InfrastructureTiming.true,
        },
    )

    # Positions for the toy case study
    pos = {
        "PP01": (20, 20),
        "PP02": (45, 20),
        "PP03": (50, 50),
        "PP04": (80, 40),
        "CP01": (65, 20),
        "F01": (75, 15),
        "F02": (75, 25),
        "K01": (30, 10),
        "K02": (40, 50),
        "S02": (60, 50),
        "S03": (10, 44),
        "S04": (10, 36),
        "R01": (20, 40),
        "R02": (70, 50),
        "O01": (1, 55),
        "O02": (1, 40),
        "O03": (1, 25),
        "N01": (30, 20),
        "N02": (30, 30),
        "N03": (30, 40),
        "N04": (40, 40),
        "N05": (45, 30),
        "N06": (50, 40),
        "N07": (60, 40),
        "N08": (60, 30),
        "N09": (70, 40),
    }

    # Run the plot_network function with several different sets of input arguments
    try:
        plot_network(strategic_model, pos=pos)
        plot_network(strategic_model, show_piping=True, show_trucking=True)
        plot_network(
            strategic_model,
            show_results=True,
            save_fig="test_network.png",
            show_fig=True,
        )
    except Exception as e:
        pytest.fail(f"Plot network feature fails with the following exception {e}")
