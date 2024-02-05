"""
Created on Wed Jun 21 07:29:42 CDT 2023


@author: wellsjeremy
"""

from ifxpymdm import Mdm, Sweep
from ..logger import Logger
import os
import re
import ruamel.yaml
yaml=ruamel.yaml.YAML(typ='safe')
import socket
from ..metrics import MdmParser
from copy import copy, deepcopy
from ..utils import listfiles, is_number, get_site, to_number,scale_param


class MdmHelperError(Exception):
    pass


class MdmHelper:
    def __init__(self, techdata=dict()):
        self._mdm_paths = []
        self._mdms = []
        self.techdata = techdata
        self._mdm_filter = dict()
        self.update_device_map = False
        self._device_map = {}

    @property
    def mdm_paths(self):
        return self._mdm_paths

    @property
    def device_map(self):
        return self._device_map

    @property
    def mdms(self):
        return self._mdms

    def import_dir(self, path):
        logger = Logger()
        for file in listfiles(path, None, ".mdm"):
            if os.path.splitext(file)[1] == ".mdm":
                logger.info(f"Found {file}")
                self.mdm_paths.append(file)

    def create_mdms(self):
        for path in self.mdm_paths:
            mdm = Mdm(path)
            check = f"{mdm.iccap_values['devtechno']}_{mdm.iccap_values['devpolarity']}".lower()
            if self._device_map.get(check):
                setattr(mdm, "devsim", self._device_map[check])
            else:
                setattr(mdm, "devsim", dict(device_type="unknown", model="unknown"))
            self.mdms.append(mdm)

    def write_meas_list(self, fout):
        for mdm in self.mdms:
            mdm: Mdm
            outputs = mdm.iccap_outputs
            ordered_sweeps = sorted(
                [s for s in mdm.sweeps if "sweep_order" in s.type_options.keys()],
                key=lambda s: s.type_options["sweep_order"],
            )

            for output in outputs:
                x_axis = mdm.first_order_sweep.name
                s = f"login.{get_site()} {mdm.fname} x={x_axis} y={output}"
                if len(ordered_sweeps) > 1:
                    s += f" p={ordered_sweeps[1].name}"
                if len(ordered_sweeps) > 2:
                    for sw in ordered_sweeps[2:]:
                        for val in sw.values:
                            temp_s = copy(s)
                            temp_s += f" {sw.name}={val}"
                            for con_sw in mdm.sweeps:
                                if con_sw.name in map(lambda q: q.name, ordered_sweeps):
                                    continue
                                temp_s += f" {con_sw.name}={con_sw.values[0]}"
                            temp_s = self._append_mdm_params(temp_s, mdm)
                            fout.write(temp_s + "\n")
                else:
                    for con_sw in mdm.sweeps:
                        if con_sw.name in map(lambda q: q.name, ordered_sweeps):
                            continue
                        s += f" {con_sw.name}={con_sw.values[0]}"
                    s = self._append_mdm_params(s, mdm)
                    fout.write(s + "\n")

            # for x in ('vd', 'vg', 'vs', 'vb'):

    def _append_mdm_params(self, s, mdm):
        x_axis = mdm.first_order_sweep.name
        skip = [
            "fname",
            "operator",
            "devtechno",
            "date",
            "version",
            "bench",
            "dielist",
            "block",
            "meascond",
            "device",
            "type",
            "lot",
            "routine",
        ]
        for x in reversed(mdm.iccap_values.keys()):
            if "data" in x:
                continue
            if x[0] == "_":
                continue
            if x in skip:
                continue
            if x != x_axis:
                if is_number(mdm.iccap_values[x]):
                    s += f" {x}={mdm.iccap_values[x]:.5g}"
                else:
                    s += f" {x}={mdm.iccap_values[x]}"
        return s

    def handle_meas_list_line(self, site, path, *rest):
        self._loaded = getattr(self, "_loaded", [])
        if get_site() != site.split(".")[1]:
            if not os.path.exists(path):
                raise MdmHelperError(
                    f"MDM file {path} does not exist at {get_site()}, please check {site}"
                )
            else:
                if path not in self._loaded:
                    mdm = Mdm(path)
                    check = f"{mdm.iccap_values['devtechno']}_{mdm.iccap_values['devpolarity']}".lower()
                    if self._device_map[check]:
                        setattr(mdm, "devsim", self._device_map[check])
                    else:
                        setattr(
                            mdm, "devsim", dict(device_type="unknown", model="unknown"),
                        )

                    self.mdms.append(mdm)
                    self._loaded.append(path)
                self._mdm_filter[path] = self._mdm_filter.get(path) or []
                self._mdm_filter[path].append(self.filter_dict_from_line(rest))
        else:
            if os.path.exists(path):
                if path not in self._loaded:
                    mdm = Mdm(path)
                    check = f"{mdm.iccap_values['devtechno']}_{mdm.iccap_values['devpolarity']}".lower()
                    if self._device_map.get(check):
                        setattr(mdm, "devsim", self._device_map[check])
                    else:
                        setattr(
                            mdm, "devsim", dict(device_type="unknown", model="unknown"),
                        )
                    self.mdms.append(mdm)
                    self._loaded.append(path)
                self._mdm_filter[path] = self._mdm_filter.get(path) or []
                self._mdm_filter[path].append(self.filter_dict_from_line(rest))
                self._loaded.append(path)

    def filter_dict_from_line(self, eq_list):
        def split_to_number(s):
            z, x = s.strip().split("=")
            return [z, to_number(x)]

        split_map = map(split_to_number, eq_list)
        split_dict = dict(split_map)
        if "p" in split_dict:
            del split_dict["p"]
        return split_dict

    def check_filter(self, mdm_dict, subset):
        return (
            subset.items()
            <= dict(
                map(
                    lambda q: [q[0], float(f"{q[1]:.5g}")] if is_number(q[1]) else q,
                    mdm_dict.items(),
                )
            ).items()
        )

    def get_device(self, md):
        logger = Logger()
        check = f"{md['devtechno']}_{md['devpolarity']}".lower()
        if check in self._device_map.keys():
            return self._device_map[check]["model"]
        else:
            return "unknown"

    def get_device_model_type(self, md):
        logger = Logger()
        check = f"{md['devtechno']}_{md['devpolarity']}".lower()
        if check in self._device_map.keys():
            return self._device_map[check]["device_type"]
        else:
            self.update_device_map = True
        if "mos" in check:
            self._device_map[check] = dict(
                device_type=md["devpolarity"].lower() + "mos", model="mosfet"
            )
            return md["devpolarity"].lower() + "mos"
        elif "res" in check:
            self._device_map[check] = dict(device_type="res", model="res")
            return "res"
        elif "cap" in check:
            self._device_map[check] = dict(device_type="cap", model="cap")
            return "cap"
        elif "npn" in check:
            self._device_map[check] = dict(device_type="npn", model="npn")
            return "npn"
        elif "pnp" in check:
            self._device_map[check] = dict(device_type="pnp", model="pnp")
            return "pnp"
        else:
            logger.warning(
                f"Could not determine guess of device_type for {md['fname']}\nUpdate the device_type and model and re-run."
            )
            self._device_map[check] = dict(device_type=check, model=check)
            return check

    def append_mdm_dict(self, top, md, mdm):
        test_fname = os.path.basename(re.sub(r"-(\d)", r"n\1", md["fname"]))
        test_name = f"{test_fname}_{md['y']}"
        ordered_sweeps = sorted(
            [sweep for sweep in mdm.sweeps if sweep.type in ["lin", "log", "list"]],
            key=lambda sweep: sweep.type_options["sweep_order"],
        )
        top[test_name] = top.get(test_name) or dict()
        first_order_sweep = mdm.first_order_sweep
        sub = top[test_name]
        sub["definitions"] = sub.get("definitions") or dict()
        sub["instance parameters"] = sub.get("instance parameters") or dict()
        sub["stimuli"] = sub.get("stimuli") or dict()
        sub["control"] = sub.get("control") or dict()
        sub["sweep"] = sub.get("sweep") or dict()
        for sweep in ordered_sweeps:
            sweep: Sweep
            options = sweep.type_options
            if sweep.type in ["lin", "log"]:
                sub["stimuli"][sweep.name] = dict(
                    start=options["start"],
                    stop=options["stop"],
                    step=options["step_size"],
                    type=sweep.type,
                )
            else:
                sub["stimuli"][sweep.name] = dict(type="list", list=sweep.values)
            sub["sweep"][options["sweep_order"]] = sweep.name
        # sub['stimuli'][first_order_sweep.name] = dict(
        #    start = first_order_sweep.type_options['start'],
        #    stop = first_order_sweep.type_options['stop'],
        #    step = first_order_sweep.type_options['step_size']
        # )
        sub["definitions"]["device_type"] = self.get_device_model_type(md)
        sub["device"] = self.get_device(md)
        key = f"{md['devtechno']}_{md['devpolarity']}".lower()
        sub["definitions"]["model"] = self._device_map[key]["model"]
        sub["definitions"]["analysis_type"] = f"{md['y']}sweep"
        in_spice_params = False
        in_bias_params = False
        for k in md.keys():
            if k == "___spice_instance":
                in_spice_params = True
                in_bias_params = False
                continue
            if k == "___calibration":
                in_spice_params = False
                in_bias_params = True
                continue
            if k[0:3] == "___":
                in_spice_params = False
                in_bias_params = False
                continue
            if in_bias_params and "data" in k:
                in_bias_params = False
                continue
            if not in_spice_params and not in_bias_params:
                continue
            if in_spice_params:
                sub["instance parameters"][k] = scale_param(k,md[k])
            if in_bias_params and k not in sub["stimuli"]:
                sub["stimuli"][k] = md[k]
        sub["control"]["temperature"] = md["temperature"]
        title = f"{sub['device']} {md['y']}-{md['x']}"
        for inst, val in sub["instance parameters"].items():
            title += f" {inst} = {val:.3g}"
        for bias, val in sub["stimuli"].items():
            if not isinstance(val, dict):
                title += f" {bias}={val}"

        sub["views"] = sub.get("views") or dict()
        sub["views"][test_name] = sub["views"].get(test_name) or dict()
        vsub = sub["views"][test_name]
        vsub["type"] = "texgraph"
        vsub["config"] = dict(
            title=title,
            xlabel=md["x"].upper(),
            ylabel=md["y"].upper(),
            corner_specific=dict(
                measure={
                    "only marks": True,
                    "thin": True,
                    "mark": "o",
                    "mark size": "1pt",
                },
                default={"no markers": True, "thin": True, "solid": True,},
            ),
        )
        if self.techdata["techdata"].get("measure_corner"):
            vsub["config"]["measure_corner"] = self.techdata["techdata"][
                "measure_corner"
            ]

        if self.is_common_log_candidate(md):
            sub["views"][f"{test_name}_log"] = deepcopy(sub["views"][test_name])
            sub["views"][f"{test_name}_log"]["config"]["axis"] = "semilogyaxis"
        sub["simulations"] = sub.get("simulations") or dict(measure=dict(sweep=[]))
        sweep_arr = sub["simulations"]["measure"]["sweep"]
        p = None
        if len(ordered_sweeps) > 1:
            p = md[ordered_sweeps[1].name]

        for x, y in zip(md["data_x"], md["data_y"]):
            sweep_arr.append([float(x), p, float(y)])

    def is_common_log_candidate(self, md):
        if md["y"] == "id" and md["x"] == "vg":
            return True
        return False

    def gen_iv_dsi_file(self):
        out = {}
        for mdm in self.mdms:
            for i, md in enumerate(mdm.to_dicts()):
                if len(self._mdm_filter) > 0 and md["fname"] in self._mdm_filter.keys():
                    skip = True
                    for test_dict in self._mdm_filter[md["fname"]]:
                        if self.check_filter(md, test_dict):
                            skip = False
                    if skip:
                        continue
                self.append_mdm_dict(out, md, mdm)
        return out

    def gen_metric_dsi_file(self):
        parser = MdmParser(self.mdms, self.techdata)
        parser.parse_all_metrics()
        out = dict()
        for metric in parser.metrics:
            out[f"{metric.metric}_{metric.fname}"] = metric.to_dsi()
        return out
