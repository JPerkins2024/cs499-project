import yaml

def EX_Compare(ruleID="-1", Param1=None, Param2=None, DictLimit=None):
    return  {"Compare":{},"string":["Compare Stuff","Otherstuff 1"],"limit":{}}

def EX_Check(ruleID="-1", Param1=None, DictLimit=None,DicMetric=None):
    return  {"check":{},"string":["Check Stuff","Otherstuff 2"],"limit":{}}

def EX_Corner_Compare(ruleID="-1", ListPar=[], DictLimit=None):
    return  {"Corner_Comp":{},"string":["Korner Stuff","Otherstuff 3"],"limit":{}}

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
    (mdrcExout[DV]["mdrc"]) = {}
    
    
    print(f"Start rules for {DV}")
    for i in dicRule.get('rules'):
        if( [i.get('rule'),i.get('rule number')] in CorruptedRules):
            continue

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
        
        (mdrcExout[DV]["mdrc"][i.get('rule number')]) = (CurrRuleDic)

    if (len(CorruptedRules) != 0):
        print(f'\n\nThe following rules were not found:')
        for name, id in CorruptedRules:
            print(f'rule: {name}, rule number: {id}')
        print(f'Please Review your Rule File')
            

Dictionary_Dump("Test.yaml", mdrcExout)