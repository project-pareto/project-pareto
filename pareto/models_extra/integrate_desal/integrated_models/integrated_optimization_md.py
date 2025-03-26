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
import pyomo.environ as pyo
from pareto.models_extra.integrate_desal.models.qcp_desal import build_network
from pareto.models_extra.desalination_models.MD_single_stage_continuous_recirculation import (
    build,
    set_operating_conditions,
    initialize_system,
    optimize_set_up,
)


def add_desalination_cons(m, treatment_dict):
    m.desalination_nodes = pyo.Set(initialize=treatment_dict.keys())
    m.v_Ctreatin = pyo.Var(m.s_NTIN, m.s_T, domain=pyo.PositiveReals)

    # Aggregate concentrations to send to desal unit
    @m.Constraint(m.s_NTIN, m.s_T)
    def concentration_aggregation(m, n, t):
        return m.v_Ctreatin[n, t] == sum(m.v_C[n, q, t] for q in m.s_Q)

    # Add minimum concentration constraint for desal
    @m.Constraint(m.desalination_nodes, m.s_T)
    def min_conc_required_at_treatment(m, n, t):
        return m.v_Ctreatin[n, t] >= 30  # g/liter

    # Add min flow constraint for desal
    # Minimum flow required for MD model is 1kg/s ~ 800 bbl/day
    # and maximum is 20 kg/s ~ 15000 bbl/day (Already covered by p_Cap parameter)
    @m.Constraint(m.desalination_nodes, m.s_T)
    def min_flow_required_at_treatment(m, n, t):
        return sum(m.v_F[a, t] for a in m.s_Ain[n]) >= 0.1 / 0.0013

    @m.Constraint(m.desalination_nodes, m.s_T)
    def max_flow_required_at_treatment(m, n, t):
        return sum(m.v_F[a, t] for a in m.s_Ain[n]) <= 1 / 0.0013

    # In the case of MD, we need to increase the disposal capacity since
    # the water that can be sent to desal is limited
    m.del_component(m.Dflow)

    @m.Constraint(m.s_ND, m.s_T, doc="Disposal flow restriction")
    def Dflow(m, n, t):
        return sum(m.v_F[a, t] for a in m.s_Ain[n]) <= 20000


def manipulate_network_vars_and_cons(m):
    # Unfix recovery fraction for desalination nodes
    for n in m.desalination_nodes:
        m.p_alphaW[n, :].unfix()

    # Set treatment cost to not include desalination unit cost
    m.del_component(m.treat_cost)

    @m.Expression()
    def treat_cost(m):
        return (
            sum(
                sum(
                    m.p_betaT[n] * sum(m.v_F[a, t] for a in m.s_Ain[n])
                    for n in m.s_NTIN
                    if n not in m.desalination_nodes
                )
                for t in m.s_T
            )
            * m.p_dt
        )


def initialize_capacity_variables(m):
    for site in m.m_network.desalination_nodes:
        m.global_md_capex[site] = max(
            pyo.value(
                m.m_treatment[site, i].fs.MD.costing.capital_cost
                * m.m_treatment[site, i].fs.costing.capital_recovery_factor
            )
            for i in m.m_network.s_T
        )

        m.global_hx_capex[site] = max(
            pyo.value(
                m.m_treatment[site, i].fs.hx.costing.capital_cost
                * m.m_treatment[site, i].fs.costing.capital_recovery_factor
            )
            for i in m.m_network.s_T
        )

        m.global_heater_capex[site] = max(
            pyo.value(
                m.m_treatment[site, i].fs.heater.costing.capital_cost
                * m.m_treatment[site, i].fs.costing.capital_recovery_factor
            )
            for i in m.m_network.s_T
        )

        m.global_chiller_capex[site] = max(
            pyo.value(
                m.m_treatment[site, i].fs.chiller.costing.capital_cost
                * m.m_treatment[site, i].fs.costing.capital_recovery_factor
            )
            for i in m.m_network.s_T
        )

        m.global_pump_brine_capex[site] = max(
            pyo.value(
                m.m_treatment[site, i].fs.pump_brine.costing.capital_cost
                * m.m_treatment[site, i].fs.costing.capital_recovery_factor
            )
            for i in m.m_network.s_T
        )

        m.global_pump_permeate_capex[site] = max(
            pyo.value(
                m.m_treatment[site, i].fs.pump_permeate.costing.capital_cost
                * m.m_treatment[site, i].fs.costing.capital_recovery_factor
            )
            for i in m.m_network.s_T
        )

        m.global_pump_feed_capex[site] = max(
            pyo.value(
                m.m_treatment[site, i].fs.pump_feed.costing.capital_cost
                * m.m_treatment[site, i].fs.costing.capital_recovery_factor
            )
            for i in m.m_network.s_T
        )

        m.global_mixer_capex[site] = max(
            pyo.value(
                m.m_treatment[site, i].fs.mixer.costing.capital_cost
                * m.m_treatment[site, i].fs.costing.capital_recovery_factor
            )
            for i in m.m_network.s_T
        )

        m.CAPEX[site] = pyo.value(
            m.global_md_capex[site]
            + m.global_hx_capex[site]
            + m.global_heater_capex[site]
            + m.global_chiller_capex[site]
            + m.global_pump_brine_capex[site]
            + m.global_pump_permeate_capex[site]
            + m.global_pump_feed_capex[site]
            + m.global_mixer_capex[site]
        )

        for t in m.m_network.s_T:
            m.OPEX[site, t] = pyo.value(
                m.m_treatment[site, t].fs.costing.total_operating_cost
            )


def integrated_model_build(network_data, treatment_dict={"R01_IN": "MD"}):
    """
    Inputs
    -------
    treatment_dict - A dictionary mapping treatment site to stages in the MEE-MVR unit
    """
    m = pyo.ConcreteModel()

    # Network Model
    m.m_network = build_network(network_data)

    add_desalination_cons(m.m_network, treatment_dict)

    # Solve network model
    m.m_network.br_obj.deactivate()
    m.m_network.obj.activate()
    ipopt = pyo.SolverFactory("ipopt")

    print("#### Initializing network ####")
    ipopt.solve(m.m_network, tee=True)

    manipulate_network_vars_and_cons(m.m_network)

    # Treatment models in each period
    treatment_models = {}
    for site in treatment_dict.keys():
        for i in m.m_network.s_T:
            treatment_models[site, i] = build()

    m.m_treatment = pyo.Reference(treatment_models)

    # Initialize treatment models
    print("#### Initializing desalination unit ####")
    for site in treatment_dict.keys():
        for t in m.m_network.s_T:
            # total mass flow rate in kg/s
            feed_flow_mass = pyo.value(sum(m.m_network.v_F[:, site, :, t]) * 0.0013)

            # Total concentration in g/kg
            conc = pyo.value(m.m_network.v_Ctreatin[site, t])

            # feed mass frac of solids
            feed_mass_frac_solids = conc / 1000

            # Initialize the model
            set_operating_conditions(
                m.m_treatment[site, t],
                feed_flow_mass=feed_flow_mass,
                feed_mass_frac_TDS=feed_mass_frac_solids,
            )

            initialize_system(m.m_treatment[site, t], solver=ipopt)

            optimize_set_up(m.m_treatment[site, t])
            m.m_treatment[site, t].fs.feed.properties[0].flow_mass_phase_comp[
                "Liq", "H2O"
            ].unfix()
            m.m_treatment[site, t].fs.feed.properties[0].flow_mass_phase_comp[
                "Liq", "NaCl"
            ].unfix()
            print(
                "############# Initialized desalination unit in  %s timeperiod ####################"
                % t
            )

    # Global capacity variables
    # MD module
    m.global_md_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals, initialize=100
    )

    # Heat exchanger module
    m.global_hx_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals, initialize=100
    )

    # Heater module
    m.global_heater_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals, initialize=100
    )

    # Chiller module
    m.global_chiller_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals, initialize=100
    )

    # Brine pump
    m.global_pump_brine_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals, initialize=100
    )

    # Permeate pump
    m.global_pump_permeate_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals, initialize=100
    )

    # Feed pump
    m.global_pump_feed_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals, initialize=100
    )

    # Mixer
    m.global_mixer_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals, initialize=100
    )

    # Total CAPEX
    m.CAPEX = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals, initialize=100
    )

    # OPEX
    m.OPEX = pyo.Var(
        m.m_network.desalination_nodes,
        m.m_network.s_T,
        domain=pyo.NonNegativeReals,
        initialize=100,
    )

    # Initialize capacity variables
    initialize_capacity_variables(m)

    # Linking constraints
    def _feed_flow_link(m, s, t):
        # total mass flow rate in kg/s
        feed_flow_mass = (
            sum(m.m_network.v_F[a, t] for a in m.m_network.s_Ain[s]) * 0.0013
        )

        # Total concentration in g/kg
        conc = m.m_network.v_Ctreatin[s, t]

        # feed flow rate of solids (kg/s)
        feed_flow_solids = feed_flow_mass * conc / 1000

        # Feed flowrate of water
        feed_flow_water = feed_flow_mass - feed_flow_solids
        return (
            m.m_treatment[s, t].fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"]
            == feed_flow_water
        )

    m.feed_flow_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_feed_flow_link
    )

    # Link feed composition to treatment feed composition
    def _feed_conc_link(m, s, t):
        # total mass flow rate in kg/s
        feed_flow_mass = (
            sum(m.m_network.v_F[a, t] for a in m.m_network.s_Ain[s]) * 0.0013
        )

        # Total concentration in g/kg
        conc = m.m_network.v_Ctreatin[s, t]

        # feed flow rate of solids (kg/s)
        feed_flow_solids = feed_flow_mass * conc / 1000

        return (
            m.m_treatment[s, t]
            .fs.feed.properties[0]
            .flow_mass_phase_comp["Liq", "NaCl"]
            == feed_flow_solids
        )

    m.feed_conc_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_feed_conc_link
    )

    # Link recovery fractions
    def _recovery_fractions_link(m, s, t):
        return m.m_network.p_alphaW[s, t] == m.m_treatment[s, t].fs.overall_recovery

    m.recovery_fractions_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_recovery_fractions_link
    )

    # Global capacity constraints
    def _global_md_capex_link(m, s, t):
        return (
            m.global_md_capex[s]
            >= m.m_treatment[s, t].fs.MD.costing.capital_cost
            * m.m_treatment[s, t].fs.costing.capital_recovery_factor
        )

    m.global_md_capex_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_global_md_capex_link
    )

    def _global_hx_capex_link(m, s, t):
        return (
            m.global_hx_capex[s]
            >= m.m_treatment[s, t].fs.hx.costing.capital_cost
            * m.m_treatment[s, t].fs.costing.capital_recovery_factor
        )

    m.global_hx_capex_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_global_hx_capex_link
    )

    def _global_heater_capex_link(m, s, t):
        return (
            m.global_heater_capex[s]
            >= m.m_treatment[s, t].fs.heater.costing.capital_cost
            * m.m_treatment[s, t].fs.costing.capital_recovery_factor
        )

    m.global_heater_capex_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_global_heater_capex_link
    )

    def _global_chiller_capex_link(m, s, t):
        return (
            m.global_chiller_capex[s]
            >= m.m_treatment[s, t].fs.chiller.costing.capital_cost
            * m.m_treatment[s, t].fs.costing.capital_recovery_factor
        )

    m.global_chiller_capex_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_global_chiller_capex_link
    )

    def _global_pump_brine_capex_link(m, s, t):
        return (
            m.global_pump_brine_capex[s]
            >= m.m_treatment[s, t].fs.pump_brine.costing.capital_cost
            * m.m_treatment[s, t].fs.costing.capital_recovery_factor
        )

    m.global_pump_brine_capex_link = pyo.Constraint(
        m.m_network.desalination_nodes,
        m.m_network.s_T,
        rule=_global_pump_brine_capex_link,
    )

    def _global_pump_permeate_capex_link(m, s, t):
        return (
            m.global_pump_permeate_capex[s]
            >= m.m_treatment[s, t].fs.pump_permeate.costing.capital_cost
            * m.m_treatment[s, t].fs.costing.capital_recovery_factor
        )

    m.global_pump_permeate_capex_link = pyo.Constraint(
        m.m_network.desalination_nodes,
        m.m_network.s_T,
        rule=_global_pump_permeate_capex_link,
    )

    def _global_pump_feed_capex_link(m, s, t):
        return (
            m.global_pump_feed_capex[s]
            >= m.m_treatment[s, t].fs.pump_feed.costing.capital_cost
            * m.m_treatment[s, t].fs.costing.capital_recovery_factor
        )

    m.global_pump_feed_capex_link = pyo.Constraint(
        m.m_network.desalination_nodes,
        m.m_network.s_T,
        rule=_global_pump_feed_capex_link,
    )

    def _global_mixer_capex_link(m, s, t):
        return (
            m.global_mixer_capex[s]
            >= m.m_treatment[s, t].fs.mixer.costing.capital_cost
            * m.m_treatment[s, t].fs.costing.capital_recovery_factor
        )

    m.global_mixer_capex_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_global_mixer_capex_link
    )

    # Calculating CAPEX based on the global variables
    def _capex_cal(m, s):
        return m.CAPEX[s] == (
            m.global_md_capex[s]
            + m.global_hx_capex[s]
            + m.global_heater_capex[s]
            + m.global_chiller_capex[s]
            + m.global_pump_brine_capex[s]
            + m.global_pump_permeate_capex[s]
            + m.global_pump_feed_capex[s]
            + m.global_mixer_capex[s]
        )

    m.capex_con = pyo.Constraint(m.m_network.desalination_nodes, rule=_capex_cal)

    # Opex calculation
    def _opex_cal(m, s, t):
        return m.OPEX[s, t] == m.m_treatment[s, t].fs.costing.total_operating_cost

    m.opex_con = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_opex_cal
    )

    # Objective function
    m.m_network.obj.deactivate()
    m.m_treatment[:, :].fs.objective.deactivate()

    m.objective = pyo.Objective(
        expr=1e-3
        * (
            m.m_network.obj
            + sum(m.CAPEX[s] for s in m.m_network.desalination_nodes)
            / 1000
            / 365
            * m.m_network.p_dt
            * len(m.m_network.s_T)
            + sum(
                sum(
                    m.OPEX[s, t] / 1000 / 365 * m.m_network.p_dt
                    for t in m.m_network.s_T
                )
                for s in m.m_network.desalination_nodes
            )
        )
    )
    print("#### Build Complete #####")
    return m
