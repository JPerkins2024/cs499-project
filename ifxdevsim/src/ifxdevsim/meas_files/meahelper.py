#! /usr/bin/env python
"""
Created on Fri Nov 17 14:18:25 CST 2023


@author: wellsjeremy
"""

import os
from ..logger import Logger
import re
import ruamel.yaml

yaml = ruamel.yaml.YAML()
import socket
from copy import copy, deepcopy
#from ifxpymea import FlatMea
from ..utils import (
    listfiles,
    is_number,
    get_site,
    to_number,
    make_sweep_dict,
    expand_generic_sweep,
    scale_param
)
import fnmatch
from ..metrics import MeaParser
import numpy as np
import pandas as pd


class MeaHelperError(Exception):
    pass


class MeaHelper:
    def __init__(self, techdata):
        self.techdata = techdata
        self._meafile_paths = []
        self._meafiles = []
        self._meafile_filter = dict()
        self.update_device_map = False
        self._device_map = {}

    @property
    def meafile_paths(self):
        return self._meafile_paths

    @property
    def device_map(self):
        return self._device_map

    @property
    def meafiles(self):
        return self._meafiles

    def import_dir(self, path):
        logger = Logger()
        for file in listfiles(path, None, ".mea"):
            if os.path.splitext(file)[1] == ".mea":
                logger.info(f"Found {file}")
                self.meafile_paths.append(file)

    # iterate: mea.curves
    def create_meafiles(self):
        logger = Logger()
        for path in self.meafile_paths:
            mea = FlatMea(path)
            self.get_device_model_type(mea)
            self.meafiles.append(mea)

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
            raise MeaHelperError(
                f"Need more specific glob keys in device map, found {matching_keys} for {fname}"
            )

    def get_device_model_type(self, mea):
        logger = Logger()
        check = os.path.basename(f"{mea.fname}")

        if map_dict := self.match_file_name_in_map(mea.fname):
            return map_dict["device_type"]
        else:
            self.update_device_map = True
        mea_preamble = mea.preamble
        pattern = r"\{(.*)\}"
        preamble_dict = dict(type="UNKNOWN")
        if match := re.search(pattern, mea_preamble):
            preamble_dict = dict(
                item.split("=") for item in match.group(1).lower().split(",")
            )

        if "mos" in preamble_dict["type"]:
            self._device_map[check] = dict(
                device_type=preamble_dict["type"], model="mosfet"
            )
            return preamble_dict["type"]
        elif "res" in preamble_dict["type"]:
            self._device_map[check] = dict(device_type="res", model="res")
            return "res"
        elif "cap" in preamble_dict["type"]:
            self._device_map[check] = dict(device_type="cap", model="cap")
            return "cap"
        elif "npn" in preamble_dict["type"]:
            self._device_map[check] = dict(device_type="npn", model="npn")
            return "npn"
        elif "pnp" in preamble_dict["type"]:
            self._device_map[check] = dict(device_type="pnp", model="pnp")
            return "pnp"
        else:
            logger.warning(
                f"Could not determine guess of device_type for {mea['fname']}\nUpdate the device_type and model and re-run."
            )
            self._device_map[check] = dict(device_type=check, model=check)
            return check

    def write_meas_list(self, fout):
        for mea in self.meafiles:
            printed_pages = []
            for sweep in mea.curves:
                page_idx = sweep["page_idx"]
                if page_idx not in printed_pages:
                    s = f"login.{get_site()} {mea.fname} "
                    ignore = [ "curve_idx", "data_x", "data_y"]
                    if sweep.get("p"):
                        ignore.append(sweep["p"])
                    for param, val in reversed(sweep.items()):
                        if param in ignore:
                            continue
                        if isinstance(val, dict):
                            s += " " + f"{param}={val}".replace(" ", "")
                        else:
                            s += f" {param}={val}"
                    printed_pages.append(page_idx)
                    s += "\n"
                    fout.write(s)

    def handle_meas_list_line(self, site, path, *rest):
        self._loaded = getattr(self, "_loaded", [])
        if get_site() != site.split(".")[1]:
            if not os.path.exists(path):
                raise MeaHelperError(
                    f"Mea file {path} does not exist at {get_site()}, please check {site}"
                )
        else:
            if path not in self._loaded:
                mea = FlatMea(path)
                if devsim_dict := self.match_file_name_in_map(mea.fname):
                    setattr(mea, "devsim", devsim_dict)
                else:
                    setattr(
                        mea, "devsim", dict(device_type="unknown", model="unknown"),
                    )

                self.meafiles.append(mea)
                self._loaded.append(path)
            self._meafile_filter[path] = self._meafile_filter.get(path) or []
            self._meafile_filter[path].append(self.filter_dict_from_line(rest))

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

    def gen_iv_dsi_file(self):
        out = {}
        for mea in self.meafiles:
            for i, md in enumerate(mea.curves):
                if (
                    len(self._meafile_filter) > 0
                    and mea.fname in self._meafile_filter.keys()
                ):
                    skip = True
                    for test_dict in self._meafile_filter[mea.fname]:
                        if self.check_filter(md, test_dict):
                            skip = False
                    if skip:
                        continue
                self.append_mea_dict(out, md, mea)
        return out

    def get_device(self, mea):
        if map_dict := self.match_file_name_in_map(mea.fname):
            return map_dict["model"]
        else:
            return "unknown"

    def parse_instance_params(self, md):
        keywords = ["page_idx", "curve_idx", "x", "name", "p", "y", "data_x", "data_y",'group']
        stims = list(filter(lambda q: q[0] == "v", md.keys()))
        [keywords.append(stim) for stim in stims]
        out = dict([(k, scale_param(k,to_number(v))) for k, v in md.items() if k not in keywords])
        return out

    def parse_doc_params(self, md):
        keywords = ["page_idx", "curve_idx", "x", "name", "p", "y", "data_x", "data_y"]
        out = dict([(k, v) for k, v in md.items() if k not in keywords])
        return out

    def get_device_map_dict(self, fname):
        logger = Logger()
        if map_dict := self.match_file_name_in_map(fname):
            return map_dict
        else:
            logger.error(f"[MEA]{fname} doesn't match a glob in the device map")
            return dict()

    def append_mea_dict(self, top, md, mea):
        test_fname = os.path.basename(re.sub(r"-(\d)", r"n\1", os.path.splitext(mea.fname)[0]))
        test_name = f"{test_fname}_{md['name']}_{md['page_idx']}"
        top[test_name] = top.get(test_name) or dict()
        sub = top[test_name]
        sub["instance parameters"] = sub.get("instance parameters") or dict()
        sub["stimuli"] = sub.get("stimuli") or dict()
        sub["control"] = sub.get("control") or dict()
        sub["sweep"] = sub.get("sweep") or dict()
        sub["definitions"] = sub.get("definitions") or dict()
        first_order_sweep = md["x"]
        second_order_sweep = md.get("p", False)
        if not sub["stimuli"].get(first_order_sweep):
            sub["stimuli"][first_order_sweep] = make_sweep_dict(md["data_x"])
        if second_order_sweep:
            tmp = sub["stimuli"].get(second_order_sweep, [])
            if isinstance(tmp, dict):
                tmp = list(map(lambda q: q[1], expand_generic_sweep(tmp, "")))
                tmp.append(md[md["p"]])
            else:
                tmp.append(md[md["p"]])
            sub["stimuli"][second_order_sweep] = make_sweep_dict(list(set(tmp)))
        sub["definitions"]["device_type"] = self.get_device_model_type(mea)
        sub["device"] = self.get_device(mea)
        if md["y"][0] == "i":
            sub["definitions"]["analysis_type"] = f"{md['y']}sweep"
        else:
            sub["definitions"]["analysis_type"] = self.adjust_meas_name(f"{md['y']}")
        instance_params = self.parse_instance_params(md)
        map_dict = self.get_device_map_dict(mea.fname)
        if map_dict.get("scale"):
            for par, scale in map_dict["scale"].items():
                instance_params[par] *= float(scale)
        sub["sweep"][1] = first_order_sweep
        if second_order_sweep:
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
            sub["stimuli"][stim] = to_number(md[stim])

        title = f"{sub['device']} {md['y']}-{md['x']}"
        for inst, val in sub["instance parameters"].items():
            if is_number(val):
                title += f" {inst} = {val:.3g}"
            else:
                title += f" {inst} = {val}"
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
        p = None
        if second_order_sweep:
            p = md[md["p"]]
        for x, y in zip(md["data_x"], md["data_y"]):
            if p:
                sweep_arr.append([f"{x:.5g}", float(p), float(y)])
            else:
                sweep_arr.append([f"{x:.5g}", None, float(y)])

    def check_filter(self, to_check, subset):
        return subset["page_idx"] == to_check["page_idx"]

    def is_common_log_candidate(self, page):
        if page["y"] == "id" and page["x"] == "vg":
            return True
        return False

    def adjust_meas_name(self, output_name):
        return {"cgc": "cgc",}.get(output_name, output_name)


    def gen_metric_dsi_file(self):
        parser = MeaParser(self.meafiles, self.techdata)
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
