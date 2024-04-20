# This is devsim.py, made by Adrian Treadwell
import argparse
from .config_loader import config
from .dsi import Dsi
from . import measures
from .parameter import Parameter
from .controller import Controller
import ruamel.yaml
yaml = ruamel.yaml.YAML(typ='safe')
import os
import sys
from .flatten import flatten
from .init import Init
from .meas_helper import MeasHelper
from .logger import Logger
from .views.LaTeX.report import main as report
from .views.view_funcs import print_valid_views, print_config, get_pdf_outputs
import subprocess
from .metrics.mdm_parser import print_valid_routines
from .utils import set_scale
import re
from .RuleExec import MDRC as Exec
from .reportGeneration import ReportGenerator as RGen

class DevSim:
    # Update: this actually works now, simply printing
    # the same str that was inputted.

    def __init__(self):
        logger = Logger()
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--input", type=str)
        parser.add_argument("-s", "--sample", type=str)
        parser.add_argument("-ms", "--meas_scale", type=float,default=1.0,help="Scales measurement parameters by this factor.",dest="meas_scale")
        parser.add_argument("-w", "--workspace", action="store_true")
        parser.add_argument(
            "-r",
            "--report",
            action="store_true",
            help="Generate LaTex report with new or existing .yal layout file",
        )
        parser.add_argument(
            "-uo",
            "--uniq_only",
            dest="uniq_only",
            action="store_true",
            help="Only uniquify parameters and write unique dsi.yml",
        )
        parser.add_argument(
            "-m",
            "--meas",
            type=str,
            dest="meas",
            help="toplevel meas directory.  With -md option, writes replay file and quits.  Without, goes directly to dsi file.  Currently only supports mdm files.",
        )
        parser.add_argument(
            "-md",
            "--meas_dry",
            type=str,
            default="meas_input_list.replay",
            dest="meas_dry",
            help="write meas_input_list.replay and quit",
        )
        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            dest="debug",
            help="Enable debug output/behavior",
            default=False,
        )
        parser.add_argument(
            "-mf",
            "--meas_from",
            type=str,
            dest="meas_from",
            const="meas_input_list.replay",
            help="read meas_input_list.replay and generate dsi",
            nargs="?",
        )
        parser.add_argument(
            "-mdsi",
            "--meas_dsi",
            type=str,
            dest="meas_dsi",
            const="meas.dsi.yml",
            help="Name of dsi file generated from measurements",
            nargs="?",
        )
        parser.add_argument(
            "-mkop",
            "--meas_kop",
            type=str,
            dest="meas_kop",
            const="kop.dsi.yml",
            help="Name of dsi kop file generated from measurements",
            nargs="?",
        )
        parser.add_argument(
            "-print-metric-routines",
            "--print-metric-routines",
            dest="print_metric_routines",
            action="store_true",
            help="Print valid metric routines used for techfile configuration and exit",
        )
        parser.add_argument(
            "-print-view-config",
            "--print-view-config",
            dest="config_to_print",
            type=str,
            help="Print viewconfig and exit. Use --print-valid-views for valid arguments",
        )
        parser.add_argument(
            "-print-valid-views",
            "--print-valid-views",
            dest="print_valid_views",
            action="store_true",
            help="Print valid viewtypes and exit",
        )
        parser.add_argument(
            "-tf",
            "--techfile",
            type=str,
            dest="techfile",
            help="Name of techfile if not relying on autodiscovery.  To force without using this, add the relative path to the techfile into .techfile in the current directory.",
        )
        parser.add_argument(
            "-pdf",
            "--combine-pdfs",
            type=str,
            dest="pdf",
            help="Combine generated pdfs into single file for easy viewing",
        )
        parser.add_argument(
            "-vo",
            "--views-only",
            action="store_true",
            dest="views_only",
            help="Only create views from previously run simulations",
        )

        args = parser.parse_args()
        print(args)
        set_scale(args.meas_scale)
        if args.debug:
            logger.setLogLevel("DEBUG")
        if args.report:
            report()
            exit()

        if args.print_valid_views:
            print_valid_views()
            exit()

        if args.config_to_print:
            print_config(args.config_to_print)
            exit()

        if args.print_metric_routines:
            print_valid_routines()
            logger.info("To implement in techfile metric, follow the example")
            example_dict = dict(
                measure=dict(
                    curve=dict(x="id", y="vg",),
                    stimuli=dict(vd="vdlin", vg="vgg", vb=0),
                    routine=dict(name="calc_id", args=["w", "vgg"]),
                )
            )
            yaml.dump(example_dict,sys.stdout)
            exit()

        init = Init()
        self.config_path = init.find_config()
        try:
            f = open(self.config_path)
            self.conf = yaml.load(f)
        except:
            self.conf = config
            self.config_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../conf/config.yml")
            )

        # self.techfile = init.find_techfile(self.conf, self.config_path)
        if args.techfile:
            self.techfile = args.techfile
        elif os.path.exists(".techfile"):
            with open(".techfile", "r") as f:
                try:
                    path = f.readline()
                    self.techfile = os.path.realpath(path.rstrip())
                except:
                    logger.warning("Unable to read ./.techfile for techfile.")

        else:
            logger.warning(
                "No techfile specified.  Either specify a techfile with -tf or write the path to it in ./.techfile"
            )
            
        try:
            self.dsrf_file = args.input.split(".")[0] + ".dsrf.yml"
        except:
            self.dsrf_file = "output.dsrf.yml"
        try:
            self.dsr_file = args.input.split(".")[0] + ".dsr.yml"
        except:
            self.dsr_file = "output.dsr.yml"

        self.techdata = None
        self.dsi_file = args.input
        try:
            tf = open(self.techfile)
            logger.info("Techfile found.")
            self.techdata = yaml.load(tf)

        except ruamel.yaml.parser.ParserError as e:
            logger.fatal(e)
        except ruamel.yaml.scanner.ScannerError as e:
            logger.fatal(e)
        except:
            logger.info("No techfile found.")
            self.techdata = dict()
        if args.meas_from:
            logger.info(f"Reading meas paths from {args.meas_from}")
            mh = MeasHelper(self.techdata)
            mh.read_meas_list(args.meas_from)
            if args.meas_dsi:
                mh.write_iv_dsi_file(args.meas_dsi)
                logger.info(f"Wrote {args.meas_dsi}")
            if args.meas_kop:
                mh.write_metric_dsi_file(args.meas_kop)
                logger.info(f"Wrote {args.meas_kop}")
            mh.write_device_map()
            exit()
        elif args.meas:
            mh = MeasHelper(self.techdata)
            mh.import_dir(args.meas)
            mh.create_meas_objects()
            if args.meas_dry:
                mh.write_meas_list(args.meas_dry)
                mh.write_device_map()
                exit()
            else:
                mh.write_iv_dsi_file(args.meas_dsi)
                mh.write_device_map()
                logger.info(f"Wrote {args.meas_dsi}")
                exit()
        sample = args.sample
        self.pdfout = None
        if args.pdf:
            self.pdfout = args.pdf
        self.dsi = Dsi(self.conf, self.techdata, args.debug)
        if (
            self.dsi_file
            and self.dsi_file != "devsim.replay"
            and self.dsi_file[-7:] != "dsi.yml"
        ):
            logger.error(self.dsi_file)
            logger.fatal("Input must have dsi.yml extension")
            exit
        elif self.dsi_file and self.dsi_file[-7:] == "dsi.yml":
            self.dsi.add_yml(self.dsi_file)
        else:
            if os.path.isfile("devsim.replay") and not sample:
                f = open("devsim.replay")
                lines = list(f.read().split())
                for line in lines:
                    if os.path.isfile(line.strip()):
                        self.dsi.add_yml(line.strip())

            if len(self.dsi.ymlFiles) == 0:
                logger.info("No files found from replay")
            else:
                input_arr = []
                for dirent in os.scandir(os.getcwd()):
                    if dirent[-7:-1] != "dsi.yml":
                        continue
                    else:
                        input_arr.append(dirent)
                dirent.close()
                if len(input_arr) == 0:
                    sample = "./sample.dsi.yml"
                else:
                    replay = open("./sample.dsi.yml")
                    for arr in input_arr:
                        replay.write(arr)
                    replay.close()
                    print(
                        "Created devsim.replay. Edit replay file then type 'devsim' to continue."
                    )
                exit()

        if sample:
            if sample[:-8:-1] != ".dsi.yml":
                sample += ".dsi.yml"
            if self.techdata:
                sample = Dsi(sample, self.techdata)
                print("Made sample")
            else:
                print("Cannot create a sample without a techfile")
        if args.uniq_only:
            uniq_name = "uniq.dsi.yml"
            logger.info(f"Writing uniquified parameters to {uniq_name}")
            with open(uniq_name, "w") as f:
                f.write(yaml.dump(self.dsi.Data))
            exit()
        if args.views_only:
            logger.info("Only creating views from previous sims from -i argument.")
            for keys in self.dsi.Data:
                if not self.dsi.Data[keys]:
                    continue
                param = Parameter(config, self.techdata, self.dsi.Data[keys], keys)
                self.dsi.AddParam(param)
            self.dsi.create_views()
            if self.pdfout:
                pdf_files = get_pdf_outputs()
                command = f"pdfunite {' '.join(pdf_files)} {self.pdfout}"
                logger.info(f"Combining all generated pdfs into {self.pdfout}")
                logger.info(f"Running {command}")
                subprocess.run(command,shell=True)
            exit()
        # new container object that contains all rules
        self.dsrf_rules = {'rules':[]}

    # creates and populates new rules
    # build_dsrf_rule input:
    # param_object: (Parameter(s)) related to the rule
    # rule_number: (str) rule identification within the dsi data
    def build_dsrf_rule(self,param_object,rule_number):
        #call in main to test
        new_rule = {}
        #case for compare rule
        if 'compare' in param_object['mdrc'][rule_number]:
            new_rule['rule'] = 'compare'
            new_rule['rule number'] = rule_number
            new_rule['device simulations'] = []
            if 'metrics' in param_object:
                new_rule['metrics'] = param_object['metrics']
            else:
                new_rule['metrics'] = None
            new_rule['device simulations'].append(param_object['measure name'])
            new_rule['device simulations'].append(param_object['measure name'] + "_" + param_object['mdrc'][rule_number]['compare']['control']['simulator'])
            new_rule['string'] = param_object['mdrc'][rule_number]['string']
            new_rule['limit'] = param_object['mdrc'][rule_number]['limit']
            self.dsrf_rules['rules'].append(new_rule)	
    	
        #case for limit check rule
        if 'check' in param_object['mdrc'][rule_number]:
    	    #only write check instruction if check rule checks for metric simulated by this param object
    	    if param_object['mdrc'][rule_number]['check']['metrics'] == param_object['metrics']:
                new_rule['rule'] = 'check'
                new_rule['rule number'] = rule_number
                new_rule['device simulations'] = []
                if 'metrics' in param_object:
                    new_rule['metrics'] = param_object['metrics']
                else:
                    new_rule['metrics'] = None
                new_rule['device simulations'].append(param_object['measure name'])
                new_rule['string'] = param_object['mdrc'][rule_number]['string']
                new_rule['limit'] = param_object['mdrc'][rule_number]['limit']
                self.dsrf_rules['rules'].append(new_rule)

        #case for limit check rule
        if 'corner_compare' in param_object['mdrc'][rule_number]:
    	    #only write check instruction if check rule checks for metric simulated by this param object
    	    if param_object['mdrc'][rule_number]['corner_compare']['metrics'] == param_object['metrics']:
                new_rule['rule'] = 'corner_compare'
                new_rule['rule number'] = rule_number
                new_rule['device simulations'] = []
                if 'metrics' in param_object:
                    new_rule['metrics'] = param_object['metrics']
                else:
                    new_rule['metrics'] = None
                new_rule['device simulations'].append(param_object['measure name'])
                new_rule['string'] = param_object['mdrc'][rule_number]['string']
                new_rule['limit'] = param_object['mdrc'][rule_number]['limit']
                self.dsrf_rules['rules'].append(new_rule)

    def main(self):
        jobs = []
        logger = Logger(printSummary=False, logLevel="INFO")
        # create a repport generator object
        report = RGen()

        report.AddStage("DSI Parameterization")
        for keys in self.dsi.Data:
            if not self.dsi.Data[keys]:
                continue
            # to infineon: the following line is how we tested 
            #   metrics that we could not access within our simulator's limited metrics:
            self.dsi.Data[keys]['simulations'] = {"top_tt":{"nominal":12.34}}

            # you should not need the previous lines within your complete simulator
            param = Parameter(config, self.techdata, self.dsi.Data[keys], keys)
            self.dsi.AddParam(param)

            # the following is the uniquification process,
            # it works by reading possible rules and determinig whether we need to create a new parameter or not
            if 'mdrc' in self.dsi.Data[keys]:
                for rule in self.dsi.Data[keys]['mdrc']:
                    self.build_dsrf_rule(self.dsi.Data[keys],rule)
                    if 'compare' in self.dsi.Data[keys]['mdrc'][rule]:
                        if 'simulator' in self.dsi.Data[keys]['mdrc'][rule]['compare']['control']:
                            new_param = self.dsi.Data[keys].copy()
                            new_param.pop("mdrc")
                            new_param["control"]["simulator"] = self.dsi.Data[keys]['mdrc'][rule]['compare']['control']['simulator']
                            new_param["control"]["language"] = self.dsi.Data[keys]['mdrc'][rule]['compare']['control']['simulator']
                            new_key = keys + "_"  + self.dsi.Data[keys]['mdrc'][rule]['compare']['control']['simulator']
                            #new_key = keys.split("__")[0] + "_" + self.dsi.Data[keys]['mdrc'][rule]['compare']['control']['simulator'] + "__"  + keys.split("__")[1]
                            new_param["measure name"] = new_param["measure name"] + "_" + self.dsi.Data[keys]['mdrc'][rule]['compare']['control']['simulator']
             
                            #creation of a parameter issues, should not create errors in the complete simulator
                            try:
                                self.dsi.AddParam(Parameter(config,self.techdata,new_param,new_key))
                            except Exception as e:
                                logger.fatal(f"Parameter Creation ERROR (MDRC) {e}\n Key value:{new_key}, \n Param: {new_param}")
                                continue
            
            
            bucket_idx = None
        
            for i, bucket in enumerate(jobs):
                if not bucket.control == param.param_data["control"]:
                    continue
                if param.param_data["control"].get("unique", False):
                    continue
                bucket_idx = i

                break
            if bucket_idx is not None:
                jobs[bucket_idx].add_param(param)
            else:
                pass
                #jobs.append(Controller(param))


        report.AddStage("MDRC Generator")

        # chose whether we need to run a preset of rule file or 
        # create a new rule file
        
        overwrite_dsrf = True

        if not overwrite_dsrf:
            try:
                with open(self.dsrf_file,"r") as f:
                    self.dsrf_rules = yaml.load(f)
                    #yaml.dump(self.dsrf_rules,f)
            except Exception as e:
                logger.error(f"dsrf file '{self.dsr_file}' does not exist")
                logger.warning(f"creating a new dsrf file")
                overwrite_dsrf = True
        if overwrite_dsrf:   
            if self.dsrf_rules['rules'] != []:
                with open(self.dsrf_file,"w") as f:
                    yaml.dump(self.dsrf_rules,f)
                    

        report.AddStage("Simulation Enviorment")

        jobids = []
        graphonly = None
        nosim = True
        if not (graphonly or nosim):
            for job in jobs:
                # job.create_rundir()
                job.netlist()
                jobids.append(job.simulate())
        jobids = list(flatten(jobids))
        if (not (nosim or graphonly)) and len(jobids) > 0:
            dummy = "bsub -R '(osrel==60 || osrel==70 || osrel==80)' -K -w '{jobids}' cat /dev/null".format(
                jobids="&&".join(map(lambda x: "ended({x})".format(x=x), jobids))
            )
            subprocess.run(dummy, shell=True)

        for job in jobs:
            job.parse()


        report.AddStage("MDRC Execution")


        #Create a map to execute rules faster
        # we recommend infineon change from a parameter list to a dictionary, 
        #  easier to search and uniquify
        ParamMap = {}
        for idx in range(len(self.dsi.Params)):
            p = self.dsi.Params[idx]
            for x in p:
                ParamMap[x.measure_name] = x
        
        
        
        # create Execute object and start executing rules
        executor = Exec()

        for Crule in (self.dsrf_rules["rules"]):
            Param_device = Crule["device simulations"]
            RuleOut = None
            logger.info(f"Runing {Crule['rule']} for {Param_device[0]} ({Crule['rule number']})")

            #verify that the mdrc section is correctly placed in the original device
            if ("MDRC_Execution" not in ParamMap[Param_device[0]].param_data["mdrc"][Crule["rule number"]].keys()):
                ParamMap[Param_device[0]].param_data["mdrc"][Crule["rule number"]]["MDRC_Execution"] = []

            #choose and execute the rule
            if (Crule['rule'] == "compare"):
                RuleOut = executor.EX_Compare(ruleID=Crule["rule number"], ruleMetric=Crule["metrics"], dvSim=[ParamMap[Param_device[0]],ParamMap[Param_device[1]]], dictLimit=Crule["limit"])
            elif (Crule['rule'] == "check"):
                    RuleOut = executor.EX_Check(ruleID=Crule['rule number'], ruleMetric=Crule["metrics"], dvSim=[ParamMap[Param_device[0]]], dictLimit=Crule['limit'])
            elif (Crule['rule'] == "corner_compare"):
                if (len(Param_device) == 2):
                    RuleOut = executor.EX_Corner_Compare(ruleID=Crule['rule number'], dvSim=[ParamMap[Param_device[0]],ParamMap[Param_device[1]]], dictLimit=Crule['limit'],ruleMetric=Crule["metrics"])
                elif (len(Param_device) == 1):
                    RuleOut = executor.EX_Corner_Compare(ruleID=Crule['rule number'], dvSim=[ParamMap[Param_device[0]]], dictLimit=Crule['limit'],ruleMetric=Crule["metrics"])
                else:
                   RuleOut = {"ID":Crule['rule number'],"ERROR":f"Error at [{Crule['rule number']}], with rule action [{ str(Crule['rule'])}],  number of parameters not suported ({len(Param_device)})"}   
            else: 
                RuleOut = {"ID":Crule['rule number'],"ERROR":f"Error at [{Crule['rule number']}], with rule action [{ str(Crule['rule'])}] , device [{ Param_device[0] }]"}   
            
            # this stage is a catch rule error execution rule, should not trigger. 
            # (RuleExec.py file corruption or rule typo)
            if RuleOut == None:
                RuleOut = {"ID":Crule['rule number'],"ERROR":f"Error at [{ str(Crule['rule number']) }] , with device [{ Param_device[0] }]"}
           
            # print out an error if the rule is invalid
            if( 'ERROR' in RuleOut.keys()):
                logger.error(f"Error in rule {RuleOut['ID']} produced:'{RuleOut['ERROR']}'")   
            
            ParamMap[Param_device[0]].param_data["mdrc"][Crule["rule number"]]["MDRC_Execution"].append(RuleOut)
            report.AddRule(device=ParamMap[Param_device[0]].device,rule=RuleOut.copy())
        
        report.AddStage("DSO Output File Generation")
        self.dsi.print()
        self.dsi.create_views()

        #print out dso file
        if self.pdfout:
            pdf_files = get_pdf_outputs()
            command = f"pdfunite {' '.join(pdf_files)} {self.pdfout}"
            logger.info(f"Combining all generated pdfs into {self.pdfout}")
            logger.info(f"Running {command}")
            subprocess.run(command,shell=True)
            
        #add last stage onto the report stage and print out report as "dsr"
        report.AddStage("MDRC Report Generation")
        report.printReport(self.dsr_file)
        

        
if __name__ == "__main__":
    dev = DevSim()
    dev.main()
