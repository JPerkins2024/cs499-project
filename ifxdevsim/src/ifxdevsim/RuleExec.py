import sys
import yaml
import re
class MDRC:
    def __init__(self):
        pass
    def EX_Compare(self, ruleID="-1", RuleMetric="", dvSim=None, DictLimit=None):
        arg1 = dvSim[0].param_data["definitions"][RuleMetric]
        arg2 = dvSim[1].param_data["definitions"][RuleMetric]
        Info = {"Parameter 1":dvSim[0].name,"Parameter 2":dvSim[1].name}
        Info["Metric"] = RuleMetric

        #Evaluate Limits
        limitPriority = "pass"
        for limitName, limitValType in DictLimit.items():
            limitVal, compareResult, calcType = EX_Compare_Calc_Types(limitValType, arg1, arg2)
            Info["Type"] = calcType
            if compareResult > float(limitVal):
                if str(limitName).isalpha() == True:
                    if "fail" in limitName:
                        limitPriority = limitName
                        break
                    else:
                        limitPriority = EX_Eval_Limits(limitPriority, limitName)
                else:
                    limitPriority = EX_Eval_Limits(limitPriority, limitName)
        return  {"Compare": ruleID, "Comparison":compareResult,"limit": limitPriority, "info":Info}

    def EX_Compare_Calc_Types(limitValType, arg1, arg2):
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
    def EX_Corner_Compare(ruleID="-1", dvSim=None, DictLimit=None):
        #dvSim on my end takes in parameters in the following form
        #dvSim = {cornerName1: cornerVal1, cornerName2: cornerVal2}
        cornerList = list(dvSim.items())
        cornerListLength = len(cornerList)
        corners = ["",""]
        maxResult = float('-inf')

        
        #Evaluate limits and perform calculations
        limitResult = "pass"
        for i in range(0, cornerListLength):
            arg1 = cornerList[i][1]
            for j in range(0, cornerListLength):
                arg2 = cornerList[j][1]
                #Iterate through all corners given

                for limitName, limitValType in DictLimit.items():
                    limitVal, compareResult, calcType = EX_Compare_Calc_Types(limitValType, arg1, arg2)
                    if compareResult > float(limitVal):
                            maxResult = max(maxResult, compareResult)
                            if compareResult == maxResult:
                                corners = [cornerList[i][0], cornerList[j][0]]
                            if str(limitName).isalpha() == True:
                                if "fail" in limitName:
                                    limitResult = limitName
                                    break
                                else:
                                    limitResult = EX_Eval_Limits(limitResult, limitName)
                            else:
                                limitResult = EX_Eval_Limits(limitResult, limitName)
        return  {Corner_Compare": ruleID, Corner_Comparison": maxResult,"Corners": corners, "limit": limitResult}

    def EX_Eval_Limits(oldLimit, newLimit):
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
                return EX_Eval_Limits_Mixed_Types(newLimit, oldLimit)
        else:
            if str(newLimit).isalpha() == True:
                return EX_Eval_Limits_Mixed_Types(oldLimit, newLimit)
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

