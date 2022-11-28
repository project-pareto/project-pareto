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
"""
Test operational model
"""
# Import Pyomo libraries
import pyomo.environ as pyo
from pyomo.util.check_units import assert_units_consistent
from pyomo.core.base import value
from pyomo.environ import Constraint

# Import IDAES solvers
from pareto.utilities.solvers import get_solver
from pareto.operational_water_management.operational_produced_water_optimization_model import (
    create_model,
    ProdTank,
    WaterQuality,
    get_operational_model_unit_container,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.units_support import (
    flatten_list,
    PintUnitExtractionVisitor,
)
from pareto.utilities.results import generate_report, PrintValues, OutputUnits
from importlib import resources
import pytest
from idaes.core.util.model_statistics import degrees_of_freedom

__author__ = "Pareto Team (Andres Calderon, M. Zamarripa)"

# -----------------------------------------------------------------------------
# Get default solver for testing
solver = get_solver("cbc")
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def build_operational_model():
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "ProductionTanks",
        "FreshwaterSources",
        "StorageSites",
        "SWDSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
    ]
    parameter_list = [
        "Units",
        "RCA",
        "FCA",
        "PCT",
        "FCT",
        "CCT",
        "PKT",
        "PRT",
        "CKT",
        "CRT",
        "PAL",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "ProductionTankCapacity",
        "DisposalCapacity",
        "CompletionsPadStorage",
        "TreatmentCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "TruckingTime",
        "DisposalPipeCapEx",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PadStorageCost",
        "PipelineOperationalCost",
        "TruckingHourlyCost",
        "FreshSourcingCost",
        "ProductionRates",
        "TreatmentEfficiency",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
    ]

    with resources.path(
        "pareto.case_studies", "EXAMPLE_INPUT_DATA_FILE_generic_operational_model.xlsx"
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)
    df_parameters["MinTruckFlow"] = 75
    df_parameters["MaxTruckFlow"] = 37000
    # create mathematical model

    def _call_model_with_config(config_dict):
        operational_model = create_model(df_sets, df_parameters, config_dict)
        return operational_model

    return _call_model_with_config


@pytest.mark.unit  # Keith
def test_basic_build(build_operational_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_operational_model(
        config_dict={
            "has_pipeline_constraints": True,
            "production_tanks": ProdTank.equalized,
            "water_quality": WaterQuality.false,
        },
    )
    assert degrees_of_freedom(m) == 133
    # Check unit config arguments
    assert len(m.config) == 3
    assert m.config.production_tanks
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_PPA, pyo.Param)
    assert isinstance(m.ProductionTankBalance, pyo.Constraint)


@pytest.mark.component
def test_strategic_model_unit_consistency(build_operational_model):
    """
    Note: There are pyomo functions like assert_units_consistent that test consistency of expressions.
    This test utilizes assert_units_consistent in addition to a special case test assertion.
    The need for this special case comes from constraints that are mathematically the same, but are not
    interpreted as such by Pyomo. An example is the storage balance constraint in time period T:
    storage at time T [bbl] = flow in [bbl/week] - flow out [bbl/week] + storage at time T-1 [bbl]
    The time unit of the flow in and flow out rate variables will always be the same as the
    length of time T that is the decision period, so the units are consistent despite [bbl] and
    [bbl/day] being inconsistent.
    """
    m = build_operational_model(
        config_dict={
            "has_pipeline_constraints": True,
            "production_tanks": ProdTank.equalized,
            "water_quality": WaterQuality.false,
        },
    )
    # Create an instance of PintUnitExtractionVisitor that can assist with getting units from constraints
    visitor = PintUnitExtractionVisitor(get_operational_model_unit_container())
    # Iterate through all Constraints
    for c in m.component_objects(Constraint):
        # If indexed, iterate through Constraint indexes
        for index in c:
            if index is None:
                condata = c

            elif index is not None:
                condata = c[index]

            # Obtain lower, upper, and body of constraint
            args = list()
            if condata.lower is not None and value(condata.lower) != 0.0:
                args.append(condata.lower)

            args.append(condata.body)

            if condata.upper is not None and value(condata.upper) != 0.0:
                args.append(condata.upper)
            # Use the visitor to extract the units of lower, upper,
            # and body of our constraint
            pint_units = [visitor.walk_expression(arg) for arg in args]
            # The units are in a nested list, flatten the list
            flat_list = flatten_list(pint_units)
            flat_list = [x for x in flat_list if x]

            # Compare all units to the first unit. Assess if the unique units are valid.
            first_unit = flat_list[0]
            # The decision period will be used to assess if the unit is valid
            decision_period_pint_unit = m.decision_period._get_pint_unit()
            for py_unit in flat_list[1:]:
                if visitor._equivalent_pint_units(first_unit, py_unit):
                    break
                # If the unit is equivalent when multiplying by the decision period,
                # the unit is consistent
                elif visitor._equivalent_pint_units(
                    first_unit * decision_period_pint_unit, py_unit
                ):
                    break
                elif visitor._equivalent_pint_units(
                    first_unit, py_unit * decision_period_pint_unit
                ):
                    break
                # otherwise, check if consistent with Pyomo's check
                else:
                    assert_units_consistent(condata)


@pytest.mark.component
def test_run_operational_model(build_operational_model):
    m = build_operational_model(
        config_dict={
            "has_pipeline_constraints": True,
            "production_tanks": ProdTank.equalized,
            "water_quality": WaterQuality.false,
        },
    )
    results = solver.solve(m, tee=True)
    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    assert degrees_of_freedom(m) == 133
    # solutions obtained from running the generic case study
    assert pytest.approx(327.9975, abs=1e-6) == pyo.value(m.v_Objective)
    assert pytest.approx(0.993, abs=1e-6) == pyo.value(
        m.v_F_Trucked["PP04", "CP01", "T1"]
    )

    # To DO:
    # 1.- add mass balance checks
    # 2.- create test marks (unit, component, etc.) (work with Ludovico/Keith)
    # 3.- skip test if solver doesnt exist


@pytest.mark.component
def test_operational_model_discrete_water_quality_build(build_operational_model):
    m = build_operational_model(
        config_dict={
            "has_pipeline_constraints": True,
            "production_tanks": ProdTank.equalized,
            "water_quality": WaterQuality.discrete,
        },
    )
    assert degrees_of_freedom(m) == 333
    # Check unit config arguments
    assert len(m.config) == 3
    assert m.config.water_quality
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.OnlyOneDiscreteQualityPerLocation, pyo.Constraint)
    assert isinstance(m.DiscreteMaxPipeFlow, pyo.Constraint)
    assert isinstance(m.SumDiscreteFlowsIsFlowPiped, pyo.Constraint)
    assert isinstance(m.DiscreteMaxTruckedFlow, pyo.Constraint)
    assert isinstance(m.SumDiscreteFlowsIsFlowTrucked, pyo.Constraint)
    assert isinstance(m.DiscreteMaxDisposalDestination, pyo.Constraint)
    assert isinstance(
        m.SumDiscreteDisposalDestinationIsDisposalDestination, pyo.Constraint
    )
    assert isinstance(m.DiscreteMaxOutStorageFlow, pyo.Constraint)
    assert isinstance(m.SumDiscreteFlowsIsFlowOutStorage, pyo.Constraint)
    assert isinstance(m.DiscreteMaxStorage, pyo.Constraint)
    assert isinstance(m.SumDiscreteStorageIsStorage, pyo.Constraint)
    assert isinstance(m.DiscreteMaxTreatmentFlow, pyo.Constraint)
    assert isinstance(m.SumDiscreteFlowsIsFlowTreatment, pyo.Constraint)
    assert isinstance(m.DiscreteMaxOutNodeFlow, pyo.Constraint)
    assert isinstance(m.SumDiscreteFlowsIsFlowOutNode, pyo.Constraint)
    assert isinstance(m.DiscreteMaxBeneficialReuseFlow, pyo.Constraint)
    assert isinstance(m.SumDiscreteFlowsIsFlowBeneficialReuse, pyo.Constraint)

    assert isinstance(m.DisposalWaterQuality, pyo.Constraint)
    assert isinstance(m.StorageSiteWaterQuality, pyo.Constraint)
    assert isinstance(m.TreatmentWaterQuality, pyo.Constraint)
    assert isinstance(m.NetworkWaterQuality, pyo.Constraint)
    assert isinstance(m.BeneficialReuseWaterQuality, pyo.Constraint)

    generate_report(
        m,
        is_print=[PrintValues.essential],
        fname="operational_results_test.xlsx",
    )
