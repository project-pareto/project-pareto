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
Test two-stage stochastic strategic water management model (TSSP)
"""
# Import pyomo libraries
import pyomo.environ as pyo
from pyomo.util.check_units import assert_units_consistent
from pyomo.core.base import value
from pyomo.environ import Constraint, Expression

# Import Pyomo libraries
from pareto.utilities.solvers import get_solver
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    create_model,
    solve_model,
    scale_model,
    pipeline_hydraulics,
    infrastructure_timing,
    set_objective,
    water_quality_discrete,
)
from pareto.utilities.enums import (
    WaterQuality,
    Objectives,
    PipelineCost,
    Hydraulics,
    DesalinationModel,
    PipelineCapacity,
    RemovalEfficiencyMethod,
    InfrastructureTiming,
    SubsurfaceRisk,
)
from pareto.utilities.units_support import get_model_unit_container
from pareto.utilities.get_data import (
    get_data,
    get_display_units,
    get_valid_input_set_tab_names,
    get_valid_input_parameter_tab_names,
)
from pareto.utilities.units_support import (
    flatten_list,
    PintUnitExtractionVisitor,
)

# from idaes.core.util.model_statistics import degrees_of_freedom
from pareto.utilities.results import (
    generate_report,
    PrintValues,
    OutputUnits,
    is_feasible,
    nostdout,
)


from pareto.strategic_water_management.stochastic_model_creation import StochasticPareto
from pareto.strategic_water_management.stochastic_results import (
    generate_stochastic_report,
)
import pareto.strategic_water_management.run_tssp
import pareto.strategic_water_management.run_for_eev
import pareto.strategic_water_management.run_for_evpi

import pytest
from importlib import resources
import copy


@pytest.fixture
def scenarios_data():
    base = get_data(
        filename="toy_case_study.xlsx",
        model_type="strategic",
    )

    low = copy.deepcopy(base)
    mid = copy.deepcopy(base)
    high = copy.deepcopy(base)

    # Example: perturb demand
    low["p_Demand"] *= 0.8
    high["p_Demand"] *= 1.2

    return {
        "low": low,
        "mid": mid,
        "high": high,
    }


@pytest.fixture
def probability_data():
    return {
        "low": 1 / 3,
        "mid": 1 / 3,
        "high": 1 / 3,
    }


def stochastic_model(scenarios_data, probability_data):
    """
    Build a small stochastic strategic model using existing
    PARETO input infrastructure.
    """
    # Use existing test input data (consistent with deterministic tests)
    model = StochasticPareto(
        scenarios_data=scenarios_data,
        pd_data=probability_data,
    )
    return model


# Test A: Scenario Structure + nonanticipativity


def test_scenario_structure_and_nonanticipativity(stochastic_model):
    """
    Verify-
    1. Scenario set is correctly created
    2. First-stage variables exist at the root level
    3. Nonanticipativity constraints enforce equality across scenarios
    """

    m = stochastic_model

    # Scenario structure
    assert hasattr(m, "set_scenarios")
    assert len(m.set_scenarios) == 3

    assert hasattr(m, "scenario")
    for s in m.set_scenarios:
        assert s in m.scenario

    # First-stage variables
    for varname in m.shared_vars:
        assert hasattr(m, varname)

    # Nonanticipativity constraints
    assert hasattr(m, "nonanticipativity")

    for varname in m.shared_vars:
        con_name = f"{varname}_con"
        assert hasattr(m.nonanticipativity, con_name)

        con = getattr(m.nonanticipativity, con_name)
        assert isinstance(con, Constraint)
        assert len(con) > 0


# Test B: Scenario probabilities


def test_scenario_probabilities_sum_to_one(stochastic_model):
    """
    Verify that scenario probabilities sum to one.
    """
    m = stochastic_model

    total_prob = sum(m.probability_data[s] for s in m.set_scenarios)
    assert abs(value(total_prob) - 1.0) < 1e-6


# Test C: Objective Function


def test_objective_is_scenario_weighted(stochastic_model):
    """
    Verify that the stochastic objective is the expected value
    of scenario objectives.
    """

    m = stochastic_model

    # Objective exists
    assert hasattr(m, "obj")

    expr = m.obj.expr

    # Extract additive terms from the objective
    # Expected form: sum_s p_s * objective_Cost_s
    terms = list(expr.args)
    assert len(terms) == len(m.set_scenarios)

    for s in m.set_scenarios:
        prob = m.probability_data[s]
        scen_obj = m.scenario[s].objective_Cost.expr

        # Find matching term
        matching_terms = [t for t in terms if prob in t.args and scen_obj in t.args]

    assert len(matching_terms) == 1


# Test D: One-scenario TSSP collapses to deterministic model


def test_single_scenario_equivalence(scenarios_data):
    """
    With one scenario, the objective should reduce to that scenario cost
    """
    # --- Select one scenario ---
    scenario_key = list(scenarios_data.keys())[0]
    scenario_kwargs = scenarios_data[scenario_key]

    single_scenario = {scenario_key: scenario_kwargs}
    prob_data = {scenario_key: 1.0}

    # --- Deterministic model ---
    det_model = create_model(**scenario_kwargs)
    solve_model(det_model)

    det_obj_value = value(det_model.objective_Cost)

    # --- Stochastic model (1 scenario) ---
    sp_model = StochasticPareto(
        scenarios_data=single_scenario,
        pd_data=prob_data,
    )

    solver = get_solver()
    solver.solve(sp_model)

    sp_obj_value = value(sp_model.obj)

    # --- Compare ---
    assert abs(det_obj_value - sp_obj_value) < 1e-6
