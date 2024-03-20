import RuleExec as R
import pytest

#Compare Calculation Tests
def test_percent_diff_2pos_param():
   result = R.EX_Compare(dvSim=[4, 6], DictLimit={"fail": "-1%"}) 
   assert result["Compare"] == (2.0 / 5.0)
def test_percent_diff_neg_param():
   result = R.EX_Compare(dvSim=[-4, -6], DictLimit={"fail": "-1%"}) 
   assert result["Compare"] == (2.0 / 5.0)
   result = R.EX_Compare(dvSim=[-1, 0], DictLimit={"fail": "-1%"}) 
   assert result["Compare"] == 2.0
def test_percent_diff_divide_by_zero():
   result = R.EX_Compare(dvSim=[-4, 4], DictLimit={"fail": "-1%"}) 
   assert result["Compare"] == 2.0
def test_percent_diff_both_param_zero():
   result = R.EX_Compare(dvSim=[0, 0], DictLimit={"fail": "-1%"}) 
   assert result["Compare"] == 0.0
def test_multiplier_normal_case():
   result = R.EX_Compare(dvSim=[100, 10], DictLimit={"fail": "-1X"}) 
   assert result["Compare"] == 10.0
def test_multiplier_divide_by_zero():
   result = R.EX_Compare(dvSim=[100, 0], DictLimit={"fail": "-1X"}) 
   assert result["Compare"] == float('inf')
def test_absdif_normal_case():
   result = R.EX_Compare(dvSim=[100, -100], DictLimit={"fail": "-1"}) 
   assert result["Compare"] == 200.0
