import yaml
import re
class MDRC:
    def __init__(self):
        pass
                 
    def EX_Compare(self, ruleID="-1", RuleMetric="", dvSim=None, DictLimit=None):
        #High Level outline: Perform calculation for limit and
        #evaluate that limit
        arg1 = dvSim[0].param_data["definitions"][RuleMetric]
        arg2 = dvSim[1].param_data["definitions"][RuleMetric]
        Info = {"Parameter 1":dvSim[0].name,"Parameter 2":dvSim[1].name}
        Info["Metric"] = RuleMetric
        limitResult = "pass"
        for k, v in DictLimit.items():
            #print(f"k:{k}\nv:{v}")
            if (v[-1:] == '%'): 
                #Percent difference case
                v = v[:-1]
                v = float(v) / 100.0
                arg1 = float(arg1)
                arg2 = float(arg2)
                denom = abs(abs(arg1) + abs(arg2))
                if denom != 0:
                    result = (2 * abs(arg1 - arg2) / abs(abs(arg1) + abs(arg2)))
                else:
                    result = 0

                Info["Type"] = "Percentage"
                #result = 2 * (arg1 - arg2) / (arg1 + arg2)
            elif( v[-1:] =='X' ): 
                #Multiplier Case
                v = v[:-1]
                v = float(v)
                arg1 = float(arg1)
                arg2 = float(arg2)
                if arg2 != 0:
                    result = arg1 / arg2
                else: 
                    #Give Infinity to alert user. May be undesirable behavior
                    result = float('inf')

                Info["Type"] = "Multiplier"
            else: 
                #Absolute difference case
                result = abs(arg1 - arg2)
                
                Info["Type"] = "AbsoluteDifferance"


            if result > float(v):
                if str(k).isalpha() == True:
                    if "fail" in k:
                        limitResult = k
                        break
                    else:
                        limitResult = self.EX_Eval_Limits(limitResult, k)
                else:
                    limitResult = self.EX_Eval_Limits(limitResult, k)
        return  {"Compare": ruleID, "Comparison":result,"limit": limitResult, "info":Info}

    def EX_Check(self, ruleID="-1", RuleMetric="", dvSim=None, DictLimit=None):
        Param = dvSim[0].param_data["definitions"][RuleMetric]
        
        Info = {"Parameter 1":dvSim[0].name}
        Info["Metric"] = RuleMetric
        for limit, value in DictLimit.items():
            if "min" in limit:
                minimum = value
            else:
                maximum = value
        limitResult = "fail"
        if Param > minimum and Param < maximum:
            limitResult = "pass"
        return  {"Compare": ruleID, "Comparison":Param,"limit": limitResult, "info":Info}
    
    def EX_Corner_Compare(self, ruleID="-1", ListPar=[], DictLimit=None):
        return  {"corner_compare":{},"string":["Korner Stuff","Otherstuff 3"],"limit":{}}

    def EX_Get_Sim_Val(self, dsoDict, simName, corner="top_tt"):
        simulation = dsoDict.get(simName)
        simData = simulation.get("simulations")
        value = simData.get(corner)
        result = value.get("nominal")
        return result

    def EX_Eval_Limits(self, oldLimit, newLimit):
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
    