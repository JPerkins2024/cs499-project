import ruamel.yaml
yaml=ruamel.yaml.YAML(typ='safe')
from .measures import MeasuresMixin
from .config_loader import config
import re
from copy import deepcopy, copy
from .merge import deep_merge
import os
import numpy as np
from .calculator import resolve_expressions
from pint import Quantity
from .utils import expand_generic_sweep
from .logger import Logger


class ParameterError(Exception):
    pass


class Parameter(MeasuresMixin):
    def __init__(self, conf=None, techdata=None, param_h=None, param=None):
        if param is not None:
            self.name = re.sub(".*?__", "", param, count=1)

        self.config = config
        self.techdata = techdata

        if param_h is not None:
            self.device = param_h.get("device")
            self.measure_name = param_h["measure name"].lower()
            self.param_data = self.tech_compile(param_h)
        self.set_required_defaults()
        self.param_data = self.calculator(self.param_data)

        self.type = "dc"
        self.unit = None
        self.netlistStr = self.netlist(1)

    def netlist(self, par=None, analysis=None):
        self.param_data["simulations"] = self.param_data.get("simulations") or {}
        ports = self.get_defs(["ports"]).split()
        analysis = self.param_data["definitions"]["analysis_type"]
        measVars = []
        if callable(getattr(self, analysis, None)):
            string = getattr(self, analysis)(ports, par)
        else:
            analysis = self.find_analysis_func(analysis)
            func = analysis[0]
            string = getattr(self, func)(analysis, ports, par)
        if type(string) == list:
            measVars.append(string[1])
            string = string[0]

        self.param_data["definitions"]["unit conversion"] = self.unit_conversion()
        string = string + "\n"
        simulator = self.param_data["control"]["simulator"]
        if simulator == "titan":
            return self.to_titan(string, measVars)
        return string

    def find_analysis_func(self, analysis):
        mismatch = re.compile(r"mm$")
        matches = mismatch.match(analysis)

        if matches is not None:
            func = mismatch
            if analysis[-1] == "_":
                analysis = analysis[0:-2]
            else:
                analysis = analysis[0:-3]

        simple_ac = [
            re.compile(r"^c"),
            re.compile(r"^q"),
            re.compile(r"^rs_"),
            re.compile(r"^rp_"),
            re.compile(r"^l"),
            re.compile(r"^y"),
        ]
        matches = []
        sweep = False
        if "sweep" in analysis:
            sweep = True
            analysis = re.sub("sweep", "", analysis)
        for regex in simple_ac:
            matches.append(re.finditer(regex, analysis))

        for one in matches:
            for two in one:
                if two.group() is not None:
                    x = two.group()
                    func = "simple_ac"

        simple_current = re.compile(r"^i")
        matches = simple_current.match(analysis)
        if matches is not None:
            func = "simple_current"

        dcres = re.compile(r"^r")
        matches = dcres.match(analysis)
        if matches is not None:
            func = "dcres"

        simple_voltage = re.compile(r"^v")
        matches = simple_voltage.match(analysis)
        if matches is not None:
            func = "simple_voltage"

        simple_tran = re.compile(r"t[vi]")
        matches = simple_tran.match(analysis)
        if matches is not None:
            func = "simple_tran"
        # Call explicit sweep function if available, otherwise keep analysissweep type
        if sweep and getattr(self, func + "_sweep", False):
            func += "_sweep"
        elif sweep:
            analysis += "sweep"

        return [func, analysis]

    def set_required_defaults(self):
        defaults = config.get("initialize", {})
        for category in defaults.keys():
            self.param_data[category] = self.param_data.get(category) or {}
            for ctrl in defaults[category].keys():
                self.param_data[category][ctrl] = (
                    self.param_data[category].get(ctrl) or defaults[category][ctrl]
                )

        self.param_data["definitions"]["reverse sweep"] = self.get_defs(
            ["reverse sweep"]
        )
        self.param_data["control"]["load balancer"] = self.get_load_balancer()
        self.param_data["control"]["language"] = self.get_language()

    def get_load_balancer(self):
        simulator = self.param_data["control"]["simulator"]
        simulator_specific = (
            config.get("valid simulators", {})
            .get(simulator, {})
            .get("load balancer", False)
        )
        default = (
            config.get("default", {}).get("control", {}).get("load balancer", False)
        )
        if self.param_data["control"].get("load balancer"):
            load_balancer = self.param_data["control"]["load balancer"]
        elif simulator_specific:
            load_balancer = simulator_specific
        else:
            load_balancer = default
        return load_balancer

    def get_language(self):
        simulator = self.param_data["control"]["simulator"]
        language = self.param_data.get("control", {}).get("language", False)
        language = language or config["valid simulators"].get(simulator, {}).get(
            "language"
        )
        language = language or "spice"
        return language

    def add_rundir(self, rundir):
        self.param_data["control"]["rundir"] = rundir

    def add_simulations(self, corner, in_vals, s_type):
        self.param_data["simulations"] = self.param_data.get("simulations") or {}
        self.param_data["simulations"][corner] = (
            self.param_data["simulations"].get(corner) or {}
        )
        logger = Logger()
        noconvert = config["units"].get("noconvert") or []
        vals = []
        if s_type == "sweep":
            for pointset in in_vals:
                x, p, val = pointset
                try:
                    act_val = (
                        float(val) * self.param_data["definitions"]["unit conversion"]
                    )
                except ValueError:
                    if val == "fail":
                        logger.error(f"Measure failed for {self.measure_name}")
                    else: 
                        logger.error(f"Unit conversion failed for {self.measure_name}")
                    act_val = val

                vals.append([x, p, act_val])
        else:
            for val in in_vals:
                try:
                    if s_type in noconvert:
                        vals.append(float(val))
                    else:
                        vals.append(
                            float(val)
                            * self.param_data["definitions"]["unit conversion"]
                        )
                except ValueError:
                    if val == "fail":
                        logger.error(f"Measure failed for {self.measure_name}")
                    else: 
                        logger.error(f"Unit conversion failed for {self.measure_name}")
                    vals.append(val)
        if s_type == "montecarlo":
            self.param_data["simulations"][corner]["nominal"] = vals[0]
            vals.pop()
            mean = np.mean(vals)
            median = np.median(vals)
            stdDev = np.std(vals)
            self.param_data["simulations"][corner]["mean"] = mean
            self.param_data["simulations"][corner]["median"] = median
            self.param_data["simulations"][corner]["sigma"] = stdDev

        elif s_type == "aged":
            self.param_data["simulations"][corner][s_type] = vals[0]
            self.postprocess_aging(corner)

        elif s_type == "asserts":
            self.param_data["simulations"][corner][s_type] = vals[0]
        elif s_type == "sweep":
            self.param_data["simulations"][corner][s_type] = vals
        else:
            self.param_data["simulations"][corner][s_type] = vals[0]

    def merge_extra_hashes(self):
        regex = []

    def convert_numerator(self, val):
        ref = self.unit.split("/")[0]
        if val == ref:
            return 1.0
        val = val[0] + "m"
        mult = float(Quantity("m").m_as(val))
        return mult

    def convert_denominator(self, val):
        try:
            if val == self.unit.split("/")[1]:
                return 1.0
        except:
            pass

        if val[-3:] == "m^2" and len(val) >= 3:
            if len(val) > 4:
                raise KeyError(
                    "Unit conversion error for {name}".format(name=self.name)
                )
            scale_1 = self.param_data["definitions"]["scale_area"]
            scale_2 = float(Quantity("m^2").m_as(val))
            if scale_1 is None:
                raise KeyError(
                    "Unit conversion error for {name}, area not defined".format(
                        name=self.name
                    )
                )
        elif val == "sq" or val == "square":
            scale_1 = self.param_data["definitions"]["square"]
            scale_2 = 1.0
            if scale_1 is None:
                raise KeyError(
                    "Unit conversion error for {name}".format(name=self.name)
                )

        elif val[-1] == "m":
            scale_1 = self.param_data["definitions"]["scale_w_perim"]
            scale_2 = float(Quantity("m").m_as(val))
        else:
            raise KeyError("Unit conversion error for {name}.".format(name=self.name))
        mult = float(scale_1) * scale_2
        if mult == 0:
            raise ZeroDivisionError("Denominator of 0")
        return mult

    def unit_conversion(self):
        if self.param_data["definitions"].get("units"):
            units = self.param_data["definitions"]["units"].lower()
            if units == "%":
                mult = 1
            elif self.unit:
                if (
                    r"/" in self.unit
                    and self.unit != self.param_data["definitions"]["units"]
                ):
                    raise KeyError(
                        "Unit conversion error for {name}".format(name=self.name)
                    )
                else:
                    convert = units.split("/")
                    if len(convert) == 1:
                        mult = self.convert_numerator(convert[0])
                    elif len(convert) == 2:
                        numerator = self.convert_numerator(convert[0])
                        denominator = self.convert_denominator(convert[1])
                        mult = numerator / denominator
                    else:
                        raise KeyError(
                            "Unit conversion for {name}".format(name=self.name)
                        )
            else:
                self.param_data["definitions"]["units"] = None
                mult = 1
        elif self.unit:
            self.param_data["definitions"]["units"] = self.unit
            mult = 1
        else:
            self.param_data["definitions"]["units"] = None
            mult = 1
        return float(mult)

    def get_defs(self, definitions, force=True):
        logger=  Logger()
        device_type = self.param_data["definitions"].get("device_type")
        if not device_type:
            logger.fatal(f"device_type not defined for {self.name}\n{self.param_data['definitions']}")
        val_devtype = config["netlist"][device_type]
        val_conf = config["default"]["definitions"]
        defs = []
        val = None
        for definition in definitions:
            if val_devtype:
                val_devtype_def = val_devtype.get(definition, None)
            val_conf_def = val_conf.get(definition, None)
            val_par_def = self.param_data["definitions"].get(definition, None)

            if val_par_def is not None:
                val = val_par_def
            elif val_devtype_def is not None:
                val = val_devtype_def
            elif val_conf_def is not None:
                val = val_conf_def

            if val is None and force is True:
                raise KeyError(
                    "{measure_name} requires {definition} to be defined.".format(
                        measure_name=self.measure_name, definition=definition
                    )
                )
            defs.append(val)
        if len(defs) == 1:
            return defs[0]
        else:
            return defs

    def tech_compile(self, param_h):
        param_h = self.find_tech_info(param_h)
        if not param_h.get("control",{}).get("corners"):
            raise Exception(f"No corners specified for {self.name}")

        param_h["control"]["corners"] = self.expand_corners(
            param_h["control"]["corners"]
        )
        param_h = deep_merge(param_h, (self.expand_metric(param_h)))
        return param_h

    def find_tech_info(self, param_h):
        try:
            if self.techdata[self.device]:
                for each in [
                    "definitions",
                    "stimuli",
                    "stress stimuli",
                    "control",
                    "instance parameters" "ic" "stress ic",
                ]:
                    self.techdata[self.device][each] = (
                        self.techdata[self.device].get(each) or {}
                    )
        except:
            return param_h
        for category in ["definitions", "stimuli"]:
            tech_def = deepcopy(
                self.techdata[self.device][category]
            )  # when techdata is None, this breaks
            input_def = param_h.get(category, {})
            inputdefBackup = deepcopy(input_def)
            if tech_def and input_def:
                defs_h = deep_merge(tech_def, input_def)
            elif tech_def:
                defs_h = tech_def
            elif input_def:
                defs_h = input_def
            else:
                param_h[category] = None
        return param_h

    def change_polarity(val):
        if val[0][0] == "-":
            val = val[1:-1]
        else:
            "-" + val
        return val

    def calculator(self, param_h):
        new_h = resolve_expressions(param_h, self.techdata)
        return new_h

        # Note: This entire module requires Dentaku (or something)

    def expand_corners(self, corner):
        try:
            if self.techdata.get('techdata',{}).get("corners", False) and self.techdata['techdata']["corners"].get(
                corner, False
            ):
                corners = re.sub(";", ",", self.techdata['techdata']["corners"][corner])
            else:
                corners = corner
        except:
            return corner
        return corners

    def expand_metric(self, param_h):
        metric = param_h.get("metrics")
        if not metric:
            return param_h
        if type(metric) != str:
            raise TypeError("Auto-expansion isn't working correctly.")
        if not self.techdata:
            return param_h
        if not self.techdata["metrics"].get(metric, False):
            raise KeyError(
                "Metric {metric} is not defined in the techfile".format(metric=metric)
            )

        metric_conditions_hash = deepcopy(self.techdata["metrics"][metric])
        noskip = ["instance parameters", "definitions", "stimuli","control"]
        for category in metric_conditions_hash:
            if category not in noskip:
                continue
            stim_h = metric_conditions_hash[category]

            if param_h.get(category):
                param_h[category] = deep_merge(param_h[category], stim_h)
            else:
                param_h[category] = stim_h
        return param_h

    def check_prereqs(self, ports, required_ports):
        for a in required_ports:
            if a not in ports:
                raise KeyError("Missing required ports.")

    def param_check(self):
        check_h = {}
        check_h["device"] = []
        check_h["definitions"] = ["device_type", "analysis_type"]
        check_h["control"] = [
            "models path",
            "simulator",
            "corners",
            "temperature",
            "load balancer",
            "step size",
        ]

        for key in check_h.keys():
            if key not in self.param_data:
                raise "{name}: Must define {key}"
            for arr in check_h[key].keys():
                if not self.param_data[key][arr]:
                    raise "{name}: Must define {key}:{arr} for {device}".format(
                        name=self.name, key=key, arr=arr, device=self.device
                    )
        return

    def get_sweep_supply(self, k):
        vmin, vmax, reverse_sweep = self.get_defs(["vmin", "vmax", "reverse sweep"])
        if reverse_sweep:
            txt = "max"
            mult = "-1*"
            string = "eg_{k} g_{k} 0 vol='min({mult}{vmin},max({mult}{vmax},v(n_master)))' ".format(
                k=k, mult=mult, vmin=vmin, vmax=vmax
            )
        else:
            txt = "min"
            mult = ""
            string = "eg_{k} g_{k} 0 vol='min({vmax},max({vmin},v(v_master)))' ".format(
                k=k, mult=mult, vmin=vmin, vmax=vmax
            )
        return [string, txt, mult]

    def get_instance_and_stimuli(self, k, ports, ac_ports, stress="", custom_bias=None):
        arr = []
        arr.append(self.get_instance_line(k, ports))
        arr.append(self.get_stimuli(k, ports, ac_ports, stress, custom_bias))
        arr = "\n".join(arr)
        return arr

    def get_instance_line(self, k, ports):
        string = []
        inst = self.get_defs(["instance"])
        string.append("{inst}_{k}".format(inst=inst, k=k))
        for port in ports:
            string.append("{port}_{k}".format(port=port, k=k))
        string.append(self.get_defs(["model"], False) or self.device)

        if self.get_defs(["_no_instance_line"], False):
            return " ".join(string)
        for param in self.param_data["instance parameters"]:
            string.append(
                "{param}={val}".format(
                    param=param, val=self.param_data["instance parameters"][param]
                )
            )
        # Todo: keep string an appropriate len
        return " ".join(string)

    def get_sweep_supply_from_dict(self, sweep, node, k):
        reverse_sweep = self.get_defs(["reverse_sweep"], False)
        vmin = min(sweep["start"], sweep["stop"])
        vmax = max(sweep["start"], sweep["stop"])
        if reverse_sweep:
            mult = "-1*"
            string = f"e{node}_{k} {node}_{k} 0 vol='min({mult}{vmin},max({mult}{vmax},v(n_master)))' "
        else:
            mult = ""
            string = (
                f"e{node}_{k} {node}_{k} 0 vol='min({vmax},max({vmin},v(v_master)))' "
            )
        return string

    def get_sweep_vmin(self):
        sweep = self.param_data["stimuli"][self.param_data["sweep"][1]]
        vmin = min(sweep["start"], sweep["stop"])
        return vmin

    def get_sweep_vmax(self):
        sweep = self.param_data["stimuli"][self.param_data["sweep"][1]]
        vmax = max(sweep["start"], sweep["stop"])
        return vmax

    def get_sweep(self, order: int):
        """
        Searches valid places for a sweep variable.
        Sweeps are defined in a dictionary where the key is the sweep order and the value is the variable.
        The variable can either be in stimuli or in instance parameters or control.

        Args:
            order (int): Sweep order

        Raises:
            ParameterError: If sweep variable can't be found

        Returns: sweep dictionary or already expanded sweep variable.

        """
        sweep_var = self.param_data["sweep"][order]
        to_check = ["stimuli", "instance parameters", "control"]
        for check in to_check:
            if self.param_data.get(check) and sweep_var in self.param_data[check]:
                return self.param_data.get(check)[sweep_var]
        raise (ParameterError(f"Unable to get sweep for {order}"))

    def find_sweep(self, order):
        sweep_var = self.param_data["sweep"][order]
        to_check = ["stimuli", "instance parameters"]
        for check in to_check:
            if (
                self.param_data.get(check)
                and sweep_var in self.param_data[check]
                and isinstance(self.param_data[check][sweep_var], dict)
            ):
                return check

    def get_stimuli(self, k, ports, ac_ports, stress="", custom_bias=None):
        string = []
        for port in ports:
            stimulus = self.find_port_stimulus(port, stress)
            ic = self.find_port_ic(port, stress)
            self.param_data[f"{stress}stimuli"] = (
                self.param_data.get(f"{stress}stimuli") or dict()
            )
            self.param_data[f"{stress}ic"] = (
                self.param_data.get(f"{stress}ic") or dict()
            )
            if custom_bias:
                stim_dict = custom_bias
            else:
                stim_dict = self.param_data[
                    "{stress}stimuli".format(
                        stress=stress if stress is not None else ""
                    )
                ]
            if stimulus:
                if isinstance(stim_dict[stimulus], dict):
                    sweep_dict = stim_dict[stimulus]
                    temp_str = self.get_sweep_supply_from_dict(sweep_dict, port, k)
                else:
                    supply = str(stim_dict[stimulus]).split()
                    while None in supply:
                        supply.remove(None)
                    for arr in supply:
                        if arr[0][0] == "/":
                            arr = arr[1:] + "_{k}".format(k=k)
                        else:
                            arr
                    temp_str = "{stimulus}_{k} {port}_{k} 0 {supp}".format(
                        stimulus=stimulus, k=k, port=port, supp=" ".join(supply)
                    )
            elif ic:
                supply = str(self.param_data["{stress}ic".format(ic=ic)][ic]).split()
                while None in supply:
                    supply.remove(None)
                for arr in supply:
                    if arr[0][0] == "/":
                        arr = arr[1:] + "_{k}".format(k=k)
                    else:
                        arr
                temp_str = self.get_ic(k, port, supply)
                string.append(temp_str)
            else:
                # Need to not netlist 0V sources.
                if not self.param_data["definitions"].get("floating_stimuli", False):
                    stimulus = "v{port}".format(port=port)
                    temp_str = "{stimulus}_{k} {port}_{k}".format(
                        k=k, stimulus=stimulus, port=port
                    )
                    self.param_data["{stress}stimuli".format(stress=stress)][
                        stimulus
                    ] = 0
            if port in ac_ports:
                temp_str += " ac 1"
            string.append(temp_str)
        if len(string) != len(ports):
            raise Exception("Error generating stimuli")
        return "\n".join(string)

    def find_port_stimulus(self, node, stress=""):
        stimulus = None
        if self.param_data[
            "{stress}stimuli".format(stress=stress if stress is not None else "")
        ]:
            for stim in self.param_data[
                "{stress}stimuli".format(stress=stress if stress is not None else "")
            ]:
                if node == stim[1:]:
                    stimulus = stim
                    break
        return stimulus

    def find_port_ic(self, node, stress=""):
        ic = None
        if self.param_data.get(
            "{stress}ic".format(stress=stress if stress is not None else "")
        ):
            for stim in self.param_data.get(
                "{stress}ic".format(stress=stress if stress is not None else "")
            ):
                if node == stim[1:]:
                    ic = stim
                    break
        return ic

    def unpack_analysis(self, analysis_type, dev_ports):
        if analysis_type[1][0] in ["s", "p"] and analysis_type[0][0] in ["r", "l", "c"]:
            analysis = analysis_type[0][0:1]
            ports = analysis_type[1][2:]
        elif analysis_type[1][0] in ["r", "i"] and "y" in analysis_type[0][0]:
            analysis = analysis_type[0][0:1]
            ports = analysis_type[1][2:]
        else:
            analysis = analysis_type[0]
            ports = analysis_type[1][1:]
            ports = ports.split("_")
            if len(ports) < 2:
                ports = list(analysis_type[1][1:])
        while None in ports:
            ports.remove(None)
        if type(dev_ports) == str:
            dev_ports = dev_ports.split()
        dev_ports = sorted(
            dev_ports, key=lambda x: len(x), reverse=True
        )  # note to sort by size

        if len(ports) > 2:
            raise LookupError(
                "Unknown analysis type: {analysis}".format(analysis=analysis_type)
            )
        single_analysis = False
        if len(ports) == 1:
            ports = [ports[0], ports[0]]
            single_analysis = True

        out_ports = [[], []]
        i = 0
        for port in ports:
            port = copy(port)
            one_port_found = False
            count = 0
            sanity_count = 0
            while len(port) != 0:
                found_ports = 0
                start = 0
                fin = len(dev_ports[0]) - 1
                if count > 0 and not one_port_found:
                    raise ParameterError(
                        "Unable to find {port} in {analysis_type}".format(
                            port=port, analysis_type=analysis_type[1]
                        )
                    )
                if sanity_count > 100:
                    raise ParameterError(
                        f"Unable to map {port} in {analysis_type[1]} to device port"
                    )
                for p in dev_ports:
                    if len(port) == 0:
                        break
                    if len(p) > len(port):
                        continue
                    fin = len(p) - 1
                    if start == fin:
                        fin = fin + 1
                    if port[start:fin] == p:
                        found_ports += 1
                        out_ports[i].append(port[start:fin])
                        port = port[fin:]
                        one_port_found = True
                sanity_count += 1
            count = 1 + count
            i = i + 1
        ports1, ports2 = out_ports
        if single_analysis == True:
            if len(ports1) > 2 or len(ports2) > 2:
                raise "Unknown Analysis {analysis_type}".format(
                    analysis_type=analysis_type
                )
            ports1 = [ports1[0]]
            ports2 = [ports2[-1]]

        return [analysis, ports1, ports2]
