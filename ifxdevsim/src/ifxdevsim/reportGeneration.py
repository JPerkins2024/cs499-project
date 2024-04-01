import time
import yaml

class ReportGenerator():
    
    def __init__(self):
        self.RulesExecuted = {}
        self.Stages_Completed = []
        

    def AddRule(self, device="", rule ={}):
        if ((device == "") or (rule == {})):
            print(f"Bad Format")
        else:
            if(device not in self.RulesExecuted.keys()):
                self.RulesExecuted[device] = [{"Time":time.time(), "Rule":rule}]
            else:
                self.RulesExecuted[device].append({"Time":time.time(), "Rule":rule})

    def AddStage(self, stage=""):
        if (stage == ""):
            print(f"Report error: '{stage}' is an Invalid stage")
        else:
            self.Stages_Completed.append(stage)

    def getDevicesUsed(self):
        return list(self.RulesExecuted.keys())

    def getNumberOfRulesExecuted(self):
        sum = 0

        for device in self.RulesExecuted.keys():
            sum = len(self.RulesExecuted[device]) + sum

        return sum
    
    def getFailRules(self):
        sum = []

        for device in self.RulesExecuted.keys():
            for rule in self.RulesExecuted[device]:
                #print(rule)
                if ("limit" in rule["Rule"].keys()):
                    if rule["Rule"]["limit"] == "fail":
                        sum.append(rule["Rule"])
                else:
                    print(f"invalid rule formmat")

        return sum
    
    def getWarningRules(self):
        sum = []

        for device in self.RulesExecuted.keys():
            for rule in self.RulesExecuted[device]:
                #print(rule)
                if ("limit" in rule["Rule"].keys()):
                    if rule["Rule"]["limit"] == "warning":
                        sum.append(rule["Rule"])
                else:
                    print(f"invalid rule formmat")

        return sum
    
    def getNoteRules(self):
        sum = []

        for device in self.RulesExecuted.keys():
            for rule in self.RulesExecuted[device]:
                #print(rule)
                if ("limit" in rule["Rule"].keys()):
                    if rule["Rule"]["limit"] == "note":
                        sum.append(rule["Rule"])
                else:
                    print(f"invalid rule formmat")

        return sum
    
    def getPassRules(self):
        sum = []

        for device in self.RulesExecuted.keys():
            for rule in self.RulesExecuted[device]:
                #print(rule)
                if ("limit" in rule["Rule"].keys()):
                    if rule["Rule"]["limit"] == "pass":
                        sum.append(rule["Rule"])
                else:
                    print(f"invalid rule formmat")

        return sum
    
    def getInvalidRules(self):
        sum = []

        for device in self.RulesExecuted.keys():
            for rule in self.RulesExecuted[device]:
                #print(rule)
                if ("limit" in rule["Rule"].keys()):
                    if (rule["Rule"]["limit"] not in (["pass", "fail","warning","note"])):
                        sum.append(rule["Rule"])
                else:
                    sum.append(rule["Rule"])

        return sum
    
    def printReport(self, title="mdrc.report.yaml"):
        if title == "":
            title = "mdrc.report.yaml"

        report = {}
        
        report["Devices_Tested"] = self.getDevicesUsed()
        report["StagesExecuted"] = self.Stages_Completed
        
        report["Rule_Distribution"] = {}
        report["Rule_Distribution"]["Pass"] = {"count":len(self.getPassRules()), "Rules":self.getPassRules()}
        report["Rule_Distribution"]["Note"] ={"count":len(self.getNoteRules()), "Rules":self.getNoteRules()}
        report["Rule_Distribution"]["Warning"] = {"count":len(self.getWarningRules()), "Rules":self.getWarningRules()}
        report["Rule_Distribution"]["Fail"] = {"count":len(self.getFailRules()), "Rules":self.getFailRules()}
        report["Rule_Distribution"]["Other"] = {"count":len(self.getInvalidRules()), "Rules":self.getInvalidRules()}
        print(report)
        with open(("./" + title),'w') as out:
            yaml.dump(report, out)