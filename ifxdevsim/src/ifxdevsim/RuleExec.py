import sys
import yaml
import re
class MDRC:
    def __init__(self):
        pass
    # The Info object that is created for each of the rules 
    # was created to help debug the rule if something whent wrong during the process
    # if you would like to remove this additional informetion there should be no reprecussion 
    # aslong as the reportgeneration.py file is also not included
    
    # EX_Compare, EX_Check, EX_Corner_Compare parameters
    #rule ID : (str) the rule number/name the user has requested
    #ruleMetric : (str) the metric that we want to compare
    #dvSim: (List)(ParameterObjects) A list of objects that we will attempt to compare
    #dictLimit: (dict)<str,float> it contains a limit as the key and a range to test as it's value
    
    # EX_Compare, EX_Check, EX_Corner_Compare Output
    #Rule: (dict)<str,float> it contains a list of keys with rule execution information
    def EX_Compare(self, ruleID="-1", ruleMetric="", dvSim=None, dictLimit=None):
        Info = {"Parameter 1":dvSim[0].name,"Parameter 2":dvSim[1].name}
        Info["Metric"] = ruleMetric

        #locate the metric within the parameter
        args = self.Locate_Metric(params=dvSim, metric=ruleMetric)
        
        
        if (2 != len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 2 parameters requested {len(dvSim)} provided", "info":Info}
        if (args == None) or (len(args) !=  len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 2 parameter metrics expected, found {len(args) if args != None else  0} total", "info":Info}
        
        if (not isinstance(args[0], dict)):
            for i in range(len(args)):
                args[i] = {i:args[i]}

        limitPriority = "pass"
        for ComparisonKey in args[0].keys():
            try:
                metricArgs=[]
                metricArgs.append(args[0][ComparisonKey])
                metricArgs.append(args[1][ComparisonKey])
            except:
                return {"ID":ruleID,"ERROR":f"Comparison error: aples to oranges, parameters {dvSim[1].name} and {dvSim[0].name} dont share values", "info":Info}
            
            for arg in metricArgs:
                if (not isinstance(arg, float)):
                    return {"ID":ruleID,"ERROR":f"Comparison error: float metric expected, found {type(arg)}", "info":Info}
            
            arg1 = metricArgs[0]
            arg2 = metricArgs[1]

            #Evaluate Limits
            for limitName, limitValType in dictLimit.items():
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

    # EX_Compare_Calc_Types input
    # limitValType : (str) this comparison can be one of 3 types, handled within the function
    # arg1 : (float) float value to compare
    # arg2 : (float) flaot value to comompare
    # output
    # limitValType : (str) comparison type character
    # result : (float) comparison responce
    # calcType : (str) word form comparison type
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

    #see coment on EX_Compare
    def EX_Check(self, ruleID="-1", ruleMetric="", dvSim=None, dictLimit=None):
        Info = {"Parameter 1":dvSim[0].name}
        Info["Metric"] = ruleMetric
        args = self.Locate_Metric(params=dvSim, metric=ruleMetric)

        if (1 != len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 1 parameter requested {len(dvSim)} provided", "info":Info}
        if (args == None) or (len(args) !=  len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 1 parameter metric expected, found {len(args) if args != None else  0} total", "info":Info}
        
        if (not isinstance(args[0], dict)):
            for i in range(len(args)):
                args[i] = {i:args[i]}

        limitResult = "fail"
        for ComparisonKey in args[0].keys():
            metricArgs=[]
            metricArgs.append(args[0][ComparisonKey])

            for arg in metricArgs:
                if (not isinstance(arg, float)):
                    return {"ID":ruleID,"ERROR":f"Comparison error: float metric expected, found {type(arg)}", "info":Info}
            
            arg1 = metricArgs[0]

            for limit, value in dictLimit.items():
                if "min" in limit:
                    minimum = value
                else:
                    maximum = value
            if arg1 > minimum and arg1 < maximum:
                limitResult = "pass"
        return  {"RuleType":"Check", "ID":ruleID, "Comparison":arg1,"limit": limitResult, "info":Info}
    
    #in addition to the comment on EX_compare
    # this rule has the capability of checking a list of corners within a parameter
    # or across multiple parameters, this is a simple distance comparison depending on the Metric type
    def EX_Corner_Compare(self, ruleID="-1", dvSim=None, dictLimit=None, ruleMetric=""):

        args = self.Locate_Metric(params=dvSim, metric=ruleMetric)
        Info = {}
        for i in range(len(dvSim)):
            Info[f"Parameter {i}"] = dvSim[i].name
        
        if (args == None) or (len(args) !=  len(dvSim)):
            return {"ID":ruleID,"ERROR":f"Comparison error: 2 parameter metrics expected, found {len(args) if args != None else  0} total", "info":Info}
        
        for arg in args:
            if (not isinstance(arg,dict)):
                return {"ID":ruleID,"ERROR":f"Comparison error: dict metric expected, found {type(arg)}", "info":Info}
        
        # the following is the format the corners need to be to be accepted within this compare rule:
        '''
           param corner data (args[x]) = {
            "top_tt": 47.5,
            "top_ff": 39.86000000000001,
            "top_ss": 57.49
            }
        '''

        #dvSim = {"cornerName1": "cornerVal1", "cornerName2": "cornerVal2"}
        cornerListA = list(args[0].items())
        Info["Corners"] = {dvSim[0].name:cornerListA}
        cornerListLengthA = len(cornerListA)
        
        #handle multiple device corners
        if len(dvSim) == 2:
            cornerListB = list(args[1].items())
            cornerListLengthB = len(cornerListB)
            Info["Corners"] = {dvSim[1].name:cornerListB}

            if len(cornerListA) != len(cornerListB):
                return {"ID":ruleID,"ERROR":f"Comparison error: corners in parameter metrics do not match, found corners in param A: {len(cornerListA)}  corners in param B: {len(cornerListB)}", "info":Info}
        
        else:
            cornerListB = list(args[0].items())
            cornerListLengthB = cornerListLengthA
            
        corners = ["",""]
        maxResult = float('-inf')
        
        #Evaluate limits and perform calculations
        limitResult = "pass"
        for i in range(0, cornerListLengthA):
            arg1 = cornerListA[i][1]
            for j in range(0, cornerListLengthB):
                arg2 = cornerListB[j][1]
                #Iterate through all corners given

                for limitName, limitValType in dictLimit.items():
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
        
    #Locate Metric inputs
    # params: (list)(parameter objects) a list of the parameters that we need to find a metric value from
    # metric: (str) the name of the metric that we are looking for   
    def Locate_Metric(self, params=[], metric=""):
        if (metric=="" or (not metric.isalpha())):
            raise KeyError(f"Metric '{metric}' format error")
        # if the metric serched matches the metric value in the parameter:
        #   we return the corners to compare
        if metric == params[0].param_data["metrics"]: 
            CornerValues = []
            for parameter in params:
                temp = {}
                for CornerLabel in parameter.param_data["simulations"].keys():
                    temp[CornerLabel] =  parameter.param_data["simulations"][CornerLabel]["nominal"] 

                CornerValues.append(temp)
            # this is a dictionary
            return CornerValues.copy()
        elif metric not in params[0].param_data.keys():
            #if the metric is not found in one of the top level keys, 
            #  we look within the available dictionaries to find the correct key
            for section in params[0].param_data.keys():
                if( type(params[0].param_data[section]) == dict):
                    for posibleMetric in params[0].param_data[section].keys():
                        if metric == posibleMetric:
                            temp = []
                            for param in params:
                                temp.append(param.param_data[section][posibleMetric])
                            return temp
        return None

    # this function converts a the corner dictionary within "imulations" to a list of floats
    def DictToFloat(self, dictArr=[]):
        temp = []
        for param in dictArr:
            temp2 = []
            for key in param.keys():
                temp2.append(param[key])
            temp.append(temp2.copy())
        for arrayIdx in range(len(temp)):
            if len(temp[arrayIdx]) == 1:
                temp[arrayIdx] = temp[arrayIdx][0]
        
        return temp.copy()