import pytest
import dsrf_builder_
import yaml

print("hello world")

with open("uniquified_params.yml","r") as f:
	dsi_params = yaml.safe_load(f.read())
	
def test_check():
	assert dsrf_builder_.build_dsrf_rule(dsi_params['h1__nhv__0'],4) != None
	assert dsrf_builder_.build_dsrf_rule(dsi_params['h1__nhv__0'],4) == {
		'device simulations': ['h1__nhv__0'],
		'limit': {'max': 1000, 'min': 500},
		'rule': 'check',
		'rule number': 4,
		'string': {'s1': 'Verify a metric is within limits', 's2': 'IDSAT'}
	}
	assert dsrf_builder_.build_dsrf_rule(dsi_params['h1__nhv__1'],4) == None
	
def test_compare():
	assert dsrf_builder_.build_dsrf_rule(dsi_params['h1__nhv__0'],'2a') != None
	assert dsrf_builder_.build_dsrf_rule(dsi_params['h1__nhv__0'],'2b') != None
	assert dsrf_builder_.build_dsrf_rule(dsi_params['h1__nhv__1'],'2a') != None
	assert dsrf_builder_.build_dsrf_rule(dsi_params['h1__nhv__1'],'2b') != None
	assert dsrf_builder_.build_dsrf_rule(dsi_params['h1__nhv__0'],'2a') == {
		'device simulations': ['h1__nhv__0', 'h1__nhv__0_titan'],
		'limit': {'fail': '1%', 'note': '0.1%'},
		'rule': 'compare',
		'rule number': '2a',
		'string': {'s1': 'Simulator  checks', 's2': 'Titan'}
	}
	assert dsrf_builder_.build_dsrf_rule(dsi_params['h1__nhv__0'],'2b') == {
		'device simulations': ['h1__nhv__0', 'h1__nhv__0_hspice'],
		'limit': {'fail': '1%', 'note': '0.1%'},
		'rule': 'compare',
		'rule number': '2b',
		'string': {'s1': 'Simulator  checks', 's2': 'Hspice'}
	}
	
