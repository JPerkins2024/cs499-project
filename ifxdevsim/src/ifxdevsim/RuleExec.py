import sys
import yaml
import re
class MDRC:
    def __init__(self):
        pass

    def EX_Compare(self, ruleID="-1", RuleMetric="", dvSim=None, DictLimit=None):
        Info = {"Parameter 1":dvSim[0].name,"Parameter 2":dvSim[1].name}
        Info["Metric"] = RuleMetric

        args = self.Locate_Metric(params=dvSim, metric=RuleMetric)

        if (2 != len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 2 parameters requested {len(dvSim)} provided", "info":Info}
        if (args == None) or (len(args) !=  len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 2 parameter metrics expected, found {len(args) if args != None else  0} total", "info":Info}
        
        for arg in args:
            if (type(arg) not in ["int","float","complex"]):
                return {"ID":ruleID,"ERROR":f"Comparison error: float metric expected, found {type(arg)}", "info":Info}
        
        arg1 = args[0]#dvSim[0].param_data["definitions"][RuleMetric]
        arg2 = args[1]#dvSim[1].param_data["definitions"][RuleMetric]

        #Evaluate Limits
        limitPriority = "pass"
        for limitName, limitValType in DictLimit.items():
            limitVal, compareResult, calcType = self.EX_Compare_Calc_Types(limitValType, arg1, arg2)
            Info["Type"] = calcType
            if compareResult > float(limitVal):
                if str(limitName).isalpha() == True:
                    if "fail" in limitName:
                        limitPriority = limitName
                        break
                    else:
                        limitPriority = self.EX_Eval_Limits(limitPriority, limitName)
                else:
                    limitPriority = self.EX_Eval_Limits(limitPriority, limitName)
        return  {"RuleType":"Compare","ID":ruleID, "Comparison":compareResult,"limit": limitPriority, "info":Info}

    def EX_Compare_Calc_Types(self, limitValType, arg1, arg2):
        calcTypeChar = limitValType[-1:]
        if calcTypeChar == '%': #Percent difference case
            limitValType = limitValType[:-1]
            limitValType = float(limitValType) / 100.0
            denom = abs(float(arg1)) + abs(float(arg2))
            if denom != 0:
                result = (2 * abs(arg1 - arg2)) / (abs(arg1) + abs(arg2))
            else:
                result = 0
            calcType = "Percentage"
        elif calcTypeChar == 'X': #Multiplier Case
            limitValType = limitValType[:-1]
            arg1 = float(arg1)
            arg2 = float(arg2)
            if arg2 != 0:
                result = arg1 / arg2
            else: 
                #Divide by Zero. Give Infinity to alert user. 
                result = float('inf')
            calcType = "Multiplier"
        else: #Absolute difference case
            result = abs(arg1 - arg2)	
            calcType = "AbsoluteDifferance"
        return limitValType, result, calcType

    def EX_Check(self, ruleID="-1", RuleMetric="", dvSim=None, DictLimit=None):
        Info = {"Parameter 1":dvSim[0].name}
        Info["Metric"] = RuleMetric
        args = self.Locate_Metric(params=dvSim, metric=RuleMetric)

        if (1 != len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 1 parameter requested {len(dvSim)} provided", "info":Info}
        if (args == None) or (len(args) !=  len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 1 parameter metric expected, found {len(args) if args != None else  0} total", "info":Info}
        
        for arg in args:
            if (type(arg) not in ["int","float","complex"]):
                return {"ID":ruleID,"ERROR":f"Comparison error: float metric expected, found {type(arg)}", "info":Info}
        
        arg1 = args[0]

        for limit, value in DictLimit.items():
            if "min" in limit:
                minimum = value
            else:
                maximum = value
        limitResult = "fail"
        if arg1 > minimum and arg1 < maximum:
            limitResult = "pass"
        return  {"RuleType":"Check", "ID":ruleID, "Comparison":arg1,"limit": limitResult, "info":Info}
    
    def EX_Corner_Compare(self, ruleID="-1", dvSim=None, DictLimit=None, RuleMetric=""):
        #dvSim on my end takes in parameters in the following form
        #dvSim = {cornerName1: cornerVal1, cornerName2: cornerVal2}

        args = self.Locate_Metric(params=dvSim, metric=RuleMetric)

        Info = {"Parameter 1":dvSim[0].name,"Parameter 2":dvSim[1].name}
        
        if (2 != len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 2 parameters requested {len(dvSim)} provided", "info":Info}
        if (args == None) or (len(args) !=  len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 2 parameter metrics expected, found {len(args) if args != None else  0} total", "info":Info}
        
        for arg in args:
            if (not isinstance(arg,dict)):
                return {"ID":ruleID,"ERROR":f"Comparison error: dict metric expected, found {type(arg)}", "info":Info}
        
        #dvSim = {"cornerName1": "cornerVal1", "cornerName2": "cornerVal2"}
        cornerListA = list(args[0].items())
        cornerListB = list(args[1].items())
        cornerListLengthA = len(cornerListA)
        cornerListLengthB = len(cornerListB)
        corners = ["",""]
        maxResult = float('-inf')
        #sys.exit(0)
        Info["Corners"] = {dvSim[0].name:cornerListA}
        Info["Corners"] = {dvSim[1].name:cornerListB}
        #Evaluate limits and perform calculations
        limitResult = "pass"
        for i in range(0, cornerListLengthA):
            arg1 = cornerListA[i][1]
            for j in range(0, cornerListLengthB):
                arg2 = cornerListB[j][1]
                #Iterate through all corners given

                for limitName, limitValType in DictLimit.items():
                    limitVal, compareResult, calcType = self.EX_Compare_Calc_Types(limitValType, arg1, arg2)
                    if compareResult > float(limitVal):
                            maxResult = max(maxResult, compareResult)
                            if compareResult == maxResult:
                                corners = [cornerListA[i][0], cornerListB[j][0]]
                            if str(limitName).isalpha() == True:
                                if "fail" in limitName:
                                    limitResult = limitName
                                    break
                                else:
                                    limitResult = self.EX_Eval_Limits(limitResult, limitName)
                            else:
                                limitResult = self.EX_Eval_Limits(limitResult, limitName)
        return  {"RuleType":"Corner_Compare", "ID":ruleID, "Comparison": maxResult,"Corners": corners, "limit": limitResult}

    def EX_Eval_Limits(self, oldLimit, newLimit):
        if str(oldLimit).isalpha() == True:
            oldLimit = oldLimit.lower()
            if str(newLimit).isalpha() == True:    
                newLimit = newLimit.lower()
                if ("fail" in oldLimit) or ("fail" in newLimit):
                    return "fail"
                elif "warning" in oldLimit or "warning" in newLimit:
                    return "warning"
                elif "note" in  oldLimit or "note" in newLimit:
                    return "note"
                else:
                    return "pass"
            else:
                return self.EX_Eval_Limits_Mixed_Types(newLimit, oldLimit)
        else:
            if str(newLimit).isalpha() == True:
                return self.EX_Eval_Limits_Mixed_Types(oldLimit, newLimit)
            else:
                if float(oldLimit) > float(newLimit):
                    return oldLimit
                else:
                    return newLimit
    def EX_Eval_Limits_Mixed_Types(floatLimit, stringLimit):
        stringLimit = stringLimit.lower()
        if "fail" not in stringLimit:
            floatLimitNum = float(floatLimit)
            if floatLimitNum > 0:
                return floatLimit
            elif "warning" in stringLimit:
                return stringLimit
            elif floatLimitNum == 0:
                return floatLimit
            elif "pass" in stringLimit:
                return floatLimit
            else: 
                return stringLimit
        else:
            return stringLimit
        
        
    def Locate_Metric(self, params=[], metric=""):
        if (metric=="" or (not metric.isalpha())):
            raise KeyError(f"Metric '{metric}' not found")

        if metric == params[0].param_data["metrics"]: 
            CornerValues = []
            #for parameter in params:
            #    CornerValues.append(parameter.param_data["simulations"])
            CornerValues = [
                {
                "top_tt": 47.5,
                "top_ff": 39.86000000000001,
                "top_ss": 57.49
                },
                {
                "top_tt": 57.42000000000001,
                "top_ff": 48.18000000000001,
                "top_ss": 69.5
                }
            ]
            return CornerValues#.copy()
        elif metric not in params[0].param_data.keys():
            for section in params[0].param_data.keys():
                if( type(params[0].param_data[section]) == dict):
                    for posibleMetric in params[0].param_data[section].keys():
                        if metric == posibleMetric:
                            temp = []
                            for param in params:
                                temp.append(param.param_data[section][posibleMetric])
                            return temp
        return None

