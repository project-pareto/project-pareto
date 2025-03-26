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


def back_calculate_design(model, treatment_dict):
    for s in treatment_dict.keys():
        m = pyo.ConcreteModel()
        # Annualization factor
        m.ann_fac = pyo.Param(
            initialize=pyo.value(model.m_treatment[s, "T01"].annual_fac)
        )
        m.cepci_ratio = pyo.Param(initialize=model.m_treatment[s, "T01"].cepci_ratio)

        # Capex variables
        m.evap_capex = pyo.Var(model.m_treatment[s, "T01"].i)
        for i in model.m_treatment[s, "T01"].i:
            m.evap_capex[i].fix(pyo.value(model.global_evaporator_capex[s, i]))

        m.preheater_capex = pyo.Var(
            initialize=pyo.value(model.global_preheater_capex[s])
        )
        m.preheater_capex.fix()

        m.compressor_capex = pyo.Var(
            initialize=pyo.value(model.global_compressor_capex[s])
        )
        m.compressor_capex.fix()

        # Design variables
        m.evap_area = pyo.Var(
            model.m_treatment[s, "T01"].i, initialize=1, domain=pyo.PositiveReals
        )
        m.preheater_area = pyo.Var(initialize=1, domain=pyo.PositiveReals)
        m.compressor_capacity = pyo.Var(initialize=1, domain=pyo.PositiveReals)

        # Constraints
        def _evaporator_capex_con(m, i):
            fm = 1.8
            return m.evap_capex[i] == m.cepci_ratio * fm * 1.218 * pyo.exp(
                3.2362
                - 0.0126 * pyo.log(m.evap_area[i] * 10.764)
                + 0.0244 * (pyo.log(m.evap_area[i] * 10.764)) ** 2
            )

        m.evaporator_capex_con = pyo.Constraint(
            model.m_treatment[s, "T01"].i, rule=_evaporator_capex_con
        )

        def _preheater_capex_con(m):
            a = m.preheater_area * 10.764
            fd = pyo.exp(-0.9816 + 0.0830 * pyo.log(a))  # utube heat exchanger
            fp = 1  # pressure < 4 bar
            fm = 1  # carbon steel
            Cb = pyo.exp(8.821 - 0.308 * pyo.log(a) + 0.0681 * (pyo.log(a)) ** 2)
            return m.preheater_capex == m.cepci_ratio * 1.218 / 1000 * fd * fm * fp * Cb

        m.preheater_capex_con = pyo.Constraint(rule=_preheater_capex_con)

        def _compressor_capex_con(m):
            return m.compressor_capex == m.cepci_ratio * (
                7.9 * m.compressor_capacity**0.62
            )

        m.compressor_capex_con = pyo.Constraint(rule=_compressor_capex_con)

        ipopt = pyo.SolverFactory("ipopt")
        ipopt.solve(m)
        print("Desalination location - %s" % s)
        print("########################################################")
        print("Evaporator areas:")
        for i in model.m_treatment[s, "T01"].i:
            print(pyo.value(m.evap_area[i]))
        print("########################################################")
        print("Preheater area:", pyo.value(m.preheater_area))
        print("########################################################")
        print("Compressor capacity:", pyo.value(m.compressor_capacity))
