#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2026 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################
"""Small regression models for the documented end-of-contract credit expiry."""

from pathlib import Path

import pytest
import pyomo.environ as p
from pyomo.util.check_units import assert_units_consistent
from pareto.utilities.get_data import get_data
from pareto.utilities.units_support import units_setup
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    _build_midstream_module,
)


@pytest.fixture(params=["cbc", "appsi_highs"])
def expiry_solver(request):
    solver = p.SolverFactory(request.param)
    if not solver.available(exception_flag=False):
        pytest.skip(f"{request.param} is not installed")
    return solver


@pytest.fixture
def model_factory():
    path = (
        Path(__file__).parents[1]
        / "case_studies/strategic_small_case_study_midstream.xlsx"
    )
    parameters = [
        "Units",
        "MidstreamContractNode",
        "MidstreamMVC_Min",
        "MidstreamMVC_Max",
        "MidstreamMVC_Tariff",
        "MidstreamMVC_Penalty",
        "MidstreamContractDuration",
        "MidstreamMakeupAlpha",
        "MidstreamMakeupCreditCap",
    ]
    _, raw = get_data(
        path,
        model_type="strategic",
        set_list=["MidstreamReceiptNodes", "MidstreamContracts"],
        parameter_list=parameters,
    )

    def build(horizon, alpha=0.9):
        m = p.ConcreteModel()
        m.df_sets = {"MidstreamReceiptNodes": ["N27"], "MidstreamContracts": ["CT27_B"]}
        m.df_parameters = {
            "Units": raw["Units"],
            "MidstreamMakeupAlpha": {"value": alpha},
            "MidstreamMakeupCreditCap": {"N27": 0},
        }
        for key in parameters:
            if key not in m.df_parameters:
                m.df_parameters[key] = {"CT27_B": raw[key]["CT27_B"]}
        units_setup(m)
        m.s_T = p.Set(initialize=range(1, horizon + 1), ordered=True)
        m.s_N = p.Set(initialize=["N27"])
        m.s_L = p.Set(initialize=["PP", "N27"])
        m.s_LLA = p.Set(initialize=[("PP", "N27")], dimen=2)
        m.s_LLT = p.Set(initialize=[], dimen=2)
        m.v_F_Piped = p.Var(
            m.s_LLA,
            m.s_T,
            domain=p.NonNegativeReals,
            units=m.model_units["volume_time"],
        )
        m.v_F_Trucked = p.Var(
            m.s_LLT,
            m.s_T,
            domain=p.NonNegativeReals,
            units=m.model_units["volume_time"],
        )
        _build_midstream_module(m)
        for t in m.s_T:
            m.vb_y_MidStart["CT27_B", t].fix(t == 1)
            m.v_F_Piped["PP", "N27", t].fix(1 if t < 12 else 1.1 if t == 12 else 0)
        m.objective = p.Objective(expr=m.v_C_TotalMidstream)
        return m

    return build


@pytest.mark.component
@pytest.mark.parametrize("padding", [0, 1, 2])
@pytest.mark.parametrize("alpha", [0, 0.5, 0.9, 1])
def test_credit_expiry_preserves_completed_receipts(
    model_factory, expiry_solver, padding, alpha
):
    solver = expiry_solver
    m = model_factory(12 + padding, alpha)
    result = solver.solve(m)
    assert result.solver.termination_condition == p.TerminationCondition.optimal
    assert p.value(m.objective) == pytest.approx(10.285)
    assert_units_consistent(m.MidCreditRecursion)
    assert_units_consistent(m.MidExpiredCreditLimit)
    assert_units_consistent(m.MidExpiredCreditInactive)
    for t in range(1, 13):
        assert p.value(m.v_Mid_Expired["N27", t]) == pytest.approx(0)
    if padding:
        assert p.value(m.v_Mid_Expired["N27", 13]) == pytest.approx(0.1 * alpha)
        assert p.value(m.v_Mid_Credit["N27", 13]) == pytest.approx(0)
    if padding == 2:
        assert p.value(m.v_Mid_Expired["N27", 14]) == pytest.approx(0)


@pytest.mark.component
def test_cannot_expire_more_than_actual_prior_credit(model_factory, expiry_solver):
    solver = expiry_solver
    m = model_factory(13)
    m.v_Mid_Credit["N27", 12].fix(0.09)
    m.v_Mid_Expired["N27", 13].fix(0.091)
    result = solver.solve(m, load_solutions=False)
    assert result.solver.termination_condition == p.TerminationCondition.infeasible
