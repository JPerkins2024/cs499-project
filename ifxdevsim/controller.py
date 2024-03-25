# Controller.py, made by Adrian Treadwell
from . import dsi
import os
from .config_loader import config
import re
from datetime import datetime
from .logparser import LogParser
from copy import deepcopy
from .flatten import flatten
import numpy as np
import stat
import subprocess
import getpass
import math
import socket
from .logger import Logger
from .utils import grouper, expand_generic_sweep


class ControllerError(Exception):
    pass


class Controller:
    def __init__(self, param):
        self.params = [param]
        self.instance_map = {}
        self.meas_names = [param.measure_name]
        self.control = deepcopy(param.param_data["control"])
        self.language = self.control.get("language")
        self.model_language = self.control.get("model language", False) or self.language
        self.corners = self.get_corners()
        self.agemode = self.check_agemode()
        self.rundir = self.create_rundir()

    def add_param(self, param):
        self.params.append(param)
        self.meas_names.append(param.measure_name)

    def netlist(self):
        options = self.get_options()
        if self.agemode:
            stress_options = options + self.get_options("stress ")
            aged_options = options + self.get_options("aged ")

        params = (
            self.get_params()
        )  # if params returns none, params_netlist is none as well. :(
        if self.agemode:
            stress_params = params + self.get_params("stress ")
            aged_params = params + self.get_params("aged ")

        param_netlist = []
        stress_netlist = []
        i = 0
        for each in self.params:
            tmp_i = str(i)
            if each.param_data.get("sweep_k"):
                if each.param_data["sweep_k"].get(1):
                    tmp_i = tmp_i + each.param_data["sweep_k"][1]
                if each.param_data["sweep_k"].get(2):
                    tmp_i = tmp_i + each.param_data["sweep_k"][2]

            param_netlist.append(each.netlist(tmp_i))
            if self.agemode:
                stress_netlist.append(each.netlist(tmp_i, "stress"))
            # self.instance_map[each.instance] = i
            i = i + 1
        self.finalize()
        self.write_netlists(options, params, param_netlist)
        if self.agemode:
            self.write_netlists(stress_options, stress_params, stress_netlist, "stress")
            self.write_netlists(aged_options, aged_params, param_netlist, "aged")

        self.print_sim_commands()

    def write_netlists(self, options, params, param_netlist, mode=None):
        extension = self.get_extension()
        for cor in self.corners:
            if mode:
                f = open(
                    self.rundir
                    + "/{cor}__{mode}.{extension}".format(
                        cor=cor["name"], mode=mode, extension=extension
                    ),
                    "a",
                )
                f.write("Circuit file created by devsim\n")
                if self.control["simulator"] == "titan":
                    f.write(".SAVE {cor}__{mode}".format(cor=cor["name"], mode=mode))
            else:
                f = open(
                    "{rundir}/{cor}.{extension}".format(
                        rundir=self.rundir, cor=cor["name"], extension=extension
                    ),
                    "a",
                )
                f.write("Circuit file created by devsim\n")
                if self.control["simulator"] == "titan":
                    f.write(f".SAVE {cor['name']}\n")
                    f.write(".database ASSERT_FILE = {cor}.db\n".format(cor=cor['name']))
            if self.control["simulator"] == "titan":
                f.write(".echo off\n")
            if self.language == "spectre":
                f.write("simulator lang=spice\n")
            f.write(options)
            if self.model_language == "spectre":
                f.write("simulator lang=spectre\n")
            f.write(cor["string"])
            if self.model_language == "spectre":
                f.write("simulator lang=spice\n")
            f.write(params)
            if self.control.get("vts", False):
                f.write("simulator lang=espice\n")
            f.write("\n".join(param_netlist) + "\n")
            if self.control.get("vts"):
                f.write("simulator lang=spice\n")
            f.write(self.get_temperature(mode) + "\n")
            f.write(self.get_control_statements(cor["name"], mode))
            f.write(".end\n")
            f.close()
        return None

    def print_sim_commands(self):
        os.chdir(os.getcwd())
        arr = []
        load_balance = self.control["load balancer"]
        simargs = self.get_simargs()
        if self.agemode:
            types = [None, "__stress", "__aged"]
        else:
            types = [None]
        for cor in self.corners:
            for each in types:
                simarg = re.sub(
                    "@CORNER@",
                    "{cor}{type}".format(
                        cor=cor["name"], type="" if each is None else each
                    ),
                    simargs,
                )  # Note for monday - I will be using re library instead of gsub
                run_str = "{load_balance} -o {cor}{type}.launch.log {simarg}".format(
                    cor=cor["name"],
                    load_balance=load_balance,
                    type="" if each is None else each,
                    simarg=simarg,
                )
                arr.append(run_str)
        arr = "\n".join(arr)
        runscript_path = os.path.join(self.rundir, "run_simulation.sh")
        f = open(runscript_path, "a+")
        f.write(arr)
        f.close()
        st = os.stat(runscript_path)
        os.chmod(runscript_path, st.st_mode | 0o0111)
        return None

    def simulate(self):
        logger = Logger()
        jobids = []
        cwd = os.getcwd()
        os.chdir(self.rundir)
        if not os.path.isfile("run_simulation.sh"):
            raise KeyError("Devsim was not properly netlisted.")
        file = open("run_simulation.sh", "r")
        run = file.read().split("\n")
        # run.insert(0, "module load LSF\n") # to represent the file as an array of its lines, you have to call split for each newline or it stores as string
        if len(run) != len(self.corners):
            raise Exception("Devsim was not properly netlisted")
        i = 0
        for cor in run:
            if "__stress" in cor:
                stress_id = "2>&1 {test}".format(test=cor.rstrip())
                if ">" in stress_id is False and "<" in stress_id is False:
                    raise Exception(
                        "LSF did not return a job ID: {chomp}".format(cor.rstrip())
                    )
                stress_id = stress_id.split(">")[0].split("<")[1]
                self.corners[i - 1]["id"][1] = stress_id
                aged_cmd = cor.rstrip()
                # Use re.sub for the gsub.sub Ruby code.
                pattern = "__stress"
                aged_cmd = re.sub(pattern, "__aged", cor)
                aged_cmd = re.sub(
                    "bsub", "bsub -w 'ended {stress_id}' ".format(stress_id=stress_id)
                )
                aged_id = "2>&1{aged_cmd}".format(aged_cmd=aged_cmd)
                if ">" in aged_id is False and "<" in aged_id is False:
                    raise Exception(
                        "LSF did not return a job ID: {aged_cmd}".format(
                            aged_cmd=aged_cmd
                        )
                    )

                aged_id = aged_id.split(">")[0].split("<")[1]
                self.corners[i - 1]["id"][2] = aged_id
                jobids.append(self.corners[i - 1]["id"][1])
                jobids.append(self.corners[i - 1]["id"]["2"])
            else:
                self.corners[i]["id"] = []
                # jobid = subprocess.Popen('2>&1 {strip}'.format(strip = cor.rstrip()), shell = True, executable = "/bin/tcsh", stderr = PIPE, stdout = PIPE)
                # out, err = jobid.communicate()
                out = subprocess.run(
                    cor, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                )
                out_stderr = out.stderr.decode()
                if ">" in out_stderr is False and "<" in out_stderr is False:
                    raise "LSF did not return a Job ID: {strip}".format(
                        strip=cor.rstrip()
                    )
                # jobid = out
                # jobid.decode("utf-8")
                jobid = out_stderr.split(">")[0].split("<")[1]

                logger.info(f"JobID for {cor}: {jobid}")
                self.corners[i]["id"].append(jobid)
                jobids.append(jobid)
            i = i + 1
        if len(self.corners) != i:
            raise "Devsim was not properly netlisted."
        os.chdir(cwd)
        return jobids

    def parse(self):
        parselist = self.get_parselist()
        self.parse_errors(self.get_logfiles())
        data = self.parse_measures(parselist)

        for k, par in enumerate(self.params):
            if par.param_data.get('simulations'):
                # Do unit conversion on any existing measurement corners.
                for corner,cdict in par.param_data['simulations'].items():
                    for mtype,val in cdict.items():
                        if isinstance(val,list):
                            par.add_simulations(corner,val,mtype)
                        else:
                            par.add_simulations(corner,[val],mtype)
            if par.param_data.get("sweep") and par.param_data.get(
                "_additional_sweep_measures"
            ):
                sweep_data = dict()
                lookup_measures = []
                tmp_k = f"{k}"
                if par.param_data.get("sweep_k") and par.param_data["sweep_k"].get(2):
                    tmp_k += f"{par.param_data['sweep_k'][2]}"
                for k_new, x in expand_generic_sweep(par.get_sweep(1), tmp_k):
                    p = None
                    if par.param_data["sweep"].get(2):
                        p = par.get_sweep(2)
                    lookup_measures.append([x, p, f"{par.find_measure_name(k_new)}"])
                for x, p, name in lookup_measures:
                    for corner, types in data[name].items():
                        for type, val in types.items():
                            if type == "nominal":
                                sweep_data[corner] = sweep_data.get(corner) or []
                                sweep_data[corner].append([x, p, val[0]])
                for corner, s_data in sweep_data.items():
                    par.add_simulations(corner, s_data, "sweep")
            elif par.param_data.get("sweep") and par.param_data.get("sweep_k"):
                tmp_k = f"{k}"
                if par.param_data["sweep_k"].get(2):
                    tmp_k += f"{par.param_data['sweep_k'][2]}"
                if par.param_data["sweep_k"].get(1):
                    tmp_k += f"{par.param_data['sweep_k'][1]}"
                measure_name = par.find_measure_name(tmp_k)
                sweep_data = dict()
                for corner, types in data.get(measure_name, {}).items():
                    for type, val in types.items():
                        if type == "nominal":
                            sweep_data[corner] = sweep_data.get(corner) or []
                            x = par.get_sweep(1)
                            p = None
                            if par.param_data["sweep"].get(2):
                                p = par.get_sweep(2)
                            sweep_data[corner].append([x, p, val[0]])
                for corner, s_data in sweep_data.items():
                    par.add_simulations(corner, s_data, "sweep")

            if data.get(par.measure_name) is None:
                continue
            else:
                for corner, types in data[par.measure_name].items():
                    for type, val in types.items():
                        par.add_simulations(corner, val, type)

    def parse_errors(self, logs):
        logger = Logger()
        simulator = self.control["simulator"]
        log_ext = config["valid simulators"][simulator]["log"]
        errors = list(map(lambda log: LogParser(log, simulator), logs))
        has_errors = list(
            map(
                lambda q: [q.logfile, q.errors],
                filter(lambda q: len(q.errors) > 0, errors),
            )
        )
        if len(has_errors) > 0:
            error_str = ""

            error_str += f"Rundir is : #{self.rundir}\n"
            for arr in has_errors:
                corner, messages = arr
                error_str += f"{os.path.splitext(corner)[0]} Errors"
                for message in messages:
                    error_str += message
            logger.error(error_str)
            # Simulation errors are never fatal to devsim.  Commenting for now until I verify that is all that is going on here.
            #logger.fatal("Simulation errors found.  Exiting...")

    def create_rundir(self):
        # rundir_path = os.getcwd()
        logger = Logger()
        userid = getpass.getuser()
        rundir_path = os.path.join("/opt/tmp_share", userid, "devsim/work")
        today = datetime.now()
        final_dir = None
        n = 0
        eok = False
        while True:
            if n > 1000:
                raise ControllerError("Having trouble creating a unique directory")

            try_dir = rundir_path + f"/devsim_{socket.gethostname()}_{os.getpid()}_{n}"
            if not os.path.exists(try_dir):
                final_dir = try_dir
                break
            elif os.path.isdir(try_dir) and os.path.exists(
                try_dir + f"/devsim_{socket.gethostname()}_{os.getpid()}_{n}_tag"
            ):
                final_dir = try_dir
                eok = True
                break
            n += 1

        if not os.path.exists(final_dir):
            logger.info(f"Creating toplevel rundir {final_dir}")
        os.makedirs(final_dir, exist_ok=eok)
        with open(
            try_dir + f"/devsim_{socket.gethostname()}_{os.getpid()}_{n}_tag", "w"
        ) as f:
            f.write("tag")
        n = 0
        while True:
            if n > 1000:
                raise ControllerError("Having trouble creating a unique directory")

            try_dir = final_dir + f"/{n}"
            if not os.path.exists(try_dir):
                final_dir = try_dir
                break
            n += 1
        if not os.path.islink("./work") and not os.path.exists("./work"):
            os.symlink(rundir_path, "work")
        logger.info(f"Creating rundir {final_dir}")
        os.mkdir(final_dir)
        self.rundir = final_dir
        return self.rundir

    def get_options(self, typeA=None):
        if self.control.get(
            "{Type1}options".format(Type1=typeA if typeA is not None else ""), False
        ):
            options = self.control[
                "{Type2}options".format(Type2=typeA if typeA is not None else "")
            ]
        else:
            simulator = self.control["simulator"]
            options = config["valid simulators"][simulator][
                "{Type3}options".format(Type3=typeA if typeA is not None else "")
            ]

        if type(options) != list:
            options = [options]
        if self.control.get(
            "append {Type4}options".format(Type4=typeA if typeA is not None else ""),
            False,
        ):
            append = self.control[
                "append {Type5}options".format(Type5=typeA if typeA is not None else "")
            ]
            if type(append) != list:
                append = [append]
                options += append
        str = ""
        for each in options:
            if each is None:
                continue
            str += ".option {each1}\n".format(each1=each)
        if str is not None:
            str += "\n"
        return str

    def get_params(self, type=None):
        if self.control.get(
            "{Type1}parameters".format(Type1=type if type is not None else ""), None
        ):
            params = self.control["{Type1}parameters".format(Type1=type)]
        else:
            simulator = self.control["simulator"]
            params = config["valid simulators"][simulator].get(
                "{Type1}parameters".format(Type1=type if type is not None else ""), None
            )

        if params is None:
            return ""
        str = ""
        for param, val in params:
            if param is None or val is None:
                continue
            key = param
            val = params[key]
            str += ".param {key}={val}\n".format(key=key, val=val)
        if str is not None:
            str += "\n"
        return str

    def get_simargs(self):
        if self.control.get("simargs", False):
            simargs = self.control["simargs"]
        else:
            simulator = self.control["simulator"]
            simargs = config["valid simulators"][simulator]["simargs"]
        if type(simargs) != list:
            simargs = [simargs]
        if self.control.get("append simargs", False):
            append = self.control["append simargs"]
            if type(append) != "list":
                append = [append]
        str = ""
        for opt in simargs:
            str += " {opt}".format(opt=opt)
        return str

    def get_extension(self):
        if self.control.get("extension", False):
            extension = self.control["extension"]
        else:
            simulator = self.control["simulator"]
            extension = config["valid simulators"][simulator]["extension"]
        return extension

    def get_corners(self):
        cor_array = []
        corners = self.control["corners"].split(":")
        tempCorners = []
        try:
            other_corners = self.control["other corners"].split(",")
        except:
            other_corners = None
        for each in corners:
            corners = tempCorners.append(each.split(","))
        corners = tempCorners
        size = 0
        for arr in corners:
            size = max([size, len(arr)])
        for arr in corners:
            if len(arr) == size:
                max_index = corners.index(arr)

        uniqueCopy = corners
        for n in range(0, size):
            cor_hash = {}
            if len(uniqueCopy) != len(corners):

                iter = 0
                current_names = map(lambda x: x["data"], cor_array)
                while corners[max_index][n] in current_names:
                    iter = iter + 1
                cor_hash["name"] = "{corners}{iter}".format(
                    corners=corners[max_index][n], iter=iter
                )
            else:
                cor_hash["name"] = corners[max_index][n]
            string = []
            for cor in corners:
                try:
                    corner = cor[n]
                except:
                    corner = None
                if corner is None:
                    corner = cor[0]
                if corner is None or len(corner) == 0:
                    continue
                string.append(self.print_corner(corner))
            if other_corners:
                for cor in other_corners:
                    string.append(self.print_corner(cor))

            cor_hash["string"] = "\n".join(string) + "\n"
            cor_array.append(cor_hash)
        return cor_array

    def check_agemode(self):
        if self.control["mode"].split()[-1] == "aging":
            return True
        else:
            return None

    def print_corner(self, corner):
        path = self.find_model_path(corner)
        if self.model_language == "spectre":
            str = self.print_spectre_corner(path)
        elif self.model_language == "spice":
            str = self.print_spice_corner(path)
        else:
            raise KeyError("Invalid Language")
        return str

    def find_model_path(self, corner):
        os.chdir(os.getcwd())
        paths = self.control["models path"].split(",")
        if paths is None:
            paths = [""]
        pathY = None

        print(f"#\n###\n paths: {paths}")
        print(f"current dir: {os.getcwd()}")
 
        for search in paths:
            x = os.path.abspath(search)
            print(f"x dir: {x}")
            if not os.path.isfile(x):
                continue
            if not os.path.isdir(
                os.path.abspath(
                    "{search}/{corner}".format(search=search, corner=corner)
                )
            ):
                continue
            pathY = "{search}/{corner}".format(search=search, corner=corner)
        if pathY is None:
            for search in paths:
                if os.path.isdir(os.path.abspath(search)):
                    continue
                if not os.path.isfile(os.path.abspath(search)):
                    continue
                pathY = [search, corner]
                break
        
        if pathY is None:
            '''
            # FIX ERRROR HOLLY Shiza DIDINT KNOW I AM SADD SHIZA!!!!!!
            raise ValueError(
                "Could not find models for corner {corner}! Search path was: \n {paths}".format(
                    corner=corner, paths="\n".join(paths)
                )
            )
            '''
            pathY = ""
        return pathY

    def print_spice_corner(self, path):
        if type(path) == list:
            str = '.lib" {FilePath}" {path1}'.format(
                FilePath=os.path.abspath(path[0]), path1=path[1]
            )
        else:
            str = '.include " {FilePath}"'.format(FilePath=os.path.abspath(path))
        return str

    def print_spectre_corner(self, path):
        if type(path) == list:
            string = 'include "{path0}" section={path1}'.format(
                path0=os.path.abspath(path[0]), path1=path[1]
            )
        else:
            string = 'include "{path}"'.format(path=os.path.abspath(path))
        return string

    def finalize(self):
        self.get_start_stop_freq()
        for param in self.params:
            param.add_rundir(self.rundir)

    def calculate_minimum_step(self, sweeps):
        steps = [s["step"] for s in sweeps]
        if all(map(lambda q: q == steps[0], steps)):
            return steps[0]
        min_step = math.inf
        for s in steps:
            if min_step > s:
                min_step = s
        done = False
        while not done:
            donemaybe = False
            for s in steps:
                sign = 1
                if s < 0:
                    sign = -1
                if s / min_step != int(s / min_step):
                    if math.floor(math.log10(abs(min_step))) == math.log10(
                        abs(min_step)
                    ):
                        min_step = sign * abs(min_step / 10)
                        min_step = float(f"{min_step:.5g}")
                        donemaybe = False
                    else:
                        n = math.floor(math.log10(abs(s)))
                        min_step = sign * (pow(10, n))
                        min_step = float(f"{min_step:.5g}")
                        donemaybe = False
                else:
                    donemaybe = True
            done = donemaybe

        return min_step

    def get_start_stop_freq(self):
        self.control["start"] = 0
        self.control["stop"] = 2
        self.control["tstop"] = None
        self.control["frequency"] = []
        self.control["nsweep"] = None
        self.control["rsweep"] = None
        self.control["analysis"] = []
        analysis = []
        if self.control.get("tran", False):
            self.control["analysis"].append("tran")
        lin_steps = []
        for par in self.params:
            # Turns string into char list, for all strings, which is not the intended outcome.
            if type(par.type) == list:
                analysis = list(flatten(par.type))
            else:
                analysis = par.type
            self.control["analysis"].append(analysis)
            if (
                "sweep" in par.param_data
                and par.param_data["sweep"].get(1)
                and par.param_data["sweep"][1] in par.param_data["stimuli"]
                and analysis == "dc"
            ):
                tmp_vmin = par.get_sweep_vmin()
                tmp_vmax = par.get_sweep_vmax()
                sweep = par.get_sweep(1)
                if sweep["type"] == "lin":
                    tmp_step = par.get_sweep(1)
                    if not tmp_step.get("step"):
                        tmp_step["step"] = (
                            tmp_step["stop"] - tmp_step["start"]
                        ) / tmp_step["num steps"]
                    lin_steps.append(tmp_step)
                self.control["start"] = min(self.control.get("start", 0), tmp_vmin)
                self.control["stop"] = max(self.control.get("stop", 2), tmp_vmax)
            if "sweep" in analysis:
                tmp_vmin = float(par.param_data.get("definitions", {}).get("vmin"))
                tmp_vmax = float(par.param_data.get("definitions", {}).get("vmax"))
                self.control["start"] = self.control.get("start") or tmp_vmin
                self.control["stop"] = self.control.get("stop") or tmp_vmax
            if "ac" in analysis:
                self.control["frequency"].append(
                    float(par.param_data["definitions"]["frequency"])
                )
            if "tran" in analysis:
                self.control["tstop"] = max(
                    float(par.param_data["definitions"]["tstop"], self.control["tstop"])
                )
            if "rsweep" in analysis:
                self.control["rsweep"] = True
            if par.param_data["definitions"]["reverse sweep"]:
                self.control["nsweep"] = True
        # The below line is the faulty line
        # Update: below line was patched with custom flatten implementation that excepts strings from further decomposition
        self.control["analysis"] = list(flatten(self.control["analysis"]))
        if len(lin_steps) > 0:
            self.control["step size"] = self.calculate_minimum_step(lin_steps)

        for i, analysisvar in enumerate(self.control["analysis"]):
            if analysisvar == "sweep":
                self.control["analysis"][i] = "dc"
        self.control["analysis"] = list(set(self.control["analysis"]))
        self.control["frequency"] = list(set(self.control["frequency"]))
        self.control["start"] = float(self.control.get("start", 0.0) or 0.0)
        self.control["stop"] = float(
            self.control.get("stop", self.control.get("step size"))
            or (self.control.get("step size"))
        )

    def get_parselist(self):
        corners = []
        parselist = []
        for cor in self.corners:
            corners.append(cor["name"])
        corners = list(flatten(corners))
        for corner in corners:
            for measure in self.get_measures():
                find_cmd = f"find {self.rundir} -name '{corner}.{measure}*' -type f -exec basename \u007b\u007d ';'"
                find_str = subprocess.run(
                    find_cmd, stdout=subprocess.PIPE, shell=True
                ).stdout.decode()
                for found in find_str.split("\n"):
                    if len(found) > 0:
                        parselist.append(found.strip())
        return parselist

    def get_measures(self):
        if self.control.get("measures"):
            measures = self.control["measures"]
        else:
            simulator = self.control["simulator"]
            measures = config["valid simulators"][simulator]["measures"]
        return measures

    def get_logfiles(self):
        corner_names = list(map(lambda x: x["name"], self.corners))
        if self.agemode:
            corner_names.append(list(map(lambda x: x + "__aged", corner_names)))
        corner_names = list(flatten(corner_names))
        corner_names = np.unique(corner_names)
        logs = []
        simulator = self.control["simulator"]
        log_extension = config["valid simulators"][simulator]["log"]
        logs = list(
            map(lambda x: os.path.join(self.rundir, x + log_extension), corner_names)
        )
        return logs

    def get_temperature(self, state=None):
        str = []
        if self.control.get("stress temperature", False) and state == "stress":
            str.append(
                ".temp {control}".format(control=self.control["stress temperature"])
            )
        else:
            str.append(".temp {control}".format(control=self.control["temperature"]))
        str = "\n".join(str) + "\n"
        return str

    def get_analysis(self):
        supplies_and_dummies = []
        analyses = []
        for arg in self.control["analysis"]:
            func = "get_{arg}_analysis".format(arg=arg)
            temp1, temp2 = getattr(self, func)()
            supplies_and_dummies.append(temp1)
            analyses.append(temp2)
        # Below simulates array.compact!, but there are still 1132 entries of the dummy str in supplies_and_dummies.
        while None in supplies_and_dummies:
            supplies_and_dummies.remove(None)
        if len(supplies_and_dummies) > 1:
            raise "Improper analysis statements"
        if len(supplies_and_dummies) > 0:
            supplies_and_dummies = str(supplies_and_dummies[0]) + "\n"
        else:
            supplies_and_dummies = "\n"
        return [supplies_and_dummies, analyses]

    def get_dc_analysis(self):
        return self.get_sweep_analysis()

    def get_sweep_analysis(self):
        start = self.control["start"]
        stop = self.control["stop"]
        step = self.control["step size"]
        if start == stop and start is not None:
            stop += step

        str = []
        analysis = []
        str.append("r_dummy1 v_master 0 1e9")
        if self.control["nsweep"]:
            str.append("r_dummy2 n_master 0 1e9")
        if self.control["rsweep"]:
            str.append("r_dummy3 r_master 0 1e9")
        if self.control["nsweep"]:
            str.append("eg_master1 0 n_master v_master 0 1")
        if self.control["rsweep"]:
            str.append(
                "eg_master2 r_master 0 vol='{stop}-v(v_master)+{start}'".format(
                    stop=stop, start=start
                )
            )

        if self.language == "spectre":
            analysis.append("vg_master (v_master 0) vsource dc=0 type=dc")
            analysis.append(
                "dc dc dev=vg_master param=dc start={start} stop={stop} step={step}".format(
                    start=start, stop=stop, step=step
                )
            )

        else:
            analysis.append("vg_master v_master 0 dc=0")
            analysis.append(
                ".dc vg_master {start} {stop} {step}".format(
                    start=start, stop=stop, step=step
                )
            )

        return ["\n".join(str), "\n".join(analysis)]

    def get_ac_analysis(self):
        freq = self.control["frequency"]
        s = None
        if self.language == "spectre":
            s = "ac ac values=[{freq}]".format(freq=(" ".join(map(str, freq))))
        else:
            if self.control["simulator"] == "titan":
                if len(freq) > 2:
                    raise "Devsim does not currently support > 2 frequencies when using titan"

                s = ".ac lin 2 {freq0} {freq_1}".format(
                    freq0=str(freq[0]), freq_1=str(freq[-1])
                )
            else:
                s = ".ac poi {freqSize} {freqJoin}".format(
                    freqSize=len(freq), freqJoin=" ".join(map(str, freq))
                )
        return [None, s]

    def get_tran_analysis(self):
        tprint = self.control["tprint"]
        tstop = self.control["tstop"]
        def_tprint = config["default"]["control"]["tprint"]
        def_tstop = config["default"]["control"]["tstop"]
        tprint = tprint or def_tprint
        tstop = tstop or def_tstop
        if self.language == "spectre":
            str = "tran tran stop={tstop}".format(tstop=tstop)
        else:
            str = ".tran {tprint} {tstop}".format(tprint=tprint, tstop=tstop)

        return [None, str]

    def parse_measures(self, parselist):
        data = {}
        for infile in parselist:
            if self.control["simulator"] == "titan":
                corner, m_type, params, values = self.read_measure_titan(infile)
            else:
                corner, m_type, params, values = self.read_measure_file(infile)
            for x in range(len(params)):
                data[params[x]] = data.get(params[x]) or dict()
                data[params[x]][corner] = data[params[x]].get(corner) or dict()
                data[params[x]][corner][m_type] = []
                for j in range(len(values)):
                    data[params[x]][corner][m_type].append(
                        self.check_fail(values[j][x])
                    )
        return data

        # if self.agemode:
        #     self.parse_aging_data(infile, data, params, corner) SMARTSOA STUFF

        # self.parse_asserts(infile, data, params, corner) SMARTSOA STUFF

    # def parse_asserts(self, infile, data, params, corner): SMARTSOA STUFF

    def check_fail(self, meas):
        try:
            return float(meas)
        except:
            return "fail"

    def get_control_statements(self, cor, mode):
        string = []
        simmode = self.control["mode"]
        if simmode:
            simmode = simmode.split()
            simmode = "_".join(simmode)

        if simmode == "normal" or simmode is None:
            supplies_and_dummies, analysis = self.get_analysis()
            string.append(supplies_and_dummies)
            if self.language == "spectre":
                string.append("simulator lang=spectre")

            string.append("\n".join(analysis))
        elif simmode:
            string.append(getattr(self, simmode)(cor, mode))
        else:
            raise "Mode {simmode} is not supported.".format(simmode=simmode)
        if self.language == "spectre":
            string.append("simulator lang=spice")
        return "\n".join(string) + "\n\n"

    def omi_aging(self, cor, mode):
        valid_simulators = ["eldo", "afs", "spectre", "aps", "xps"]
        self.check_valid_simulator(valid_simulators, "OMI")
        supplies_and_dummies, analysis = self.get_analysis()
        str = []
        if mode == "aged":
            cfg = open(self.rundir + "/{cor}_omi.cfg".format(cor=cor), "rw")
            cfg.write("** Configuration file for OMI")
            cfg.write("*")
            cfg.write("*1 for absolute file location to the cfg file")
            cfg.write("*0 for relative file location to the cfg file")
            cfg.write("*-1 for NULL")
            cfg.write(
                "age_data_file      0   ./#{cor}__stress.omiage0.dat".format(cor=cor)
            )
            cfg.write("age_model_file     -1   NULL")
            cfg.write("age_setting_file   -1   NULL")
            cfg.close()

            str.append(
                ".option omiinput={rundir}/#{cor}_omi.cfg".format(
                    rundir=self.rundir, cor=cor
                )
            )
            str.append(supplies_and_dummies)
            if self.language == "spectre":
                str.append("simulator lang=spectre")
            str.append("\n".join(analysis))
        elif mode == "stress":
            str.append(self.control["stress tran"])
        else:
            str.append(supplies_and_dummies)
            if self.language == "spectre":
                str.append("simulator lang = spectre")
            str.append("\n".join(analysis))
        return "\n".join(str)

    def tmi_aging(self, cor, mode):
        valid_simulators = ["eldo", "afs", "spectre", "aps", "xps", "titan"]
        self.check_valid_simulator(valid_simulators, "TMI")
        supplies_and_dummies, analysis = self.get_analysis
        str = []
        if mode == "aged":
            if self.control["simulator"] == "titan":
                tmiinput = "{rundir}/{cor}__stress.t1.tmiage0".format(
                    rundir=self.rundir, cor=cor
                )
            else:
                tmiinput = "{rundir}/{cor}__stress.tmiage0".format(
                    rundir=self.rundir, cor=cor
                )
            str.append(".option tmiinput=#{tmiinput}".format(tmiinput=tmiinput))
            str.append(supplies_and_dummies)
            if self.language == "spectre":
                str.append("simulator lang=spectre")
            str.append("\n".join(analysis))
        elif mode == "stress":
            str.append(self.control["stress tran"])
        else:
            str.append(supplies_and_dummies)
            if self.language == "spectre":
                str.append("simulator lang=spectre")
            str.append("\n".join(analysis))
        return "\n".join(str)

    def agemos_aging(self, cor, mode):
        valid_simulators = ["spectre", "aps"]
        self.check_valid_simulator(valid_simulators, "Agemos")
        supplies_and_dummies, analysis = self.get_analysis
        str = []
        if mode == "aged":
            dagetime = self.control["aged parameters"]["dagetime"]
            if not dagetime:
                raise "Must specify aged parameters:dagetime"
            str.append(supplies_and_dummies)
            str.append("simulator lang=spectre")
            str.append("rel reliability {")
            str.append("  age time={dagetime}y".format(dagetime=dagetime))
            str.append("  simmode type=aging")
            str.append("  simmode file={cor}__stress.bs0".format(cor=cor))
            for analy in analysis:
                str.append("  {analy}".format(analy=analy))
            str.append("}")
        elif mode == "stress":
            dagetime = self.control["stress parameters"]["dagetime"]
            if not dagetime:
                raise "Must specify stress parameters:dagetime"
            str.append("simulator lang=spectre")
            str.append("rel reliability {")
            str.append("  age time={dagetime}y".format(dagetime))
            str.append(" simmode type=stress")
            str.append("  deltad value=0.1")
            if not self.control["stress tran"]:
                raise "Must provide control: stress tran"
            str.append("  {control}".format(self.control["stress tran"]))
            str.append("}")
        else:
            str.append(supplies_and_dummies)
            str.append("simulator lang=spectre")
            for analy in analysis:
                str.append("  {analy}".format(analy=analy))
        return "\n".join(str)

    def montecarlo(self, cor, mode):
        mcargs = self.get_mc_args
        if mcargs["syntax"] == "spectre":
            str = self.montecarlo_spectre(mcargs["args"])
            return str
        if mcargs["syntax"] == "hspice":
            str = self.montecarlo_hspice(mcargs["args"])
            return str
        if mcargs["syntax"] == "titan":
            str = self.montecarlo_titan(mcargs["args"])
            return str

        raise "Syntax {mcargs} is not supported.".format(mcargs=mcargs["syntax"])

    def montecarlo_spectre(self, args):
        supplies_and_dummies, analysis = self.get_analysis()
        str = []
        str.append(supplies_and_dummies)
        str.append("simulator lang=spectre")
        for analy in analysis:
            analy = analy.split("\n")
            if len(analy) > 1:
                str.append("\n".join(analy[0:-2]))
            else:
                next
        str.append("mc1 montecarlo" + args + " {")

        for analy in analysis:
            analy = analy.split("\n")
            str.append("  {analyneg1}".format(analy1=analy[-1]))
        str.append("}")
        return "\n".join(str)

    def montecarlo_hspice(self, args):
        supplies_and_dummies, analysis = self.get_analysis()
        str = []
        str.append(supplies_and_dummies)
        str.append(
            map(lambda x: x, "\n".join(analysis).split("\n"))
        )  # Note: actually recreate the lambda for the map.
        return "\n".join(str)

    def montecarlo_titan(self, args):
        supplies_and_dummies, analysis = self.get_analysis
        str = []
        str.append(supplies_and_dummies)
        str.append("\n".join(analysis) + "\n.mc" + args)
        return "\n".join(str)

    def get_mc_args(self):
        if self.control["monte carlo"]:
            mcargs = self.control["monte carlo"]
        else:
            self.simulator = self.control["simulator"]
            mcargs = config["valid simulators"][self.simulator]["monte carlo"]
        return mcargs

    def check_valid_simulator(self, valid_simulators, message):
        self.simulator = self.control["simulator"]
        if self.simulator not in valid_simulators:
            raise "{message} is not supported with {simulator}".format(
                message=message, simulator=self.simulator
            )

    def read_measure_titan(self, infile):
        header_arr = []
        meas_arr = []
        measStatements = []
        with open(f"{self.rundir}/{infile}", mode='r') as f_in:
            lines = f_in.read()
        line = [num[0] + 1 for num in enumerate(re.findall("Measure Statement", lines))]
        [measStatements.append(num) for num in line]
        firstAlter = re.findall('Alteration Run', lines)
        if len(firstAlter) > 0 : 
            lastMeas = lines.index(firstAlter[0]) - 2
        else:
            lastMeas = -2
        numMeasures = lastMeas - measStatements[0]
        for meas in measStatements:
            row = []
            lastLine = meas+numMeasures-1 if lastMeas > 0 else -1
            for line in lines.split("\n")[meas:lastLine]:
                element = line.split('|')
                if len(element) > 1:
                    if meas == measStatements[0]:
                        header_arr.append(element[0].strip())
                    row.append(element[1].strip())
            meas_arr.append(row)
        if len(measStatements) > 1:
            type = 'montecarlo'
        else:
            type = 'nominal'
        corner = infile.split('.')[0]
        return [corner, type, header_arr, meas_arr]

    def read_measure_file(self, infile):
        header = True
        header_arr = []
        meas_arr = []
        start = subprocess.getoutput(
            f'grep -in "\.title" {self.rundir}/{infile}'
        ).split(":")[0]
        start = int(start)
        f = open(f"{self.rundir}/{infile}", "r")
        flines = f.readlines()
        for line in flines[start:]:
            element = line.rstrip().split()
            for ele in element:
                if header:
                    header_arr.append(ele)
                    if "alter#" == ele:
                        header = False
                else:
                    meas_arr.append(ele)
        meas_arr = list(grouper(meas_arr, len(header_arr)))

        corner = infile.split(".")[0]
        m_type = None
        if len(meas_arr) > 1:
            m_type = "montecarlo"
            endData = self.getNumMonteRuns() - 1
            meas_arr = meas_arr[
                0:endData
            ]  # Chop off bottom, some simulators add extra stuff
            if not (
                (len(header_arr) == len(meas_arr[0]))
                and (len(meas_arr[0]) == len(meas_arr[-1]))
            ):
                raise (ControllerError(f"Error parsing measures file {infile}"))
        elif "__aged" in corner:
            corner = re.sub("__aged", "", corner)
            m_type = "aged"
        else:
            m_type = "nominal"
        return [corner, m_type, header_arr, meas_arr]

    def getNumMonteRuns(self):
        mcargs = self.get_mc_args()
        if mcargs["syntax"] == "spectre":
            s = re.findall(r"numruns\s*=\s*\d+", mcargs["args"])[0].split("=")[-1]
        elif mcargs["syntax"] == "hspice":
            s = re.findall(r"monte\s*=\s*\d+", mcargs["args"])[0].split("=")[-1]
        else:
            raise ControllerError(
                "Syntax #{mcargs['syntax']} for getNumMonteRuns is not supported."
            )
        return int(s)
