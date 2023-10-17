#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2023 by the software owners:
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
Test strategic model
"""
# Import Pyomo libraries
import pyomo.environ as pyo
from pyomo.util.check_units import assert_units_consistent
from pyomo.core.base import value
from pyomo.environ import Constraint, units

# Import IDAES solvers
from pareto.utilities.solvers import get_solver
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    WaterQuality,
    create_model,
    solve_model,
    get_strategic_model_unit_container,
    Objectives,
    scale_model,
    PipelineCost,
    Hydraulics,
    PipelineCapacity,
    pipeline_hydraulics,
    RemovalEfficiencyMethod,
    InfrastructureTiming,
    infrastructure_timing,
)
from pareto.utilities.get_data import get_data, get_display_units
from pareto.utilities.units_support import (
    flatten_list,
    PintUnitExtractionVisitor,
)
from importlib import resources
import pytest
from idaes.core.util.model_statistics import degrees_of_freedom
from pareto.utilities.results import (
    generate_report,
    PrintValues,
    OutputUnits,
    is_feasible,
    nostdout,
)

__author__ = "Pareto Team (Andres Calderon, M. Zamarripa)"

# -----------------------------------------------------------------------------
# Get default solver for testing
solver = get_solver("cbc")
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def build_strategic_model():
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "SWDSites",
        "FreshwaterSources",
        "StorageSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
        "PipelineDiameters",
        "StorageCapacities",
        "InjectionCapacities",
        "TreatmentCapacities",
        "TreatmentTechnologies",
    ]
    parameter_list = [
        "Units",
        "PNA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NRA",
        "NSA",
        "FCA",
        "RCA",
        "RNA",
        "RSA",
        "SCA",
        "SNA",
        "ROA",
        "SOA",
        "NOA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
        "RST",
        "ROT",
        "SOT",
        "Elevation",
        "CompletionsPadOutsideSystem",
        "DesalinationTechnologies",
        "DesalinationSites",
        "BeneficialReuseCredit",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "WellPressure",
        "NodeCapacities",
        "InitialPipelineCapacity",
        "InitialPipelineDiameters",
        "InitialDisposalCapacity",
        "InitialTreatmentCapacity",
        "ReuseMinimum",
        "ReuseCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "CompletionsPadStorage",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PipelineOperationalCost",
        "FreshSourcingCost",
        "TruckingHourlyCost",
        "PipelineDiameterValues",
        "DisposalCapacityIncrements",
        "InitialStorageCapacity",
        "StorageCapacityIncrements",
        "TreatmentCapacityIncrements",
        "TreatmentEfficiency",
        "RemovalEfficiency",
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineCapexDistanceBased",
        "PipelineCapexCapacityBased",
        "PipelineCapacityIncrements",
        "PipelineExpansionDistance",
        "Hydraulics",
        "Economics",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
        "PadStorageInitialWaterQuality",
        "DisposalOperatingCapacity",
        "TreatmentExpansionLeadTime",
        "DisposalExpansionLeadTime",
        "StorageExpansionLeadTime",
        "PipelineExpansionLeadTime_Dist",
        "PipelineExpansionLeadTime_Capac",
    ]

    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.case_studies",
        "strategic_treatment_demo.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

        # create mathematical model
        def _call_model_with_config(config_dict):
            strategic_model = create_model(df_sets, df_parameters, config_dict)
            return strategic_model

    return _call_model_with_config


@pytest.mark.unit
def test_basic_build_capex_distance_based_capacity_input(build_strategic_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "node_capacity": True,
            "water_quality": WaterQuality.false,
        }
    )
    assert degrees_of_freedom(m) == 29595
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)


@pytest.mark.unit
def test_basic_build_capex_distance_based_capacity_calculated(build_strategic_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.calculated,
            "node_capacity": True,
            "water_quality": WaterQuality.false,
        }
    )
    assert degrees_of_freedom(m) == 29595
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)


@pytest.mark.unit
def test_basic_build_capex_capacity_based_capacity_input(build_strategic_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.input,
            "node_capacity": True,
            "water_quality": WaterQuality.false,
        }
    )
    assert degrees_of_freedom(m) == 29595
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)


@pytest.mark.unit
def test_basic_build_capex_capacity_based_capacity_calculated(build_strategic_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.calculated,
            "node_capacity": True,
            "water_quality": WaterQuality.false,
        }
    )
    assert degrees_of_freedom(m) == 29595
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)


def test_strategic_model_build_units_scaled_units_consistency(build_strategic_model):
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
    m = build_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.calculated,
        }
    )

    # Create an instance of PintUnitExtractionVisitor that can assist with getting units from constraints
    visitor = PintUnitExtractionVisitor(get_strategic_model_unit_container())
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


# if solver cbc exists @solver
@pytest.mark.component
def test_run_strategic_model(build_strategic_model):
    m = build_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.calculated,
            "infrastructure_timing": InfrastructureTiming.false,
        }
    )
    solver = get_solver("cbc")
    solver.options["seconds"] = 60
    results = solver.solve(m, tee=False)
    assert degrees_of_freedom(m) == 29595

    # Test report building
    [model, results_dict] = generate_report(
        m,
        results,
        is_print=PrintValues.essential,
        output_units=OutputUnits.user_units,
        fname="test_strategic_print_results.xlsx",
    )


@pytest.fixture(scope="module")
def build_reduced_strategic_model():
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "SWDSites",
        "FreshwaterSources",
        "StorageSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
        "PipelineDiameters",
        "StorageCapacities",
        "InjectionCapacities",
        "TreatmentCapacities",
        "TreatmentTechnologies",
    ]
    parameter_list = [
        "Units",
        "PNA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NRA",
        "NSA",
        "FCA",
        "RCA",
        "RNA",
        "RSA",
        "SCA",
        "SNA",
        "ROA",
        "SOA",
        "NOA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
        "RST",
        "ROT",
        "SOT",
        "Elevation",
        "CompletionsPadOutsideSystem",
        "DesalinationTechnologies",
        "DesalinationSites",
        "BeneficialReuseCredit",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "WellPressure",
        "NodeCapacities",
        "InitialPipelineCapacity",
        "InitialPipelineDiameters",
        "InitialDisposalCapacity",
        "InitialTreatmentCapacity",
        "ReuseMinimum",
        "ReuseCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "CompletionsPadStorage",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PipelineOperationalCost",
        "FreshSourcingCost",
        "TruckingHourlyCost",
        "PipelineDiameterValues",
        "DisposalCapacityIncrements",
        "InitialStorageCapacity",
        "StorageCapacityIncrements",
        "TreatmentCapacityIncrements",
        "TreatmentEfficiency",
        "RemovalEfficiency",
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineCapexDistanceBased",
        "PipelineCapexCapacityBased",
        "PipelineCapacityIncrements",
        "PipelineExpansionDistance",
        "Hydraulics",
        "Economics",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
        "PadStorageInitialWaterQuality",
        "DisposalOperatingCapacity",
        "TreatmentExpansionLeadTime",
        "DisposalExpansionLeadTime",
        "StorageExpansionLeadTime",
        "PipelineExpansionLeadTime_Dist",
        "PipelineExpansionLeadTime_Capac",
    ]

    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.case_studies",
        "strategic_small_case_study.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

        # create mathematical model
        def _call_model_with_config(config_dict):
            reduced_strategic_model = create_model(df_sets, df_parameters, config_dict)
            return reduced_strategic_model

    return _call_model_with_config


@pytest.mark.unit
def test_hydraulics_post_process_input(
    build_reduced_strategic_model,
):
    """Make a model and make sure it doesn't throw exception"""
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.input,
            "hydraulics": Hydraulics.post_process,
            "water_quality": WaterQuality.false,
        }
    )
    mh = pipeline_hydraulics(m)

    assert isinstance(mh, pyo.ConcreteModel)
    assert isinstance(mh.hydraulics, pyo.Block)
    assert isinstance(mh.hydraulics.v_Pressure, pyo.Var)
    assert isinstance(mh.hydraulics.v_PumpHead, pyo.Var)
    assert isinstance(mh.hydraulics.vb_Y_Pump, pyo.Var)
    assert isinstance(mh.hydraulics.v_ValveHead, pyo.Var)
    assert isinstance(mh.hydraulics.v_PumpCost, pyo.Var)
    assert isinstance(mh.hydraulics.p_iota_HW_material_factor_pipeline, pyo.Param)
    assert isinstance(mh.hydraulics.p_rhog, pyo.Param)
    assert isinstance(mh.hydraulics.p_nu_PumpFixedCost, pyo.Param)
    assert isinstance(mh.hydraulics.p_nu_ElectricityCost, pyo.Param)
    assert isinstance(mh.hydraulics.p_eta_PumpEfficiency, pyo.Param)
    assert isinstance(mh.hydraulics.p_eta_MotorEfficiency, pyo.Param)
    assert isinstance(mh.hydraulics.p_upsilon_WellPressure, pyo.Param)
    assert isinstance(mh.hydraulics.p_effective_Pipeline_diameter, pyo.Param)
    assert isinstance(mh.hydraulics.p_xi_Min_AOP, pyo.Param)
    assert isinstance(mh.hydraulics.p_xi_Max_AOP, pyo.Param)
    assert isinstance(mh.hydraulics.p_HW_loss, pyo.Param)
    assert isinstance(mh.hydraulics.objective, pyo.Objective)
    assert isinstance(mh.hydraulics.NodePressure, pyo.Constraint)
    assert isinstance(mh.hydraulics.MAOPressure, pyo.Constraint)
    assert isinstance(mh.hydraulics.PumpCostEq, pyo.Constraint)
    assert isinstance(mh.hydraulics.HydraulicsCostEq, pyo.Constraint)
    assert isinstance(mh.hydraulics.PumpHeadCons, pyo.Constraint)


# if solver cbc exists @solver
@pytest.mark.component
def test_run_hydraulics_post_process_reduced_strategic_model(
    build_reduced_strategic_model,
):
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "hydraulics": Hydraulics.post_process,
            "node_capacity": True,
            "water_quality": WaterQuality.false,
            "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
        }
    )

    options = {
        "deactivate_slacks": True,
        "scale_model": False,
        "scaling_factor": 1000,
        "running_time": 60 * 5,
        "gap": 0,
    }
    results = solve_model(model=m, options=options)

    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    assert degrees_of_freedom(m) == 11560
    # solutions obtained from running the reduced generic case study
    assert pytest.approx(88199.598, abs=1e-1) == pyo.value(m.v_Z)
    assert pytest.approx(26.105, abs=1e-1) == pyo.value(m.hydraulics.v_Z_HydrualicsCost)
    assert pytest.approx(24, abs=1e-1) == pyo.value(
        sum(m.hydraulics.vb_Y_Pump[key] for key in m.s_LLA)
    )

    with nostdout():
        assert is_feasible(m)


@pytest.mark.unit
def test_hydraulics_co_optimize_input(
    build_reduced_strategic_model,
):
    """Make a model and make sure it doesn't throw exception"""
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.input,
            "hydraulics": Hydraulics.co_optimize,
            "water_quality": WaterQuality.false,
        }
    )
    mh = pipeline_hydraulics(m)

    assert isinstance(mh, pyo.ConcreteModel)
    assert isinstance(mh.hydraulics, pyo.Block)
    assert isinstance(mh.hydraulics.v_Pressure, pyo.Var)
    assert isinstance(mh.hydraulics.v_PumpHead, pyo.Var)
    assert isinstance(mh.hydraulics.v_ValveHead, pyo.Var)
    assert isinstance(mh.hydraulics.v_PumpCost, pyo.Var)
    assert isinstance(mh.hydraulics.p_iota_HW_material_factor_pipeline, pyo.Param)
    assert isinstance(mh.hydraulics.p_rhog, pyo.Param)
    assert isinstance(mh.hydraulics.p_nu_PumpFixedCost, pyo.Param)
    assert isinstance(mh.hydraulics.p_nu_ElectricityCost, pyo.Param)
    assert isinstance(mh.hydraulics.p_eta_PumpEfficiency, pyo.Param)
    assert isinstance(mh.hydraulics.p_eta_MotorEfficiency, pyo.Param)
    assert isinstance(mh.hydraulics.p_upsilon_WellPressure, pyo.Param)
    assert isinstance(mh.hydraulics.v_effective_Pipeline_diameter, pyo.Var)
    assert isinstance(mh.hydraulics.p_xi_Min_AOP, pyo.Param)
    assert isinstance(mh.hydraulics.p_xi_Max_AOP, pyo.Param)
    assert isinstance(mh.hydraulics.v_HW_loss, pyo.Var)
    assert isinstance(mh.objective, pyo.Objective)
    assert isinstance(mh.hydraulics.HW_loss_equaltion, pyo.Constraint)
    assert isinstance(mh.hydraulics.NodePressure, pyo.Constraint)
    assert isinstance(mh.hydraulics.EffectiveDiameter, pyo.Constraint)
    assert isinstance(mh.hydraulics.MAOPressure, pyo.Constraint)
    assert isinstance(mh.hydraulics.PumpCostEq, pyo.Constraint)
    assert isinstance(mh.hydraulics.HydraulicsCostEq, pyo.Constraint)
    assert isinstance(mh.hydraulics.PumpHeadCons, pyo.Constraint)


@pytest.mark.unit
def test_basic_reduced_build_capex_capacity_based_capacity_calculated(
    build_reduced_strategic_model,
):
    """Make a model and make sure it doesn't throw exception"""
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.calculated,
            "water_quality": WaterQuality.false,
        }
    )
    assert degrees_of_freedom(m) == 12851
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)


@pytest.mark.unit
def test_basic_reduced_build_capex_capacity_based_capacity_input(
    build_reduced_strategic_model,
):
    """Make a model and make sure it doesn't throw exception"""
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.false,
        }
    )
    assert degrees_of_freedom(m) == 12851
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)


@pytest.mark.unit
def test_basic_reduced_build_capex_distance_based_capacity_input(
    build_reduced_strategic_model,
):
    """Make a model and make sure it doesn't throw exception"""
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.false,
        }
    )
    assert degrees_of_freedom(m) == 12851
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)


@pytest.mark.unit
def test_basic_reduced_build_discrete_water_quality_input(
    build_reduced_strategic_model,
):
    """Make a model and make sure it doesn't throw exception"""
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.discrete,
        }
    )
    assert degrees_of_freedom(m) == 103331
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
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
    assert isinstance(m.DiscreteMaxCompletionsPadIntermediateFlow, pyo.Constraint)
    assert isinstance(
        m.SumDiscreteFlowsIsFlowCompletionsPadIntermediate, pyo.Constraint
    )
    assert isinstance(m.DiscreteMaxCompletionsPadStorageFlow, pyo.Constraint)
    assert isinstance(m.SumDiscreteFlowsIsFlowCompletionsPadStorage, pyo.Constraint)
    assert isinstance(m.DiscreteMaxPadStorage, pyo.Constraint)
    assert isinstance(m.SumDiscretePadStorageIsPadStorage, pyo.Constraint)
    assert isinstance(m.DiscreteMaxFlowOutPadStorage, pyo.Constraint)
    assert isinstance(m.SumDiscreteFlowOutPadStorageIsFlowOutPadStorage, pyo.Constraint)
    assert isinstance(m.DiscreteMaxFlowInPadStorage, pyo.Constraint)
    assert isinstance(m.SumDiscreteFlowInPadStorageIsFlowInPadStorage, pyo.Constraint)
    assert isinstance(m.DiscreteMaxCompletionsDestination, pyo.Constraint)
    assert isinstance(
        m.SumDiscreteCompletionsDestinationIsCompletionsDestination, pyo.Constraint
    )
    assert isinstance(m.DisposalWaterQuality, pyo.Constraint)
    assert isinstance(m.StorageSiteWaterQuality, pyo.Constraint)
    assert isinstance(m.TreatmentWaterQuality, pyo.Constraint)
    assert isinstance(m.NetworkWaterQuality, pyo.Constraint)
    assert isinstance(m.BeneficialReuseWaterQuality, pyo.Constraint)
    assert isinstance(m.CompletionsPadIntermediateWaterQuality, pyo.Constraint)
    assert isinstance(m.CompletionsPadWaterQuality, pyo.Constraint)
    assert isinstance(m.CompletionsPadStorageWaterQuality, pyo.Constraint)


@pytest.mark.component
def test_strategic_model_scaling(build_reduced_strategic_model):
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.input,
        }
    )
    scaled_m = scale_model(m, scaling_factor=100000)
    scaled_components = []
    scaled_vars = []
    unscaled_vars = []
    scaled_constraints = []
    unscaled_constraints = []
    [scaled_components.append(i.name) for i in scaled_m.scaling_factor.keys()]

    # Checking for scaled and unscaled variables
    for v in m.component_objects(ctype=pyo.Var):
        if "vb_y" not in v.name:
            if str("scaled_" + v.name) in scaled_components:
                scaled_vars.append(v.name)
            else:
                unscaled_vars.append(v.name)

    # Checking for scaled and unscaled constraints
    for c in m.component_objects(ctype=pyo.Constraint):
        if str("scaled_" + c.name) in scaled_components:
            scaled_constraints.append(c.name)
        else:
            unscaled_constraints.append(c.name)

    assert len(unscaled_vars) == 0
    assert len(unscaled_constraints) == 0


# if solver cbc exists @solver
@pytest.mark.component
def test_run_reduced_strategic_model(build_reduced_strategic_model):
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.false,
        }
    )

    options = {
        "deactivate_slacks": True,
        "scale_model": False,
        "scaling_factor": 1000,
        "running_time": 60 * 5,
        "gap": 0,
    }
    results = solve_model(model=m, options=options)

    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    assert degrees_of_freedom(m) == 11560
    # solutions obtained from running the reduced generic case study
    assert pytest.approx(88199.598, abs=1e-1) == pyo.value(m.v_Z)
    with nostdout():
        assert is_feasible(m)


@pytest.mark.component
def test_water_quality_reduced_strategic_model_removal_concentration(
    build_reduced_strategic_model,
):
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.post_process,
            "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
        }
    )

    options = {
        "deactivate_slacks": True,
        "scale_model": False,
        "scaling_factor": 1000,
        "running_time": 60 * 5,
        "gap": 0,
    }
    results = solve_model(model=m, options=options)

    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    # solutions obtained from running the reduced generic case study water quality
    assert degrees_of_freedom(m.quality) == 1768
    assert pytest.approx(4.8342164, abs=1e-1) == pyo.value(m.quality.v_X)
    assert isinstance(m.p_epsilon_TreatmentRemoval, pyo.Param)
    assert (
        len(m.p_epsilon_TreatmentRemoval) > 1
    )  # Check if multiple components have removal efficiency values
    assert pytest.approx(0.1649151, abs=1e-6) == pyo.value(
        m.quality.v_Q["R01-PostTreatmentTreatedWaterNode", "TDS", "T01"]
    )
    assert pytest.approx(0.1649151, abs=1e-6) == pyo.value(
        m.quality.v_Q["R01-PostTreatmentTreatedWaterNode", "TDS", "T01"]
    )
    assert pytest.approx(0.0000063868, abs=1e-6) == pyo.value(
        m.quality.v_Q["R01-PostTreatmentTreatedWaterNode", "Fe", "T01"]
    )
    assert pytest.approx(0.0011560108, abs=1e-6) == pyo.value(
        m.quality.v_Q["R01-PostTreatmentResidualNode", "Fe", "T01"]
    )
    with nostdout():
        assert is_feasible(m)

    # Test report building
    [model, results_dict] = generate_report(
        m,
        results,
        is_print=PrintValues.essential,
        output_units=OutputUnits.user_units,
        fname="test_strategic_print_results.xlsx",
    )


@pytest.fixture(scope="module")
def build_modified_reduced_strategic_model():
    # This modifies the small strategic case study for load-based removal efficiency values
    # The modified excel sheet is located in the test folder
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "SWDSites",
        "FreshwaterSources",
        "StorageSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
        "PipelineDiameters",
        "StorageCapacities",
        "InjectionCapacities",
        "TreatmentCapacities",
        "TreatmentTechnologies",
    ]
    parameter_list = [
        "Units",
        "PNA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NRA",
        "NSA",
        "FCA",
        "RCA",
        "RNA",
        "RSA",
        "SCA",
        "SNA",
        "ROA",
        "SOA",
        "NOA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
        "RST",
        "ROT",
        "SOT",
        "Elevation",
        "CompletionsPadOutsideSystem",
        "DesalinationTechnologies",
        "DesalinationSites",
        "BeneficialReuseCredit",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "WellPressure",
        "NodeCapacities",
        "InitialPipelineCapacity",
        "InitialPipelineDiameters",
        "InitialDisposalCapacity",
        "InitialTreatmentCapacity",
        "ReuseMinimum",
        "ReuseCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "CompletionsPadStorage",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PipelineOperationalCost",
        "FreshSourcingCost",
        "TruckingHourlyCost",
        "PipelineDiameterValues",
        "DisposalCapacityIncrements",
        "InitialStorageCapacity",
        "StorageCapacityIncrements",
        "TreatmentCapacityIncrements",
        "TreatmentEfficiency",
        "RemovalEfficiency",
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineCapexDistanceBased",
        "PipelineCapexCapacityBased",
        "PipelineCapacityIncrements",
        "PipelineExpansionDistance",
        "Hydraulics",
        "Economics",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
        "PadStorageInitialWaterQuality",
        "DisposalOperatingCapacity",
        "TreatmentExpansionLeadTime",
        "DisposalExpansionLeadTime",
        "StorageExpansionLeadTime",
        "PipelineExpansionLeadTime_Dist",
        "PipelineExpansionLeadTime_Capac",
    ]

    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.tests",
        "strategic_small_case_study_load_removaleff.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

        # create mathematical model
        def _call_model_with_config(config_dict):
            modified_reduced_strategic_model = create_model(
                df_sets, df_parameters, config_dict
            )
            return modified_reduced_strategic_model

    return _call_model_with_config


@pytest.mark.component
def test_water_quality_reduced_strategic_model_removal_load(
    build_modified_reduced_strategic_model,
):
    m = build_modified_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.post_process,
            "removal_efficiency_method": RemovalEfficiencyMethod.load_based,
        }
    )

    options = {
        "deactivate_slacks": True,
        "scale_model": False,
        "scaling_factor": 1000,
        "running_time": 60 * 5,
        "gap": 0,
    }
    results = solve_model(model=m, options=options)

    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    # solutions obtained from running the reduced generic case study water quality
    assert degrees_of_freedom(m.quality) == 1768
    assert pytest.approx(4.8342164, abs=1e-1) == pyo.value(m.quality.v_X)
    assert isinstance(
        m.p_epsilon_TreatmentRemoval, pyo.Param
    )  # Check if the removal efficiency parameter is correctly initialized
    assert (
        len(m.p_epsilon_TreatmentRemoval) > 1
    )  # Check if multiple components have removal efficiency values
    assert pytest.approx(0.1649151, abs=1e-6) == pyo.value(
        m.quality.v_Q["R01-PostTreatmentTreatedWaterNode", "TDS", "T01"]
    )
    assert pytest.approx(0.1649151, abs=1e-6) == pyo.value(
        m.quality.v_Q["R01-PostTreatmentTreatedWaterNode", "TDS", "T01"]
    )
    assert pytest.approx(0.0000063868, abs=1e-6) == pyo.value(
        m.quality.v_Q["R01-PostTreatmentTreatedWaterNode", "Fe", "T01"]
    )
    assert pytest.approx(0.0011560108, abs=1e-6) == pyo.value(
        m.quality.v_Q["R01-PostTreatmentResidualNode", "Fe", "T01"]
    )
    with nostdout():
        assert is_feasible(m)

    # Test report building
    [model, results_dict] = generate_report(
        m,
        results,
        is_print=PrintValues.essential,
        output_units=OutputUnits.user_units,
        fname="test_strategic_print_results.xlsx",
    )


@pytest.mark.component
def test_solver_option_reduced_strategic_model(build_reduced_strategic_model):
    m = build_reduced_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.false,
        }
    )

    options = {
        "deactivate_slacks": True,
        "scale_model": False,
        "scaling_factor": 1000,
        "running_time": 60 * 5,
        "gap": 0,
        "solver": "cbc",
    }
    results = solve_model(model=m, options=options)

    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    assert degrees_of_freedom(m) == 11560
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)
    with nostdout():
        assert is_feasible(m)

    # Test report building
    [model, results_dict] = generate_report(
        m,
        results,
        is_print=PrintValues.essential,
        output_units=OutputUnits.user_units,
        fname="test_strategic_print_results.xlsx",
    )


@pytest.mark.component
def test_strategic_model_UI_display_units():
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "SWDSites",
        "FreshwaterSources",
        "StorageSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
        "PipelineDiameters",
        "StorageCapacities",
        "InjectionCapacities",
        "TreatmentCapacities",
        "TreatmentTechnologies",
    ]
    parameter_list = [
        "Units",
        "PNA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NRA",
        "NSA",
        "FCA",
        "RCA",
        "RNA",
        "RSA",
        "SCA",
        "SNA",
        "ROA",
        "SOA",
        "NOA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
        "RST",
        "ROT",
        "SOT",
        "Elevation",
        "CompletionsPadOutsideSystem",
        "DesalinationTechnologies",
        "DesalinationSites",
        "BeneficialReuseCredit",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "WellPressure",
        "NodeCapacities",
        "InitialPipelineCapacity",
        "InitialPipelineDiameters",
        "InitialDisposalCapacity",
        "InitialTreatmentCapacity",
        "ReuseMinimum",
        "ReuseCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "CompletionsPadStorage",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PipelineOperationalCost",
        "FreshSourcingCost",
        "TruckingHourlyCost",
        "PipelineDiameterValues",
        "DisposalCapacityIncrements",
        "InitialStorageCapacity",
        "StorageCapacityIncrements",
        "TreatmentCapacityIncrements",
        "TreatmentEfficiency",
        "RemovalEfficiency",
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineCapexDistanceBased",
        "PipelineCapexCapacityBased",
        "PipelineCapacityIncrements",
        "PipelineExpansionDistance",
        "Hydraulics",
        "Economics",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
        "PadStorageInitialWaterQuality",
        "DisposalOperatingCapacity",
        "TreatmentExpansionLeadTime",
        "DisposalExpansionLeadTime",
        "StorageExpansionLeadTime",
        "PipelineExpansionLeadTime_Dist",
        "PipelineExpansionLeadTime_Capac",
    ]

    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.case_studies",
        "strategic_small_case_study.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    input_sheet_names = parameter_list + set_list
    UI_display_units = get_display_units(input_sheet_names, df_parameters["Units"])
    assert UI_display_units


@pytest.fixture(scope="module")
def build_toy_strategic_model():
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "SWDSites",
        "FreshwaterSources",
        "StorageSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
        "PipelineDiameters",
        "StorageCapacities",
        "InjectionCapacities",
        "TreatmentCapacities",
        "TreatmentTechnologies",
    ]
    parameter_list = [
        "Units",
        "PNA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NRA",
        "NSA",
        "FCA",
        "RCA",
        "RNA",
        "RSA",
        "SCA",
        "SNA",
        "ROA",
        "SOA",
        "NOA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
        "RST",
        "ROT",
        "SOT",
        "Elevation",
        "CompletionsPadOutsideSystem",
        "DesalinationTechnologies",
        "DesalinationSites",
        "BeneficialReuseCredit",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "WellPressure",
        "NodeCapacities",
        "InitialPipelineCapacity",
        "InitialPipelineDiameters",
        "InitialDisposalCapacity",
        "InitialTreatmentCapacity",
        "ReuseMinimum",
        "ReuseCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "CompletionsPadStorage",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PipelineOperationalCost",
        "FreshSourcingCost",
        "TruckingHourlyCost",
        "PipelineDiameterValues",
        "DisposalCapacityIncrements",
        "InitialStorageCapacity",
        "StorageCapacityIncrements",
        "TreatmentCapacityIncrements",
        "TreatmentEfficiency",
        "RemovalEfficiency",
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineCapexDistanceBased",
        "PipelineCapexCapacityBased",
        "PipelineCapacityIncrements",
        "PipelineExpansionDistance",
        "Hydraulics",
        "Economics",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
        "PadStorageInitialWaterQuality",
        "DisposalOperatingCapacity",
        "TreatmentExpansionLeadTime",
        "DisposalExpansionLeadTime",
        "StorageExpansionLeadTime",
        "PipelineExpansionLeadTime_Dist",
        "PipelineExpansionLeadTime_Capac",
    ]

    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.case_studies",
        "strategic_toy_case_study.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

        # create mathematical model
        def _call_model_with_config(config_dict):
            toy_strategic_model = create_model(df_sets, df_parameters, config_dict)
            return toy_strategic_model

    return _call_model_with_config


@pytest.mark.unit
def test_basic_toy_build(build_toy_strategic_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_toy_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.false,
        }
    )
    assert degrees_of_freedom(m) == 7237
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)


# if solver cbc exists @solver
@pytest.mark.component
def test_run_toy_strategic_model(build_toy_strategic_model):
    m = build_toy_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.false,
            "infrastructure_timing": InfrastructureTiming.true,
        }
    )

    options = {
        "deactivate_slacks": True,
        "scale_model": False,
        "scaling_factor": 1000,
        "running_time": 60 * 5,
        "gap": 0,
    }

    results = solve_model(model=m, options=options)

    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    assert degrees_of_freedom(m) == 6875
    assert pytest.approx(6122.5178, abs=1e-1) == pyo.value(m.v_Z)
    with nostdout():
        assert is_feasible(m)


@pytest.fixture(scope="module")
def build_permian_demo_strategic_model():
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "SWDSites",
        "FreshwaterSources",
        "StorageSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
        "PipelineDiameters",
        "StorageCapacities",
        "InjectionCapacities",
        "TreatmentCapacities",
        "TreatmentTechnologies",
    ]
    parameter_list = [
        "Units",
        "PNA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NRA",
        "NSA",
        "FCA",
        "RCA",
        "RNA",
        "RSA",
        "SCA",
        "SNA",
        "ROA",
        "SOA",
        "NOA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
        "RST",
        "ROT",
        "SOT",
        "Elevation",
        "CompletionsPadOutsideSystem",
        "DesalinationTechnologies",
        "DesalinationSites",
        "BeneficialReuseCredit",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "WellPressure",
        "NodeCapacities",
        "InitialPipelineCapacity",
        "InitialPipelineDiameters",
        "InitialDisposalCapacity",
        "InitialTreatmentCapacity",
        "ReuseMinimum",
        "ReuseCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "CompletionsPadStorage",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PipelineOperationalCost",
        "FreshSourcingCost",
        "TruckingHourlyCost",
        "PipelineDiameterValues",
        "DisposalCapacityIncrements",
        "InitialStorageCapacity",
        "StorageCapacityIncrements",
        "TreatmentCapacityIncrements",
        "TreatmentEfficiency",
        "RemovalEfficiency",
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineCapexDistanceBased",
        "PipelineCapexCapacityBased",
        "PipelineCapacityIncrements",
        "PipelineExpansionDistance",
        "Hydraulics",
        "Economics",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
        "PadStorageInitialWaterQuality",
        "DisposalOperatingCapacity",
        "TreatmentExpansionLeadTime",
        "DisposalExpansionLeadTime",
        "StorageExpansionLeadTime",
        "PipelineExpansionLeadTime_Dist",
        "PipelineExpansionLeadTime_Capac",
    ]

    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.case_studies",
        "strategic_permian_demo.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

        # create mathematical model
        def _call_model_with_config(config_dict):
            permian_demo_strategic_model = create_model(
                df_sets, df_parameters, config_dict
            )
            return permian_demo_strategic_model

    return _call_model_with_config


@pytest.mark.unit
def test_basic_permian_demo_build(build_permian_demo_strategic_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_permian_demo_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "water_quality": WaterQuality.false,
        }
    )
    assert degrees_of_freedom(m) == 20955
    # Check unit config arguments
    assert len(m.config) == 8
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)
    assert isinstance(m.PipelineExpansionCapEx, pyo.Constraint)


# if solver cbc exists @solver
@pytest.mark.component
def test_run_permian_demo_strategic_model(build_permian_demo_strategic_model):
    m = build_permian_demo_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,
            "pipeline_capacity": PipelineCapacity.calculated,
        }
    )
    solver = get_solver("cbc")
    solver.options["seconds"] = 60
    results = solver.solve(m, tee=False)
    assert degrees_of_freedom(m) == 20955

    # Test report building
    [model, results_dict] = generate_report(
        m,
        is_print=PrintValues.essential,
        output_units=OutputUnits.user_units,
        fname="test_strategic_print_results.xlsx",
    )


# if solver cbc exists @solver
@pytest.mark.component
def test_infrastructure_buildout(build_toy_strategic_model):
    # Build model: Test with capacity based pipeline config option
    m_capacity_based = build_toy_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.capacity_based,  # capacity_based
            "pipeline_capacity": PipelineCapacity.input,
            "infrastructure_timing": InfrastructureTiming.true,
        }
    )

    # Build Model: Test with distance based pipeline config option
    m_distance_based = build_toy_strategic_model(
        config_dict={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,  # distance_based
            "pipeline_capacity": PipelineCapacity.calculated,
            "infrastructure_timing": InfrastructureTiming.false,
        }
    )

    # Solve models
    solver = get_solver("cbc")
    solver.options["seconds"] = 60 * 5
    results_capacity_based = solver.solve(m_capacity_based, tee=False)
    results_distance_based = solver.solve(m_distance_based, tee=False)

    # Toy case study builds treatment, storage, pipeline.
    # For testing purposes, let's adjust results to also build disposal and use new disposal.
    m_capacity_based.vb_y_Disposal["K01", "I2"].fix(1)
    m_capacity_based.v_F_DisposalDestination["K01", "T13"].fix(
        m_capacity_based.p_sigma_Disposal["K01"] * 2
    )
    m_distance_based.vb_y_Disposal[("K01", "I2")].fix(1)
    m_distance_based.v_F_DisposalDestination["K01", "T13"].fix(
        m_distance_based.p_sigma_Disposal["K01"] * 2
    )

    # Call infrastructure buildout
    infrastructure_timing(m_capacity_based)
    infrastructure_timing(m_distance_based)

    # Test results report build with infrastructure buildout
    [model, results_dict] = generate_report(
        m_capacity_based,
        is_print=PrintValues.essential,
        output_units=OutputUnits.user_units,
        fname="test_strategic_print_results.xlsx",
    )

    [model, results_dict] = generate_report(
        m_distance_based,
        is_print=PrintValues.essential,
        output_units=OutputUnits.user_units,
        fname="test_strategic_print_results.xlsx",
    )
