#! /usr/bin/env python
"""
Created on Tue Oct 24 14:35:04 CDT 2023


@author: wellsjeremy
"""

import os
from ..logger import Logger
import re
import ruamel.yaml
yaml=ruamel.yaml.YAML()
import socket
from copy import copy, deepcopy
#from ifxpyproplusdat import ProPlusDat as Dat
from ..utils import listfiles, is_number, get_site, to_number, make_sweep_dict,scale_param
import fnmatch
from ..metrics import DatParser


class DatHelperError(Exception):
    pass


class DatHelper:
    def __init__(self, techdata):
        self.techdata = techdata
        self._dat_paths = []
        self._dats = []
        self._dat_filter = dict()
        self.update_device_map = False
        self._device_map = {}

    @property
    def dat_paths(self):
        return self._dat_paths

    @property
    def device_map(self):
        return self._device_map

    @property
    def dats(self):
        return self._dats

    def import_dir(self, path):
        logger = Logger()
        for file in listfiles(path, None, ".dat"):
            if os.path.splitext(file)[1] == ".dat":
                logger.info(f"Found {file}")
                self.dat_paths.append(file)

    def create_datfiles(self):
        logger = Logger()
        for path in self.dat_paths:
            dat = Dat(path)
            for md in dat.to_dicts():
                self.get_device_model_type(md)
                break
            self.dats.append(dat)

    def is_common_log_candidate(self, page):
        if page["y"] == "id" and page["x"] == "vg":
            return True
        return False

    def write_meas_list(self, fout):
        for dat in self.dats:
            for sweep in dat.get_sweeps():
                s = f"login.{get_site()} {dat.fname} "
                for param, val in reversed(sweep.items()):
                    if isinstance(val, dict):
                        s += " " + f"{param}={val}".replace(" ", "")
                    else:
                        s += f" {param}={val}"
                s += "\n"
                fout.write(s)

    def handle_meas_list_line(self, site, path, *rest):
        self._loaded = getattr(self, "_loaded", [])
        if get_site() != site.split(".")[1]:
            if not os.path.exists(path):
                raise DatHelperError(
                    f"Dat file {path} does not exist at {get_site()}, please check {site}"
                )
        else:
            if path not in self._loaded:
                dat = Dat(path)
                if devsim_dict := self.match_file_name_in_map(dat.fname):
                    setattr(dat, "devsim", devsim_dict)
                else:
                    setattr(
                        dat, "devsim", dict(device_type="unknown", model="unknown"),
                    )

                self.dats.append(dat)
                self._loaded.append(path)
            self._dat_filter[path] = self._dat_filter.get(path) or []
            self._dat_filter[path].append(self.filter_dict_from_line(rest))

    def filter_dict_from_line(self, eq_list):
        def split_to_number_or_dict(s):
            z, x = s.strip().split("=")
            if x[0] == "{" and x[-1] == "}":
                tmp = dict()
                for item in x[1:-1].split(","):
                    par, val = item.split(":")
                    tmp[par] = to_number(val)
                return [z, tmp]
            else:
                return [z, to_number(x)]

        split_map = map(split_to_number_or_dict, filter(lambda x: len(x) > 0, eq_list))
        split_dict = dict(split_map)
        return split_dict

    def check_filter(self, to_check, subset):
        return subset["page"] == to_check["page"]

    def gen_iv_dsi_file(self):
        out = {}
        for dat in self.dats:
            for i, md in enumerate(dat.to_dicts()):
                if len(self._dat_filter) > 0 and md["fname"] in self._dat_filter.keys():
                    skip = True
                    for test_dict in self._dat_filter[md["fname"]]:
                        if self.check_filter(md, test_dict):
                            skip = False
                    if skip:
                        continue
                self.append_dat_dict(out, md, dat)
        return out

    def match_file_name_in_map(self, fname):
        matching_keys = [
            key
            for key in self.device_map.keys()
            if fnmatch.fnmatch(os.path.basename(fname), key)
        ]
        if len(matching_keys) == 0:
            return None
        if len(matching_keys) == 1:
            matched = self.device_map[matching_keys[0]]
            if self.device_map.get("default"):
                ret = deepcopy(self.device_map.get("default"))
                ret.update(matched)
            else:
                ret = matched
            return ret
        else:
            raise DatHelperError(
                f"Need more specific glob keys in device map, found {matching_keys} for {fname}"
            )

    def get_device(self, md):
        if map_dict := self.match_file_name_in_map(md["fname"]):
            return map_dict["model"]
        else:
            return "unknown"

    def get_device_map_dict(self, fname):
        logger = Logger()
        if map_dict := self.match_file_name_in_map(fname):
            return map_dict
        else:
            logger.error(f"[DAT]{fname} doesn't match a glob in the device map")
            return dict()

    def get_device_model_type(self, md):
        logger = Logger()
        check = os.path.basename(f"{md['fname']}")
        if map_dict := self.match_file_name_in_map(md["fname"]):
            return map_dict["device_type"]
        else:
            self.update_device_map = True
        if "mos" in check:
            self._device_map[check] = dict(device_type=md["datatype"], model="mosfet")
            return md["datatype"]
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

    def adjust_meas_name(self, output_name):
        return {"cgc": "cgc",}.get(output_name, output_name)

    def append_dat_dict(self, top, md, dat):
        test_fname = os.path.basename(re.sub(r"-(\d)", r"n\1", md["fname"]))
        test_name = f"{test_fname}_{md['page']}_{md['page_index']}"
        top[test_name] = top.get(test_name) or dict()
        sub = top[test_name]
        sub["instance parameters"] = sub.get("instance parameters") or dict()
        sub["stimuli"] = sub.get("stimuli") or dict()
        sub["control"] = sub.get("control") or dict()
        sub["sweep"] = sub.get("sweep") or dict()
        sub["definitions"] = sub.get("definitions") or dict()
        first_order_sweep = md["x"]
        second_order_sweep = md["p"]
        if not sub["stimuli"].get(first_order_sweep):
            sub["stimuli"][first_order_sweep] = make_sweep_dict(md["data_x"])
        if not sub["stimuli"].get(second_order_sweep):
            sub["stimuli"][second_order_sweep] = make_sweep_dict(
                list(md["data_p"].values())
            )
        sub["definitions"]["device_type"] = self.get_device_model_type(md)
        sub["device"] = self.get_device(md)
        if md["y"][0] == "i":
            sub["definitions"]["analysis_type"] = f"{md['y']}sweep"
        else:
            sub["definitions"]["analysis_type"] = self.adjust_meas_name(f"{md['y']}")
        instance_params = dict()
        for param,val in dat.header_data['instance']:
            instance_params[param] = scale_param(val)
        map_dict = self.get_device_map_dict(md["fname"])
        if map_dict.get("scale"):
            for par, scale in map_dict["scale"].items():
                instance_params[par] *= float(scale)
        doc_params = deepcopy(dat.header_data["instance"])
        sub["sweep"][1] = first_order_sweep
        sub["sweep"][2] = second_order_sweep
        if "t" in instance_params:
            sub["control"]["temperature"] = instance_params["t"]
            del instance_params["t"]
        sub["instance parameters"] = instance_params
        sub["views"] = sub.get("views") or dict()
        sub["views"][test_name] = sub["views"].get(test_name) or dict()
        stims = list(filter(lambda q: q[0] == "v" or q[0] == "i", md.keys()))
        stims = list(
            filter(lambda q: q not in [first_order_sweep, second_order_sweep], stims)
        )
        for stim in stims:
            sub["stimuli"][stim] = md[stim]

        title = f"{sub['device']} {md['y']}-{md['x']}"
        for inst, val in sub["instance parameters"].items():
            title += f" {inst} = {val:.3g}"
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
        if self.techdata.get("techdata", {}).get("measure_corner"):
            vsub["config"]["measure_corner"] = self.techdata["techdata"][
                "measure_corner"
            ]
        if self.is_common_log_candidate(md):
            sub["views"][f"{test_name}_log"] = deepcopy(sub["views"][test_name])
            sub["views"][f"{test_name}_log"]["config"]["axis"] = "semilogyaxis"

        sub["simulations"] = sub.get("simulations") or dict(measure=dict(sweep=[]))
        sweep_arr = sub["simulations"]["measure"]["sweep"]
        p = md[md["p"]]
        for x, y in zip(md["data_x"], md["data_y"]):
            sweep_arr.append([f"{x:.5g}", float(p), float(y)])

    def gen_metric_dsi_file(self):
        parser = DatParser(self.dats, self.techdata)
        parser.parse_all_metrics()
        out = dict()
        for metric in parser.metrics:
            orig_name = f"{metric.metric}_{metric.fname}"
            name = orig_name
            i= 0
            while out.get(name,False):
                name = f"{orig_name}_{i}"
                i+=1
            out[name] = metric.to_dsi()
        return out
