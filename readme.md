# Devsim MDRC Project for CS499

## Installing Devsim
Clone repository using the link found in GitHub

Navigate to the directory cs499-project

Use command `pip install -e ifxdevsim` to install the package.

## Usage
```
usage: dvsim [-h] [-i INPUT] [-s SAMPLE] [-ms MEAS_SCALE] [-w] [-r] [-uo] [-m MEAS] [-md MEAS_DRY] [-d]
             [-mf [MEAS_FROM]] [-mdsi [MEAS_DSI]] [-mkop [MEAS_KOP]] [-print-metric-routines]
             [-print-view-config CONFIG_TO_PRINT] [-print-valid-views] [-tf TECHFILE] [-pdf PDF] [-vo]

options:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
  -s SAMPLE, --sample SAMPLE
  -ms MEAS_SCALE, --meas_scale MEAS_SCALE
                        Scales measurement parameters by this factor.
  -w, --workspace
  -r, --report          Generate LaTex report with new or existing .yal layout file
  -uo, --uniq_only      Only uniquify parameters and write unique dsi.yml
  -m MEAS, --meas MEAS  toplevel meas directory. With -md option, writes replay file and quits. Without, goes directly
                        to dsi file. Currently only supports mdm files.
  -md MEAS_DRY, --meas_dry MEAS_DRY
                        write meas_input_list.replay and quit
  -d, --debug           Enable debug output/behavior
  -mf [MEAS_FROM], --meas_from [MEAS_FROM]
                        read meas_input_list.replay and generate dsi
  -mdsi [MEAS_DSI], --meas_dsi [MEAS_DSI]
                        Name of dsi file generated from measurements
  -mkop [MEAS_KOP], --meas_kop [MEAS_KOP]
                        Name of dsi kop file generated from measurements
  -print-metric-routines, --print-metric-routines
                        Print valid metric routines used for techfile configuration and exit
  -print-view-config CONFIG_TO_PRINT, --print-view-config CONFIG_TO_PRINT
                        Print viewconfig and exit. Use --print-valid-views for valid arguments
  -print-valid-views, --print-valid-views
                        Print valid viewtypes and exit
  -tf TECHFILE, --techfile TECHFILE
                        Name of techfile if not relying on autodiscovery. To force without using this, add the
                        relative path to the techfile into .techfile in the current directory.
  -pdf PDF, --combine-pdfs PDF
                        Combine generated pdfs into single file for easy viewing
  -vo, --views-only     Only create views from previously run simulations

```

# Welcome to the CS 499 Senior project Page
## Important changes:
changes to the application all happen within the dsi.py file, these changes include:
- An addition to how parameter uniquification is made
- A module that executes rules specified in the MDRC module of the tech file (as well as sends a report dictionary to the report generator)
- A module that attaches the rule results on to the original DSI parameters
- A module that creates a Report file that outputs what happened during the simulation of the software

## Optional MDRC section of DSI files
DSI (DevSim Input) files will now support a new set of options to allow for rule check configuration. Each Parameter in the DSI file an have a ‘mdrc’ section added to it. This section will contain a dictionary of rules. Each rule should contain the following information:
- The type of rule (Check,Compare,etc)
- Any control information (such as the simulator for a Simulator comparison rule)
- A set of strings to be used in the report generation stage
- A set of limit information for appropriate for the given rule (numeric range, min/max percent differences, etc)

## The change to Devsim’s Parameter Object creation:
After uniquified DSI data has been created inside of Devsim, another process happens to create modified object duplicates to allow for simulator comparison. Each uniquified parameter object (a device with a single metric to simulate) with simulator comparison rules in its ‘drc’ section will be duplicated once for each simulator comparison rule. Each duplicate will have its simulator changed to reflect the simulator of the desired comparison. The name of the parameter object will also be changed to reflect the duplication using the following format: 
```[original name]_[name of simulator]```

## DSRF file creation
A DSRF (DevSim Rule File) file will be created containing the instructions for the execution stage of the software. Each uniquified parameter object will have instructions written into this file for any applicable rules in its ‘drc’ section. Each instruction in the DSRF file will contain
- The rule to execute
- The rule number as specified in the DSI file
- The parameter object(s) to perform the evaluation on
- Limit information for the rule
- Any strings to be passed to the report generator

## The addition of Rule Execution Module process:
This module is the interface that handles the rules obtained from the tech file. Rules can be added to specific devices
to compare metrics and check that the devices fall within specified thresholds. After the execution module has ran a report dictionary is created
for the report generator module to output informational output such that the user is able to analyze immediate metrics fast.

This module follows the following process:
1. Obtain Dsi Parameters from the Uniquification process
2. Obtain a Rule file from the Data Extractor, (or obtain the information from dsi.Data need to decide before pushing)
3. Read next possible instructions and handle edge-cases before sending information to the corresponding rule handler
4. Obtain necessary information to execute the rule
	- Device: device that the rule applies to
	- Comparison device (optional): if the rule requires them for comparison, for example: the rule "compare"
5. After every rule execution, get a dictionary with the following parameters and attach them to a Report dictionary. (some of the output comes from the executor module itself, others from the rules)
	- Rule: name of the rule executed
	- Device: device it was executed on
	- limit result: the tag attributes and status
	- notes: information related to the nodes ex: if the rule is compared, what percentage of the devices are the same (8%, 10%, etc.)
6. Attach output to the device parameter on the DSI
6. Repeat for all available rules
7. Send report to the next stage

This module currently incorporates the following rules:

### Compare Rule:
Compares two different device simulations and their data values against one or more limits. 
{Description}  
{Process}
Next
{Output}
Test cases for the Compare Rule are within test_ExecRule.py and cover tests 1-7. The percent difference calculation handles tests 1-4, the multiplier calculation covers tests 5 and 6, and test 7 checks the absolute difference calculation.

### Check Rule:
{Description}
{Process}
{output}
Test cases for the Check Rule are within test_ExecRule.py and cover tests 8-9.

### Corner-Compare Rule:
Input: Two or more corners of a device simulation
Output: Highest exceeded limit & corresponding comparison value 

Takes as input a list of corners for a given device simulation and retrieves each specified corner’s data values if present. The comparisons calculated are currently the same as the comparison’s in the Compare rule. The Corner-Compare rule will then iterate through all the possible combinations of corner values present and use each limit against the combination. The highest priority limit that was exceeded by any corner combination comparison is the one reported for the Corner-Compare rule along with the value of the comparison.

### Evaluate Limits of a Rule:
Input: Two or more limits
Takes two limits and evaluates them on the priority system (Fail > Positive number > Warning > Number 0 > Note > Negative number > Pass. Currently assumes in processing that no other characters are present with number limits.

## The newly added Report Generation Module process:
This section of the model aims to facilitate the information that occurred during the run time of the program, it aims to capture any relevant information, such as how many devices were simulated, how many rules executions occurred, what devices need immediate attention. As well as what stages occurred during the program.

A new class was defined “Report Generator, at the present moment it contains only 2 member variables, “RulesExecuted” [dictionary] & “Stages_Completed” [list], to use this class you will use the

### “Add Rule” 
This function has the parameters: “device” [string] (the name of the device the rules were applied to) & “rule” [dictionary] (the rule name and information that came when executing the rule). Calling this function with valid parameters (not blank or empty) will automatically store information about the rules stored and used for data analysis in the “RulesExecuted” variable

### “Add Stage”
This function has the parameter: “stage” [string] (the name of the stage currently being executed). This function is used whenever a new stage was executed, such that if we need to start the simulation across different stages we know what was executed during runtime
