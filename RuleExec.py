
import yaml

'''
- rule: compare
  rule number: <e.g. 1b>
  parameter1: <parname1>
  parameter2: <parname2>
  string: [ <string at top of rule hierarchy> , <string at next level of rule hierarchy> ] 
  limit: 
    fail: 1%
'''
def EX_Compare(ruleID="-1", Param1=None, Param2=None, DictLimit=None):
    pass
'''
      check:
        metrics: idsat
      string: ['Verify a metric is within limits','IDSAT']
      limit:
        min: 500
        max: 1000
'''
def EX_Check(ruleID="-1", Param1=None, DicLimit=None,DicMetric=None):
    pass
def EX_Corner_Compare():
    pass


def RFtoList(DictionaryUsed):
    pass

def Dictionary_Read(path):
    #read in a yaml file as a dict
    with open(("./"+path),'r') as f:
        d = yaml.safe_load(f.read())
    return d

'''
dic = Dictionary_Read("test")
print(type(dic))
x = dic.get("example_dictionary")
print(x.get("key_2"))
'''

DSIv1_File  = 0
DSIv2_File  = 1
TF_File     = 2
DSO_File    = 3
RF_File     = 4



PathARR = ["ifxdevsim/example/techfile/mdrc.dsi.yml",
            "ifxdevsim/example/techfile/mxs8.dsi.yml",
            "ifxdevsim/example/techfile/mxs8.tf.yml",
            "ifxdevsim/example/techfile/mxs9.dso.yml",
            "ifxdevsim/example/techfile/test.dsrf.yml"]

dic = Dictionary_Read(PathARR[RF_File])
print(f" {PathARR[RF_File]}:\n{dic}")
print(f"Keys : {dic.keys()}" )


for i in dic.get('rules'):
    print(f"i : {i.keys()}")
    test = i.get('rule')
    '''
    #python is not being nice
    match test :
        case 'compare':
            print("This rule is compare")
        case 'check':
            print("This rule is check")
        case 'corner_compare':
            print("This rule corner-Compares")
        case _ :
            print("Rule Not Found check rule file for corrupted Rule")
    '''
    if test == "compare":
        print("This rule is compare")
        EX_Compare()
    elif test == "check":
        print("This rule is check")
        EX_Compare()
    elif test == "corner_compare":
        print("This rule is corner_compare")
        EX_Compare()
    else:
        print("Rule Not Found check rule file for corrupted Rule")
#print(f"Values: \n{x}")

'''  
#write examply by perki

#write a dictionary to a yaml file
new_dict = {
    "int_1": 12,
    "float_1": 12.3,
    "subdict_1": {
        "st": "hello",
        "in": 12
        },
    "li": [1,2,3,4,5]
    }

with open("example_out.yaml",'w') as out:
    yaml.dump(new_dict, out)
    
'''
