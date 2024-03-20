import yaml
import re

def EX_Compare(ruleID="-1", dvSim=None, DictLimit=None):
	#High Level outline: Perform calculation for limit and
	#evaluate that limit
    arg1 = dvSim[0]
    arg2 = dvSim[1]

    limitResult = "pass"
    for k, v in DictLimit.items():
        match v[-1:]:
            case '%': #Percent difference case
                v = v[:-1]
                v = float(v) / 100.0
                arg1 = float(arg1)
                arg2 = float(arg2)
                denom = abs(abs(arg1) + abs(arg2))
                if denom != 0:
                    result = (2 * abs(arg1 - arg2) / abs(abs(arg1) + abs(arg2)))
                else:
                    result = 0
				#result = 2 * (arg1 - arg2) / (arg1 + arg2)
            case 'X': #Multiplier Case
                v = v[:-1]
                v = float(v)
                arg1 = float(arg1)
                arg2 = float(arg2)
                if arg2 != 0:
                    result = arg1 / arg2
                else: 
                    #Give Infinity to alert user. May be undesirable behavior
                    result = float('inf')
            case _: #Absolute difference case
                result = abs(arg1 - arg2)	
        if result > float(v):
            if str(k).isalpha() == True:
                if "fail" in k:
                    limitResult = k
                    break
                else:
                    limitResult = EX_Eval_Limits(limitResult, k)
            else:
                limitResult = EX_Eval_Limits(limitResult, k)
    return  {"Compare": result,"limit": limitResult}

def EX_Check(ruleID="-1", dvSim=None, DictLimit=None):
    for limit, value in DictLimit.items():
        if "min" in limit:
            minimum = value
        else:
            maximum = value
    limitResult = "fail"
    if dvSim > minimum and dvSim < maximum:
        limitResult = "pass"
    return  {"check": dvSim, "limit": limitResult}

def EX_Corner_Compare(ruleID="-1", ListPar=[], DictLimit=None):
    return  {"Corner_Comp":{},"string":["Korner Stuff","Otherstuff 3"],"limit":{}}

def EX_Get_Sim_Val(dsoDict, simName, corner="top_tt"):
    simulation = dsoDict.get(simName)
    simData = simulation.get("simulations")
    value = simData.get(corner)
    result = value.get("nominal")
    return result

def EX_Eval_Limits(oldLimit, newLimit):
    if str(oldLimit).isalpha() == True:
        if str(newLimit).isalpha() == True:    
            if "fail" in oldLimit or "fail" in "newLimit":
                return "fail"
            elif "warning" in oldLimit or "warning" in newLimit:
                return "warning"
            else:
                return "note"
        else:
            if "fail" not in oldLimit:
                newLimitNum = float(newLimit)
                if newLimitNum > 0:
                    return newLimit
                elif "warning" in oldLimit:
                    return oldLimit
                elif newLimitNum == 0:
                    return newLimit
                elif "pass" in oldLimit:
                    return newLimit
                else: 
                    return oldLimit
    else:
        if str(newLimit).isalpha() == True:
            if "fail" not in newLimit:
                oldLimitNum = float(oldLimit)
                if oldLimitNum > 0:
                    return oldLimit
                elif "warning" in newLimit:
                    return oldLimit
                elif oldLimitNum == 0:
                    return oldLimit
                else: 
                    return newLimit
        else:
            if float(oldLimit) > float(newLimit):
                return oldLimit
            else:
                return newLimit

def Dictionary_Read(path):
    #read in a yaml file as a dict
    with open(("./"+path),'r') as f:
        d = yaml.safe_load(f.read())
    return d

def Dictionary_Dump(path, DictUsed):
    with open(path,'w') as out:
	    yaml.dump(DictUsed, out, explicit_start=True)
    return

"""
DSIv1_File  = 0
DSIv2_File  = 1
TF_File     = 2
DSO_File    = 3
RF_File     = 4
UKY_Offset  = 5



PathARR = ["ifxdevsim/example/techfile/mdrc.dsi.yml", # ------------------\
            "ifxdevsim/example/techfile/mxs8.dsi.yml",
            "ifxdevsim/example/techfile/mxs8.tf.yml",
            "ifxdevsim/example/techfile/mxs9.dso.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml",# Real Files ------/
            "TestCasesForExec/test.dsrf.yml",# UKY Test files ------------\
            "TestCasesForExec/mxs9.dso.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml",
            "TestCasesForExec/test2.dsrf.yml",
            "Test_Files/test.dso.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml"]#------------------/

#dicRule = Dictionary_Read(PathARR[RF_File])
dicRule = Dictionary_Read(PathARR[8]) #Uses mxs9.dso in TestCasesforExec
#dicDso  = Dictionary_Read(PathARR[DSO_File]) 
dicDso  = Dictionary_Read(PathARR[9]) #Uses hard coded dsrf file in Test Cases folder
dicDsi  = Dictionary_Read(PathARR[DSIv2_File])

CurrRuleDic = {}

mdrcExout = {}

CorruptedRules=[]
"""
"""
for DV in dicDso.keys():
    (mdrcExout[DV]) = {}
    (mdrcExout[DV]["device"]) = dicDso[DV].get("device")
    (mdrcExout[DV]["metrics"]) = dicDso[DV].get("metrics")
    (mdrcExout[DV]["mdrc"]) = {}
    
    
    #print(f"Start rules for {DV}")
    for i in dicRule.get('rules'):
        test = i.get('rule')
        ruleNum = i.get('rule number')
        if( [test, ruleNum] in CorruptedRules):
            continue

        #print(f"Runing rule:{ruleNum} for {DV}")
		#Routine for grabbing data based on rule type
         if test == "compare":
            deviceSims = []
            for device in i.get("device simulations"):
               deviceSims.append(EX_Get_Sim_Val(dicDso, device)) 
            CurrRuleDic = EX_Compare(ruleID=i.get('rule number'), dvSim= deviceSims, DictLimit= i.get('limit'))
        elif test == "check":
            device = EX_Get_Sim_Val(dicDso, i.get("device simulations"))
            CurrRuleDic = EX_Check(ruleID="Check", dvSim=device, DictLimit=i.get('limit'))
        elif test == "corner_compare":
            CurrRuleDic = EX_Corner_Compare(ruleID="Corner")
        else:
            print(f"     Rule:{i.get('rule')} Not Found check rule file for corrupted Rule:{i.get('rule number')}")
            CorruptedRules.append([test,ruleNum])
        
        (mdrcExout[DV]["mdrc"][ruleNum]) = (CurrRuleDic)

    if (len(CorruptedRules) != 0):
        print(f'\n\nThe following rules were not found:')
        for name, id in CorruptedRules:
            print(f'rule: {name}, rule number: {id}')
        print(f'Please Review your Rule File')
    Dictionary_Dump("Test.yml", mdrcExout)
"""
def ExecDSRF():
    #Traverse Rules instead of devices in DSO file
    for i in dicRule.get('rules'):
        test = i.get('rule')
        ruleNum = i.get('rule number')

        #Routine for grabbing data based on rule type
        if test == "compare":
            deviceSims = []
            for device in i.get("device simulations"):
               deviceSims.append(EX_Get_Sim_Val(dicDso, device)) 
            CurrRuleDic = EX_Compare(ruleID=i.get('rule number'), dvSim= deviceSims, DictLimit= i.get('limit'))
        elif test == "check":
            device = EX_Get_Sim_Val(dicDso, i.get("device simulations"))
            CurrRuleDic = EX_Check(ruleID="Check", dvSim=device, DictLimit=i.get('limit'))
        elif test == "corner_compare":
            CurrRuleDic = EX_Corner_Compare(ruleID="Corner")
        (mdrcExout[ruleNum]) = (CurrRuleDic)
        mdrcExout[ruleNum]["string"] = i.get("string")

    Dictionary_Dump("Test.yml", mdrcExout)
if __name__ == '__main__':
    PathARR = ["ifxdevsim/example/techfile/mdrc.dsi.yml", # ------------------\
                "ifxdevsim/example/techfile/mxs8.dsi.yml",
                "ifxdevsim/example/techfile/mxs8.tf.yml",
                "ifxdevsim/example/techfile/mxs9.dso.yml",
                "ifxdevsim/example/techfile/test.dsrf.yml",# Real Files ------/
                "TestCasesForExec/test.dsrf.yml",# UKY Test files ------------\
                "TestCasesForExec/mxs9.dso.yml",
                "ifxdevsim/example/techfile/test.dsrf.yml",
                "TestCasesForExec/test2.dsrf.yml",
                "Test_Files/test.dso.yml",
                "ifxdevsim/example/techfile/test.dsrf.yml",
                "ifxdevsim/example/techfile/test.dsrf.yml"]#------------------/

    #dicRule = Dictionary_Read(PathARR[RF_File])
    dicRule = Dictionary_Read(PathARR[8]) #Uses hard coded dsrf file in Test Cases folder
    #dicDso  = Dictionary_Read(PathARR[DSO_File]) 
    dicDso  = Dictionary_Read(PathARR[9])
    #dicDsi  = Dictionary_Read(PathARR[DSIv2_File])

    CurrRuleDic = {}

    mdrcExout = {}

    CorruptedRules=[]

    ExecDSRF()
