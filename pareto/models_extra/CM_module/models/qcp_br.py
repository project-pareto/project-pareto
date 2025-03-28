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
Qudratically-Constrained Program (QCP) to find the optimal operational conditions
to meet minimum critical mineral requirements within a produced water network.
"""
import sys
import pyomo.environ as pyo


def build_qcp_br(data):
    model = pyo.ConcreteModel()

    # -------------------SETS-----------------------------
    # Nodes
    model.s_N = pyo.Set(initialize=data["s_N"], doc="Nodes")
    model.s_NMS = pyo.Set(initialize=data["s_NMS"], doc="Mixers/Splitters")
    model.s_NP = pyo.Set(initialize=data["s_NP"], doc="Production pads")
    model.s_NC = pyo.Set(initialize=data["s_NC"], doc="Completion pads")
    model.s_NS = pyo.Set(initialize=data["s_NS"], doc="Storage")
    model.s_ND = pyo.Set(initialize=data["s_ND"], doc="Disposal")
    model.s_NW = pyo.Set(initialize=data["s_NW"], doc="Fresh water source")
    model.s_NTIN = pyo.Set(initialize=data["s_NTIN"], doc="Inlet to Treatment Facility")
    model.s_NTTW = pyo.Set(
        initialize=data["s_NTTW"], doc="Treated Water of Treatment Facility"
    )
    model.s_NTCW = pyo.Set(
        initialize=data["s_NTCW"], doc="Concentrated Water of Treatment Facility"
    )

    # Arcs
    model.s_A = pyo.Set(initialize=data["s_A"], doc="Arcs")
    model.s_Ain = pyo.Param(
        model.s_N, initialize=data["s_Ain"], doc="Arcs going into node", within=pyo.Any
    )
    model.s_Aout = pyo.Param(
        model.s_N,
        initialize=data["s_Aout"],
        doc="Arcs coming out of node",
        within=pyo.Any,
    )

    # Components
    model.s_Q = pyo.Set(initialize=data["s_Q"], doc="Components")
    model.s_Qalpha = pyo.Param(
        model.s_NTIN,
        initialize=data["s_Qalpha"],
        doc="Components being treated at Treated Water Node",
        within=pyo.Any,
    )

    # Time Periods
    model.s_T = pyo.Set(initialize=data["s_T"], doc="Time Periods")

    # ----------------------PARAMETERS-------------------------------------
    # Generation and Consumption Parameters
    model.p_FGen = pyo.Param(
        model.s_NMS | model.s_NP | model.s_NC,
        model.s_T,
        initialize=data["p_FGen"],
        doc="Flow Generated",
        within=pyo.Reals,
    )
    model.p_CGen = pyo.Param(
        model.s_NMS | model.s_NP | model.s_NC,
        model.s_Q,
        model.s_T,
        initialize=data["p_CGen"],
        doc="Concentration in flow generated",
        within=pyo.Reals,
    )

    model.p_FCons = pyo.Param(
        model.s_NMS | model.s_NP | model.s_NC,
        model.s_T,
        initialize=data["p_FCons"],
        doc="Flow consumed",
        within=pyo.Reals,
    )

    # Inventory Parameters
    model.p_I0 = pyo.Param(
        model.s_NS, initialize=data["p_I0"], doc="Initial Inventory", within=pyo.Reals
    )
    model.p_C0 = pyo.Param(
        model.s_NS,
        model.s_Q,
        initialize=data["p_C0"],
        doc="Initial Concentration",
        within=pyo.Reals,
    )

    # Treatment Efficiencies
    model.p_alpha = pyo.Param(
        model.s_NTIN,
        model.s_Q,
        initialize=data["p_alpha"],
        doc="Treatment Efficiency",
        within=pyo.Reals,
    )
    model.p_alphaW = pyo.Param(
        model.s_NTIN,
        initialize=data["p_alphaW"],
        doc="Removal Efficiency",
        within=pyo.Reals,
    )

    # Capacity limits for sinks
    model.p_Cap = pyo.Param(
        model.s_ND | model.s_NW | model.s_NTIN,
        initialize=data["p_Cap"],
        doc="Capacity of sources and sinks",
        within=pyo.Reals,
    )

    # Time discretization
    model.p_dt = pyo.Param(
        initialize=data["p_dt"], doc="Time discretized for inventory", within=pyo.Reals
    )

    # Minimum treatment concentration required
    model.p_Cmin = pyo.Param(
        model.s_NTCW,
        model.s_Q,
        initialize=data["p_Cmin"],
        mutable=True,
        doc="Minimum concentration required at the concentrated water node",
        within=pyo.Reals,
    )
    model.p_Fmin = pyo.Param(
        model.s_NTIN,
        initialize=data["p_Fmin"],
        mutable=True,
        doc="Minimum Flow required at each treatment site",
        within=pyo.Reals,
    )

    # Cost Parameters
    model.p_betaArc = pyo.Param(
        model.s_A,
        initialize=data["p_betaArc"],
        doc="Operational costs of arcs",
        within=pyo.Reals,
    )
    model.p_betaD = pyo.Param(
        model.s_ND,
        initialize=data["p_betaD"],
        mutable=True,
        doc="Operational cost of disposal site",
        within=pyo.Reals,
    )
    model.p_betaW = pyo.Param(
        model.s_NW,
        initialize=data["p_betaW"],
        doc="Costs of sourcing freshwater",
        within=pyo.Reals,
    )
    model.p_betaT = pyo.Param(
        model.s_NTIN,
        initialize=data["p_betaT"],
        mutable=True,
        doc="Operating cost of treatment facility",
        within=pyo.Reals,
    )
    model.p_betaS = pyo.Param(
        model.s_NS,
        initialize=data["p_betaS"],
        mutable=True,
        doc="Costs of storing produced water",
        within=pyo.Reals,
    )
    model.p_betaR = pyo.Param(
        model.s_NTTW,
        initialize=data["p_betaR"],
        doc="Cost of beneficial reuse operation",
        within=pyo.Reals,
    )

    model.p_gammaS = pyo.Param(
        model.s_NS,
        initialize=data["p_gammaS"],
        mutable=True,
        doc="Earnings from retrieving water from storage tanks",
        within=pyo.Reals,
    )
    model.p_gammaT = pyo.Param(
        model.s_NTCW,
        model.s_Q,
        initialize=data["p_gammaT"],
        doc="Earnings from each component",
        within=pyo.Reals,
    )
    model.p_gammaR = pyo.Param(
        model.s_NTTW,
        initialize=data["p_gammaR"],
        doc="Earnings from beneficial reuse",
        within=pyo.Reals,
    )

    # Functions
    model.p_nodeUp = pyo.Param(
        model.s_A,
        initialize=data["p_nodeUp"],
        doc="Upstream node of the arc",
        within=pyo.Any,
    )
    model.p_nodeDown = pyo.Param(
        model.s_A,
        initialize=data["p_nodeDown"],
        doc="Downstream node of the arc",
        within=pyo.Any,
    )
    model.p_tp = pyo.Param(
        model.s_A, initialize=data["p_tp"], doc="Type of arc", within=pyo.Any
    )
    model.p_treatedIN = pyo.Param(
        model.s_NTTW | model.s_NTCW,
        initialize=data["p_treatedIN"],
        doc="Inlet node for each treatment facility",
        within=pyo.Any,
    )

    # --------------------VARIABLES-----------------------------
    model.v_F = pyo.Var(
        model.s_A,
        model.s_T,
        bounds=data["p_Fbounds"],
        doc="Flow in arc",
        initialize=1000,
    )
    model.v_C = pyo.Var(
        model.s_N - model.s_ND,
        model.s_Q,
        model.s_T,
        bounds=data["p_Cbounds"],
        doc="Composition in node",
        initialize=20,
    )
    model.v_I = pyo.Var(
        model.s_NS,
        model.s_T,
        bounds=data["p_Ibounds"],
        doc="Inventory in node",
        initialize=1000,
    )

    # ----------------------OBJECTIVE---------------------------

    @model.Expression()
    def arc_cost(m):
        return (
            sum(sum(m.p_betaArc[a] * m.v_F[a, t] for a in m.s_A) for t in m.s_T)
            * m.p_dt
        )

    @model.Expression()
    def disp_cost(m):
        return (
            sum(
                sum(m.p_betaD[n] * sum(m.v_F[a, t] for a in m.s_Ain[n]) for n in m.s_ND)
                for t in m.s_T
            )
            * m.p_dt
        )

    @model.Expression()
    def fresh_cost(m):
        return (
            sum(
                sum(
                    m.p_betaW[n] * sum(m.v_F[a, t] for a in m.s_Aout[n]) for n in m.s_NW
                )
                for t in m.s_T
            )
            * m.p_dt
        )

    @model.Expression()
    def treat_cost(m):
        return (
            sum(
                sum(
                    m.p_betaT[n] * sum(m.v_F[a, t] for a in m.s_Ain[n])
                    for n in m.s_NTIN
                )
                for t in m.s_T
            )
            * m.p_dt
        )

    @model.Expression()
    def stor_cost(m):
        return (
            sum(
                sum(m.p_betaS[n] * sum(m.v_F[a, t] for a in m.s_Ain[n]) for n in m.s_NS)
                for t in m.s_T
            )
            * m.p_dt
        )

    @model.Expression()
    def stor_rev(m):
        return (
            sum(
                sum(
                    m.p_gammaS[n] * sum(m.v_F[a, t] for a in m.s_Aout[n])
                    for n in m.s_NS
                )
                for t in m.s_T
            )
            * m.p_dt
        )

    @model.Expression()
    def treat_rev(m):
        return (
            sum(
                sum(
                    sum(
                        sum(m.p_gammaT[n, q] * m.v_F[a, t] for q in m.s_Q)
                        for a in m.s_Aout[n]
                    )
                    for n in m.s_NTCW
                )
                for t in m.s_T
            )
            * m.p_dt
        )

    @model.Expression()
    def ben_reuse_net_cost(m):
        return (
            sum(
                sum(
                    (m.p_betaR[n] - m.p_gammaR[n])
                    * sum(m.v_F[a, t] for a in m.s_Aout[n])
                    for n in m.s_NTTW
                )
                for t in m.s_T
            )
            * m.p_dt
        )

    @model.Objective(doc="Maximize treatment revenue only")
    def treatment_only_obj(m):
        return -m.treat_rev

    model.treatment_only_obj.deactivate()

    @model.Expression()
    def total_cost(m):
        return (
            m.arc_cost
            + m.disp_cost
            + m.fresh_cost
            + m.treat_cost
            + m.stor_cost
            - m.stor_rev
            - m.treat_rev
        )

    @model.Objective(doc="Cost Minimization Objective")
    def obj(m):
        return m.total_cost / 1000

    model.obj.deactivate()

    @model.Expression()
    def total_cost_w_br(m):
        return (
            m.arc_cost
            + m.disp_cost
            + m.fresh_cost
            + m.treat_cost
            + m.stor_cost
            - m.stor_rev
            - m.treat_rev
            + m.ben_reuse_net_cost
        )

    @model.Objective(doc="Objective with beneficial reuse consideration")
    def br_obj(m):
        return m.total_cost_w_br / 1000

    # ---------------------------CONSTRAINTS-----------------------------------
    # flow for non-inventory terms
    @model.Constraint(
        model.s_NP | model.s_NMS,
        model.s_T,
        doc="General flow equation for non inventory nodes",
    )
    def noinvflow(m, n, t):
        return (
            sum(m.v_F[a, t] for a in m.s_Ain[n]) + m.p_FGen[n, t]
            == sum(m.v_F[a, t] for a in m.s_Aout[n]) + m.p_FCons[n, t]
        )

    # Splitter and Mixers
    @model.Constraint(
        model.s_NMS, model.s_Q, model.s_T, doc="Mixer/Splitter Concentration "
    )
    def MSconc(m, n, q, t):
        if len(m.s_Ain[n]) == 1:
            a = m.s_Ain[n][0]
            return m.v_C[m.p_nodeUp[a], q, t] == m.v_C[n, q, t]

        elif len(m.s_Ain[n]) > 1:
            return (
                sum(m.v_F[a, t] * m.v_C[m.p_nodeUp[a], q, t] for a in m.s_Ain[n])
                == sum(m.v_F[a, t] for a in m.s_Aout[n]) * m.v_C[n, q, t]
            )
        else:
            print("Error: MS has no inlet")

    # Production Pads
    @model.Constraint(
        model.s_NP, model.s_Q, model.s_T, doc="Production Pads Concentration"
    )
    def Pconc(m, n, q, t):
        assert len(m.s_Ain[n]) == 0
        return m.v_C[n, q, t] == m.p_CGen[n, q, t]

    # Completion Pads
    # flow and concentration constraints are done together below
    model.Cflow = pyo.ConstraintList(doc="Completions pad flow")
    model.Cconc = pyo.ConstraintList(doc="Completions pad Concentration")
    for n in model.s_NC:
        for t in model.s_T:
            # condition where completion pad is producing
            if model.p_FGen[n, t] > 0 and model.p_FCons[n, t] == 0:
                model.Cflow.add(
                    model.p_FGen[n, t] == sum(model.v_F[a, t] for a in model.s_Aout[n])
                )  # flow constraint
                model.Cflow.add(
                    0 == sum(model.v_F[a, t] for a in model.s_Ain[n])
                )  # flow constraint
                for q in model.s_Q:
                    model.Cconc.add(
                        model.v_C[n, q, t] == model.p_CGen[n, q, t]
                    )  # conc constraint

            # condition where completion pad is consuming
            elif model.p_FGen[n, t] == 0 and model.p_FCons[n, t] > 0:
                model.Cflow.add(
                    model.p_FCons[n, t] == sum(model.v_F[a, t] for a in model.s_Ain[n])
                )  # flow constraint
                model.Cflow.add(
                    0 == sum(model.v_F[a, t] for a in model.s_Aout[n])
                )  # flow constraint

            # condition where completion pad is neither producing nor consuming
            elif model.p_FGen[n, t] == 0 and model.p_FCons[n, t] == 0:
                model.Cflow.add(
                    0 == sum(model.v_F[a, t] for a in model.s_Aout[n])
                )  # flow constraint
                model.Cflow.add(
                    0 == sum(model.v_F[a, t] for a in model.s_Ain[n])
                )  # flow constraint
                for q in model.s_Q:
                    model.Cconc.add(model.v_C[n, q, t] == 0)  # conc constraints

            # condition where completion pad is both producing and consuming
            elif model.p_FGen[n, t] > 0 and model.p_FCons[n, t] > 0:
                model.Cflow.add(
                    model.p_FGen[n, t] == sum(model.v_F[a, t] for a in model.s_Aout[n])
                )  # flow constraint
                model.Cflow.add(
                    model.p_FCons[n, t] == sum(model.v_F[a, t] for a in model.s_Ain[n])
                )  # flow constraint
                for q in model.s_Q:
                    model.Cconc.add(
                        model.v_C[n, q, t] == model.p_CGen[n, q, t]
                    )  # conc constraint

    # Storage
    @model.Constraint(model.s_NS, model.s_T, doc="Storage inventory balance")
    def Sinv(m, n, t):
        if t == m.s_T.first():
            return (
                m.v_I[n, t]
                == m.p_I0[n]
                + sum(m.v_F[a, t] for a in m.s_Ain[n]) * m.p_dt
                - sum(m.v_F[a, t] for a in m.s_Aout[n]) * m.p_dt
            )
        else:
            return (
                m.v_I[n, t]
                == m.v_I[n, m.s_T.prev(t)]
                + sum(m.v_F[a, t] for a in m.s_Ain[n]) * m.p_dt
                - sum(m.v_F[a, t] for a in m.s_Aout[n]) * m.p_dt
            )

    @model.Constraint(
        model.s_NS, model.s_Q, model.s_T, doc="Storage concentration balance"
    )
    def Sconc(m, n, q, t):
        if t == m.s_T.first():
            return (
                m.v_I[n, t] * m.v_C[n, q, t]
                == m.p_I0[n] * m.p_C0[n, q]
                + sum(m.v_F[a, t] * m.v_C[m.p_nodeUp[a], q, t] for a in m.s_Ain[n])
                * m.p_dt
                - m.v_C[n, q, t] * sum(m.v_F[a, t] for a in m.s_Aout[n]) * m.p_dt
            )
        else:
            return (
                m.v_I[n, t] * m.v_C[n, q, t]
                == m.v_I[n, m.s_T.prev(t)] * m.v_C[n, q, m.s_T.prev(t)]
                + sum(m.v_F[a, t] * m.v_C[m.p_nodeUp[a], q, t] for a in m.s_Ain[n])
                * m.p_dt
                - m.v_C[n, q, t] * sum(m.v_F[a, t] for a in m.s_Aout[n]) * m.p_dt
            )

    # Disposal
    @model.Constraint(model.s_ND, model.s_T, doc="Disposal flow restriction")
    def Dflow(m, n, t):
        return sum(m.v_F[a, t] for a in m.s_Ain[n]) <= m.p_Cap[n]

    # Freshwater
    @model.Constraint(model.s_NW, model.s_T, doc="Freshwater flow restriction")
    def Wflow(m, n, t):
        return sum(m.v_F[a, t] for a in m.s_Aout[n]) <= m.p_Cap[n]

    @model.Constraint(model.s_NW, model.s_Q, model.s_T, doc="Freshwater concentration")
    def Wconc(m, n, q, t):
        return m.v_C[n, q, t] == 0

    # Treatment Inlet Node
    @model.Constraint(model.s_NTIN, model.s_T, doc="Treatment inlet flow restriction")
    def TINflow(m, n, t):
        return sum(m.v_F[a, t] for a in m.s_Ain[n]) <= m.p_Cap[n]

    @model.Constraint(
        model.s_NTIN, model.s_Q, model.s_T, doc="Treatment inlet concentration"
    )
    def TINconc(m, n, q, t):
        assert len(m.s_Ain[n]) == 1
        a = m.s_Ain[n][0]
        return m.v_C[n, q, t] == m.v_C[m.p_nodeUp[a], q, t]

    # Treatment Treated Water Node
    @model.Constraint(model.s_NTTW, model.s_T, doc="Flow of Treated Water Stream")
    def NTTWflow(m, n, t):
        assert len(m.s_Aout[n]) == 1
        n1 = m.p_treatedIN[n]
        return m.v_F[m.s_Aout[n][0], t] == m.p_alphaW[n1] * (m.v_F[m.s_Ain[n1][0], t])

    model.NTTWconc = pyo.ConstraintList(
        doc="Concentration of components being treated at Treated Water Node"
    )
    for n in model.s_NTTW:
        assert len(model.s_Aout[n]) == 1
        n1 = model.p_treatedIN[n]
        for t in model.s_T:
            for q in model.s_Qalpha[n1]:
                model.NTTWconc.add(
                    model.v_C[n, q, t]
                    == (1 - model.p_alpha[n1, q]) * model.v_C[n1, q, t]
                )

    # Treatment Concentrated Water Node
    @model.Constraint(model.s_NTCW, model.s_T, doc="Flow of Concentrated Water Stream")
    def NTCWflow(m, n, t):
        assert len(m.s_Aout[n]) == 1
        n1 = m.p_treatedIN[n]
        return m.v_F[m.s_Aout[n][0], t] == (1 - m.p_alphaW[n1]) * (
            m.v_F[m.s_Ain[n1][0], t]
        )

    model.NTCWconc = pyo.ConstraintList(
        doc="Concentration of components being treated at Concentrated Water Node"
    )
    for n in model.s_NTCW:
        assert len(model.s_Aout[n]) == 1
        n1 = model.p_treatedIN[n]
        for t in model.s_T:
            for q in model.s_Qalpha[n1]:
                model.NTCWconc.add(
                    model.v_C[n, q, t]
                    == (
                        (
                            1
                            - model.p_alphaW[n1]
                            + model.p_alpha[n1, q] * model.p_alphaW[n1]
                        )
                        / (1 - model.p_alphaW[n1])
                    )
                    * model.v_C[n1, q, t]
                )

    # Treatment: Cases where treatment is acting as a splitter
    model.NTSrcconc = pyo.ConstraintList(
        doc="Concentration of components not being treated"
    )
    for n in model.s_NTTW | model.s_NTCW:
        assert len(model.s_Aout[n]) == 1
        n1 = model.p_treatedIN[n]
        for t in model.s_T:
            for q in model.s_Q - model.s_Qalpha[n1]:
                model.NTSrcconc.add(model.v_C[n, q, t] == model.v_C[n1, q, t])

    # Restricting the minimum concentration at the concentrated water node
    @model.Constraint(
        model.s_NTCW,
        model.s_Q,
        model.s_T,
        doc="Minimum concentration out of concentrated water node",
    )
    def minconccon(m, n, q, t):
        return m.v_C[n, q, t] >= m.p_Cmin[n, q]

    @model.Constraint(
        model.s_NTIN, model.s_T, doc="Minimum inlet flow required at treatment site"
    )
    def minflowcon(m, n, t):
        return sum(m.v_F[a, t] for a in m.s_Ain[n]) >= m.p_Fmin[n]

    return model
