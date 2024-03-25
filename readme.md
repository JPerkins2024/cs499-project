# Welcome to the CS 499 Senior project Page
## Important changes:
changes to the application all happen within the dsi.py file, these changes include:
    - An addition to how parameter uniquification is made
    - A module that executes rules specified in the mdrc module of the tech file (as well as sends a report dictionary to the report generator)
    - A module that attaches the rule results on to the original DSI parameters
    - A module that creates a Report file that outputs what happend during the simulation of the software

## The change to the Parapeter Uniquification Process:
{change this to refflect how this happens and what is outputed}

## The addition of Rule Execution Module process:
This module is the interface that handles the rules obtained from the tech file. Rules can be added to specific devices
to compare metrics and check that the devices fall within specified thresholds. After the execution module has ran a report dictionary is created
for the report generator module to output informational output such that the user is able to analyse imediate metrics fast.

This module follows the following process:
1. Obtain Dsi Parameters from the Uniquification proces
2. Obtain a Rule file from the Data Extractor, (or obain the information from dsi.Data need to decide before pushing)
3. Read next posible instructions and handle edge-cases before sending information to the corresponding rule handler
4. Obtain nessesary information to execute the rule
    - Device: device that the rule applies to
    - Comparison device (optional): if the rule requires them for comparison, for example: the rule "compare"
5. after every rule execution, get a dictionary with the following parameters and attach them to a Repport dictionary. (some of the output comes from the executor module itself, others from the rules)
    - Rule: name of the rule executed
    - Device: device it was executed on
    - limit result: the tag atributed and stattus
    - notes: information related to the nodes ex: if the rule is compare, what persentage of the devices are the same (8%, 10%, etc.)
6. Attach output to the device parameter on the dsi
6. Repeat for all available rules
7. Send report to the next stage

This module currently incorpoorates the following rules:

### Compare Rule:
{Description}
{Process}
{Output}

### Check Rule:
{Description}
{Process}
{output}

### Corner-Compare Rule:
TBD... I think
{Description}
{Process}
{output}

## The newly added Report Generation Module process:
TBD...
{Description}
{Process}
{Output}
