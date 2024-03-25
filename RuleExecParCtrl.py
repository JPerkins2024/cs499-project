import yaml
import re

class ControllerA:
    def __init__(self, param):
        self.params = [param]
        self.instance_map = {}
        self.meas_names = [param.measure_name]
        #self.control = deepcopy(param.param_data["control"])
        #self.language = self.control.get("language")
        #self.model_language = self.control.get("model language", False) or self.language
        #self.corners = self.get_corners()
        #self.agemode = self.check_agemode()

class ParameterA():
    def __init__(self, conf=None, techdata=None, param_h=None, param=None):
        if param is not None:
            self.name = re.sub(".*?__", "", param, count=1)

        self.config = None
        self.techdata = techdata

        if param_h is not None:
            self.device = param_h.get("device")
            self.measure_name = param_h["measure name"].lower()
            self.param_data = None#self.tech_compile(param_h)
        #self.set_required_defaults()
       # self.param_data = self.calculator(self.param_data)

        self.type = "dc"
        self.unit = None
        #self.netlistStr = self.netlist(1)

class DsiA:  # The original DSI was a hash. The name "hash" in this context serves only as a reminder that I need to make it a hash
    def __init__(self, conf, techdata, debug=False):
        self.ymlFiles = []
        self.conf = conf
        self.Params = []
        self.Data = dict()
        self.techdata = techdata
        self.debug = debug

def EX_Compare(ruleID="-1", Param1=None, Param2=None, DictLimit=None):
    return  {"compare": {},"string":["Compare Stuff","Otherstuff 1"],"limit":{}}

def EX_Check(ruleID="-1", Param1=None, DictLimit=None,DicMetric=None):
    return  {"check":{},"string":["Check Stuff","Otherstuff 2"],"limit":{}}

def EX_Corner_Compare(ruleID="-1", ListPar=[], DictLimit=None):
    return  {"corner_compare":{},"string":["Korner Stuff","Otherstuff 3"],"limit":{}}

def Dictionary_Read(path):
    #read in a yaml file as a dict
    with open(("./"+path),'r') as f:
        d = yaml.safe_load(f.read())
    return d

def Dictionary_Dump(path, DictUsed):
    with open(path,'w') as out:
        yaml.dump(DictUsed, out)
    return

DSIv1_File  = 0
DSIv2_File  = 1
TF_File     = 2
DSO_File    = 3
RF_File     = 4
UKY_Offset  = 5

'''

PathARR = ["ifxdevsim/example/techfile/mdrc.dsi.yml", # ------------------\
            "ifxdevsim/example/techfile/mxs8.dsi.yml",
            "ifxdevsim/example/techfile/mxs8.tf.yml",
            "ifxdevsim/example/techfile/mxs9.dso.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml",# Real Files ------/
            "TestCasesForExec/test.dsrf.yml",# UKY Test files ------------\
            "TestCasesForExec/mxs9.dso.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml"]#------------------/

#dicRule = Dictionary_Read(PathARR[RF_File])
dicRule = Dictionary_Read(PathARR[UKY_Offset])
#dicDso  = Dictionary_Read(PathARR[DSO_File])
dicDso  = Dictionary_Read(PathARR[UKY_Offset+1])
dicDsi  = Dictionary_Read(PathARR[DSIv2_File])

CurrRuleDic = {}

mdrcExout = {}

CorruptedRules=[]

for DV in dicDso.keys():
    (mdrcExout[DV]) = {}
    (mdrcExout[DV]["device"]) = dicDso[DV].get("device")
    (mdrcExout[DV]["metrics"]) = dicDso[DV].get("metrics")
    (mdrcExout[DV]["instance parameters"]) = dicDso[DV].get("instance parameters")
    (mdrcExout[DV]["mdrc"]) = {}
    
    
    print(f"Start rules for {DV}")
    for i in dicRule.get('rules'):
        if( [i.get('rule'),i.get('rule number')] in CorruptedRules):
            continue # Rule was found corrupted previously

        print(f"Runing rule:{i.get('rule number')} for {DV}")
        test = i.get('rule')
        if test == "compare":
            CurrRuleDic = EX_Compare(ruleID="Compare")
        elif test == "check":
            CurrRuleDic = EX_Check(ruleID="Check")
        elif test == "corner_compare":
            CurrRuleDic = EX_Corner_Compare(ruleID="Corner")
        else:
            print(f"     Rule:{i.get('rule')} Not Found check rule file for corrupted Rule:{i.get('rule number')}")
            CorruptedRules.append([i.get('rule'),i.get('rule number')])
            continue #skip to next since it is a corrupted rule
        
        (mdrcExout[DV]["mdrc"][i.get('rule number')]) = (CurrRuleDic)

if (len(CorruptedRules) != 0):
    print(f'\n\nThe following rules were not found:')
    for name, id in CorruptedRules:
        print(f'rule: {name}, rule number: {id}')
    print(f'Please Review your Rule File')
        

Dictionary_Dump("Test.yaml", mdrcExout)
'''



DvNames = ["nhv__1","nhv__titan__1","nhv__spectre__1","nv__2","nv__titan__2","nv__3"]
def GenDummyContent(arr):
    Dic = {}
    for key in arr:
        Dic[key] = {"techdata":{"DATA1"}, "dsi":{"DsiData":"DTa", "device":"str","measure name":"tester"}  }
    return Dic


def testing1():
    jobs = []
    config = None
    toes = GenDummyContent(DvNames)
    for keys in toes.keys():
        if not toes[keys]:
            continue
        param = ParameterA(config, toes[keys]["techdata"], toes[keys]["dsi"], keys)

        jobs.append(ControllerA(param))

    for j in jobs:
        print("new job")
        for p in j.params:
            print(f"Job items {p.name}")

testing1()