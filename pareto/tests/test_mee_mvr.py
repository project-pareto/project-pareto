import pytest
import pyomo.environ as pyo
from pareto.models_extra.desalination_models.mee_mvr import make_mee_mvr_model
from idaes.core.util.model_statistics import degrees_of_freedom

ipopt_avail = pyo.SolverFactory("ipopt").available()

class TestMeeMvrModel():
    def test_dof(self):
        m = make_mee_mvr_model(N_evap = 1, inputs_variables=False)
        assert degrees_of_freedom(m) == 2
        
        m = make_mee_mvr_model(N_evap = 2, inputs_variables=False)
        assert degrees_of_freedom(m) == 3
        
        m = make_mee_mvr_model(N_evap = 3, inputs_variables=False)
        assert degrees_of_freedom(m) == 5
    
    @pytest.mark.skipif(not ipopt_avail, reason="ipopt is not available")
    def test_single_stage(self):
        m = make_mee_mvr_model(N_evap = 1, inputs_variables=False)
        m.flow_feed = 10 
        m.salt_feed = 70
        
        ipopt = pyo.SolverFactory('ipopt')
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        m.flow_feed = 10 
        m.salt_feed = 140
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        m.flow_feed = 20
        m.salt_feed = 140
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        m.flow_feed = 20
        m.salt_feed = 70
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
      
    @pytest.mark.skipif(not ipopt_avail, reason="ipopt is not available")
    def test_two_stage(self):
        m = make_mee_mvr_model(N_evap = 2, inputs_variables=False)
        m.flow_feed = 10
        m.salt_feed = 70
        
        ipopt = pyo.SolverFactory('ipopt')
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        m.flow_feed = 10 
        m.salt_feed = 140
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        m.flow_feed = 20
        m.salt_feed = 140
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        m.flow_feed = 20
        m.salt_feed = 70
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
    @pytest.mark.skipif(not ipopt_avail, reason="ipopt is not available")
    def test_three_stage(self):
        m = make_mee_mvr_model(N_evap = 3, inputs_variables=False)
        #This needs a higher compression ratio to find the optimum
        m.CR_max = 6
        
        m.flow_feed = 10
        m.salt_feed = 70
        
        ipopt = pyo.SolverFactory('ipopt')
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        m.flow_feed = 10 
        m.salt_feed = 140
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        m.flow_feed = 20
        m.salt_feed = 140
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        m.flow_feed = 20
        m.salt_feed = 70
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)
        
        
        
if __name__ == "__main__":
    pytest.main()