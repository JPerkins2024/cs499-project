import time
import yaml

class ReportGenerator():
    
    def __init__(self):
        self.RulesExecuted = {}
        self.StagesCompleted = []
        self.AvailableTypes = ["pass", "fail","warning","note"]
        

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
            self.StagesCompleted.append(stage)

    def getDevicesUsed(self):
        return list(self.RulesExecuted.keys())

    def getNumberOfRulesExecuted(self):
        sum = 0

        for device in self.RulesExecuted.keys():
            sum = len(self.RulesExecuted[device]) + sum

        return sum
    
    def getRulesType(self, Type=""):
        sum = []

        if (Type in self.AvailableTypes):
            for device in self.RulesExecuted.keys():
                for rule in self.RulesExecuted[device]:
                    #print(rule)
                    if ("limit" in rule["Rule"].keys()):
                        if rule["Rule"]["limit"] == Type:
                            sum.append(rule["Rule"])
                    else:
                        pass
        elif (Type == "Invalid"):
            for device in self.RulesExecuted.keys():
                for rule in self.RulesExecuted[device]:
                    #print(rule)
                    if ("limit" in rule["Rule"].keys()):
                        if (rule["Rule"]["limit"] not in (self.AvailableTypes)):
                            sum.append(rule["Rule"])
                    else:
                        sum.append(rule["Rule"])
        elif (Type == "ALL"):
            for device in self.RulesExecuted.keys():
               for rule in self.RulesExecuted[device]:
                    sum.append(rule["Rule"])
        else:
            print(f"{Type} Invalid Option, you can search for:")
            print("pass: All rules that passed")
            print("fail: All rules that failed")
            print("warning: All rules that recived a warning")
            print("note: All rules that recived a note")
            print("Invalid: All rules that have an invalid format (including errors)")
            print("ALL: All rules that were executed")

        return sum
        
    
    def printReport(self, title="mdrc.report.yaml"):
        if title == "":
            title = "mdrc.report.yaml"

        report = {}
        
        report["Devices_Tested"] = self.getDevicesUsed()
        report["StagesExecuted"] = self.StagesCompleted
        
        report["Rule_Distribution"] = {}
        hold = self.getRulesType(Type="pass")
        report["Rule_Distribution"]["Pass"] = {"count":len(hold), "Rules":hold}
        hold = self.getRulesType(Type="note")
        report["Rule_Distribution"]["Note"] ={"count":len(hold), "Rules":hold}
        hold = self.getRulesType(Type="warning")
        report["Rule_Distribution"]["Warning"] = {"count":len(hold), "Rules":hold}
        hold = self.getRulesType(Type="fail")
        report["Rule_Distribution"]["Fail"] = {"count":len(hold), "Rules":hold}
        hold = self.getRulesType(Type="Invalid")
        report["Rule_Distribution"]["Other"] = {"count":len(hold), "Rules":hold}
        #print(report)
        with open(("./" + title),'w') as out:
            yaml.dump(report, out)