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
from pareto.models_extra.desalination_models.mee_mvr import make_mee_mvr_model


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
        return m.v_Ctreatin[n, t] >= 70  # g/liter

    # Add min flow constraint for desal
    # Minimum flow required for MVC model is 1kg/s ~ 800 bbl/day
    # and maximum is 20 kg/s ~ 15000 bbl/day (Already covered by p_Cap parameter)
    @m.Constraint(m.desalination_nodes, m.s_T)
    def min_flow_required_at_treatment(m, n, t):
        return sum(m.v_F[a, t] for a in m.s_Ain[n]) >= 3 / 0.0013


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


def integrated_model_build(network_data, treatment_dict={"R01_IN": 1}):
    """
    Inputs
    -------
    treatment_dict - A dictionary mapping treatment site to stages in the MEE-MVR unit
    """
    m = pyo.ConcreteModel()

    # Network Model
    m.m_network = build_network(network_data)

    add_desalination_cons(m.m_network, treatment_dict)
    manipulate_network_vars_and_cons(m.m_network)

    # Solve network model
    m.m_network.br_obj.deactivate()
    m.m_network.obj.activate()
    ipopt = pyo.SolverFactory("ipopt")

    print("#### Initializing network ####")
    ipopt.solve(m.m_network)

    # Treatment models in each period
    treatment_models = {}
    global_evap_capex_index = []
    for site in treatment_dict.keys():
        N_evap = treatment_dict[site]
        for i in m.m_network.s_T:
            treatment_models[site, i] = make_mee_mvr_model(
                N_evap=N_evap, inputs_variables=True
            )

        # Store desal site name and evaporator index for each in a
        for n in range(N_evap):
            global_evap_capex_index.append((site, n))
    m.m_treatment = pyo.Reference(treatment_models)

    # Initialize treatment models
    print("#### Initializing desalination unit ####")
    annual_fac = {}
    for site in treatment_dict.keys():
        for t in m.m_network.s_T:
            m.m_treatment[site, t].flow_feed.fix(
                pyo.value(sum(m.m_network.v_F[:, site, :, t]) * 0.0013)
            )
            m.m_treatment[site, t].salt_feed.fix(
                pyo.value(m.m_network.v_Ctreatin[site, t])
            )
            ipopt.options["tol"] = 1e-6
            res = ipopt.solve(m.m_treatment[site, i])
            try:
                pyo.assert_optimal_termination(res)
            except:
                import pdb

                pdb.set_trace()
            m.m_treatment[site, t].flow_feed.unfix()
            m.m_treatment[site, t].salt_feed.unfix()

            annual_fac[site] = pyo.value(m.m_treatment[site, t].annual_fac)

    # Global capacity variables
    # Indices for global evaporator capacity
    m.global_evaporator_capex = pyo.Var(
        global_evap_capex_index, domain=pyo.NonNegativeReals
    )
    m.global_preheater_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals
    )
    m.global_compressor_capex = pyo.Var(
        m.m_network.desalination_nodes, domain=pyo.NonNegativeReals
    )
    m.CAPEX = pyo.Var(m.m_network.desalination_nodes, domain=pyo.NonNegativeReals)
    m.OPEX = pyo.Var(
        m.m_network.desalination_nodes, m.m_network.s_T, domain=pyo.NonNegativeReals
    )

    # Initialization for global variables
    global_var_init = {}
    for site in m.m_network.desalination_nodes:
        N_evap = treatment_dict[site]
        for n in range(N_evap):
            global_var_init["global_evap_capex", site, n] = max(
                pyo.value(m.m_treatment[site, i].evaporator_capex[n])
                for i in m.m_network.s_T
            )
            m.global_evaporator_capex[site, n] = global_var_init[
                "global_evap_capex", site, n
            ]

        global_var_init["global_preheater_capex", site] = max(
            pyo.value(m.m_treatment[site, i].preheater_capex) for i in m.m_network.s_T
        )
        global_var_init["global_compressor_capex", site] = max(
            pyo.value(m.m_treatment[site, i].compressor_capex) for i in m.m_network.s_T
        )
        global_var_init["capex", site] = pyo.value(
            annual_fac[site]
            * (
                sum(
                    global_var_init["global_evap_capex", site, n] for n in range(N_evap)
                )
                + global_var_init["global_preheater_capex", site]
                + global_var_init["global_compressor_capex", site]
            )
        )

        m.global_preheater_capex[site] = global_var_init["global_preheater_capex", site]
        m.global_compressor_capex[site] = global_var_init[
            "global_compressor_capex", site
        ]
        m.CAPEX[site] = global_var_init["capex", site]
        for i in m.m_network.s_T:
            m.OPEX[site, i] = pyo.value(m.m_treatment[site, i].OPEX)

    # Linking constraints
    # Need to convert units of flow to kg/s
    def _feed_flow_link(m, s, t):
        return (
            m.m_treatment[s, t].flow_feed == sum(m.m_network.v_F[:, s, :, t]) * 0.0013
        )

    m.feed_flow_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_feed_flow_link
    )

    # Link feed composition to treatment feed composition
    def _feed_conc_link(m, s, t):
        return m.m_treatment[s, t].salt_feed == m.m_network.v_Ctreatin[s, t]

    m.feed_conc_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_feed_conc_link
    )

    # Link recovery fractions
    def _recovery_fractions_link(m, s, t):
        return m.m_network.p_alphaW[s, t] == m.m_treatment[s, t].water_recovery_fraction

    m.recovery_fractions_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_recovery_fractions_link
    )

    # Global capacity constraints
    def _global_evap_area_link(m, s, i, t):
        return (
            m.global_evaporator_capex[s, i] >= m.m_treatment[s, t].evaporator_capex[i]
        )

    m.global_evap_area_link = pyo.Constraint(
        global_evap_capex_index, m.m_network.s_T, rule=_global_evap_area_link
    )

    def _global_ph_area_link(m, s, t):
        return m.global_preheater_capex[s] >= m.m_treatment[s, t].preheater_capex

    m.global_preheater_area_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_global_ph_area_link
    )

    def _global_comp_capacity_link(m, s, t):
        return m.global_compressor_capex[s] >= m.m_treatment[s, t].compressor_capex

    m.global_compressor_capacity_link = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_global_comp_capacity_link
    )

    # Calculating CAPEX based on the global variables
    def _capex_cal(m, s):
        return m.CAPEX[s] == m.m_treatment[s, "T01"].annual_fac * (
            sum(m.global_evaporator_capex[s, i] for i in range(treatment_dict[s]))
            + m.global_compressor_capex[s]
            + m.global_preheater_capex[s]
        )

    m.capex_con = pyo.Constraint(m.m_network.desalination_nodes, rule=_capex_cal)

    # Opex calculation
    def _opex_cal(m, s, t):
        return m.OPEX[s, t] == m.m_treatment[s, t].OPEX

    m.opex_con = pyo.Constraint(
        m.m_network.desalination_nodes, m.m_network.s_T, rule=_opex_cal
    )

    # Objective function
    m.m_network.obj.deactivate()
    m.m_treatment[:, :].obj.deactivate()

    m.objective = pyo.Objective(
        expr=(
            m.m_network.obj
            + sum(m.CAPEX[s] for s in m.m_network.desalination_nodes)
            / 365
            * m.m_network.p_dt
            * len(m.m_network.s_T)
            + sum(
                sum(m.OPEX[s, t] / 365 * m.m_network.p_dt for t in m.m_network.s_T)
                for s in m.m_network.desalination_nodes
            )
        )
    )

    print("#### Build Complete #####")
    return m
