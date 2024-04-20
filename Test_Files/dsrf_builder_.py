def build_dsrf_rule(param_object,rule_number):
    #call in main to test
    new_rule = {}
    #case for compare rule
    if 'compare' in param_object['mdrc'][rule_number]:
    	new_rule['rule'] = 'compare'
    	new_rule['rule number'] = rule_number
    	new_rule['device simulations'] = []
    	new_rule['device simulations'].append(param_object['measure name'])
    	new_rule['device simulations'].append(param_object['measure name'] + "_" + param_object['mdrc'][rule_number]['compare']['control']['simulator'])
    	new_rule['string'] = param_object['mdrc'][rule_number]['string']
    	new_rule['limit'] = param_object['mdrc'][rule_number]['limit']
    	return new_rule	
    #case for limit check rule
    if 'check' in param_object['mdrc'][rule_number]:
    	#only write check instruction if check rule checks for metric simulated by this param object
        if param_object['mdrc'][rule_number]['check']['metrics'] == param_object['metrics']:
    	    new_rule['rule'] = 'check'
    	    new_rule['rule number'] = rule_number
    	    new_rule['device simulations'] = []
    	    new_rule['device simulations'].append(param_object['measure name'])
    	    new_rule['string'] = param_object['mdrc'][rule_number]['string']
    	    new_rule['limit'] = param_object['mdrc'][rule_number]['limit']
    	    return new_rule
