import pyomo.environ as pyo
import idaes

import pytest


def lp():
    m = pyo.ConcreteModel()
    m.x = pyo.Var(initialize=3)
    m.y = pyo.Var(initialize=3)
    m.c1 = pyo.Constraint(expr=m.x >= 1)
    m.c2 = pyo.Constraint(expr=m.y >= 2)
    m.c3 = pyo.Constraint(expr=m.x <= 5)
    m.c4 = pyo.Constraint(expr=m.y <= 5)
    m.obj = pyo.Objective(expr=m.x + m.y)
    return m, 1


def milp():
    m = pyo.ConcreteModel()
    m.x = pyo.Var(domain=pyo.Integers, initialize=3)
    m.y = pyo.Var(domain=pyo.Integers, initialize=3)
    m.c1 = pyo.Constraint(expr=m.x >= 0.5)
    m.c2 = pyo.Constraint(expr=m.y >= 1.5)
    m.c3 = pyo.Constraint(expr=m.x <= 5)
    m.c4 = pyo.Constraint(expr=m.y <= 5)
    m.obj = pyo.Objective(expr=m.x + m.y)
    return m, 1


def nlp():
    m = pyo.ConcreteModel()
    m.x = pyo.Var(initialize=-0.1)
    m.y = pyo.Var(initialize=1)
    m.c = pyo.Constraint(expr=m.x >= 1)
    m.obj = pyo.Objective(expr=m.x**2 + m.y**2)
    return m, 1


def minlp():
    m = pyo.ConcreteModel()
    m.x = pyo.Var(initialize=-0.1)
    m.y = pyo.Var(initialize=1)
    m.i = pyo.Var(domain=pyo.Binary, initialize=1)
    m.c = pyo.Constraint(expr=m.x >= 1)
    m.obj = pyo.Objective(
        expr=m.i * (m.x**2 + m.y**2) + (1 - m.i) * 4 *(m.x**2 + m.y**2))
    return m, 1


MAP_SOLVER_PROBLEM = {
    'ipopt_sens': nlp,
    'bonmin': minlp,
    'couenne': minlp,
    'clp': lp,
    'cbc': milp
}


@pytest.fixture(
    scope='class',
    params=list(MAP_SOLVER_PROBLEM.keys())
)
def solver_name(request):
    return request.param


@pytest.fixture(
    scope='class',
)
def solver(solver_name):
    return pyo.SolverFactory(solver_name)


@pytest.fixture(
    scope='class'
)
def problem(solver_name):
    return MAP_SOLVER_PROBLEM[solver_name]


class TestSolver:
    def test_solver_available(self, solver):
        assert solver.available()
    
    def test_solver_has_solution(self, solver, problem):
        m, x = problem()
        solver.solve(m)
        assert pytest.approx(x) == pyo.value(m.x)
