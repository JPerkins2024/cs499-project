# dsi.py, written by Adrian Treadwell
# Parse all YAML inputs and create parameter objects
# Go through parameter objects and create controller objects
# Depending on modularity, may make ControllerHelper.py
#import yaml
#from yaml import CDumper
import  ruamel.yaml
yaml = ruamel.yaml.YAML(typ='safe')
yamldumper = ruamel.yaml.YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
from .config_loader import config
from copy import deepcopy
from .merge import deep_merge
from .views import create_views
import re
import numpy as np
import os
from .logger import Logger
from .utils import expand_generic_sweep
from .calculator import (
    resolve_custom_expression,
    build_symbol_table,
    needs_resolving,
    convert_dict_units,
)


class DsiError(Exception):
    pass


class Dsi:  # The original DSI was a hash. The name "hash" in this context serves only as a reminder that I need to make it a hash
    def __init__(self, conf, techdata, debug=False):
        self.ymlFiles = []
        self.conf = conf
        self.Params = []
        self.Data = dict()
        self.techdata = techdata
        self.debug = debug

    def add_yml(self, ymlFile):
        self.ymlFiles.append(ymlFile)
        f = open(ymlFile, "r")
        yml_h = yaml.load(f)
        yml_h["default"] = yml_h.get("default") or dict()
        dirname = os.path.dirname(ymlFile)
        yml_h["default"]["_fname"] = ymlFile
        yml_h["default"]["_dirname"] = dirname
        yml_h, count = self.uniquify_params(yml_h, 0)
        yml_h = self.defaultsAndOverrides(yml_h)
        yml_h, count = self.uniquify_params(yml_h, 0)
        yml_h = self.uniq_paramname(yml_h)

        self.Data = yml_h
        f.close()

    def uniq_paramname(self, yml_h):
        key = str(len(self.ymlFiles))
        new_h = dict()
        for k in yml_h.keys():
            key_final = "h" + key + "__" + k
            new_h[key_final] = deepcopy(yml_h[k])
            new_h[key_final]["measure name"] = key_final
        return new_h

    def print(self):
        logger = Logger()
        for i, par in enumerate(self.Params):
            outname = self.ymlFiles[i]
            outname = re.sub("dsi.yml", "dso.yml", outname)
            out_hash = dict()
            for param in par:
                out_hash[param.name] = param.param_data
            outfile = open(outname, "w")
            #outfile.write(yaml.dump(out_hash, Dumper=CDumper))
            yamldumper.dump(out_hash,outfile)
            logger.info(f"Wrote {outname}")
            outfile.close()

    def is_sweep(self, subh, toph):
        if "type" in subh and toph.get("sweep"):
            return True
        return False

    def defaultsAndOverrides(self, yml_h):
        return_h = deepcopy(yml_h)
        for v in yml_h.keys():
            if v == "default" or v == "override":
                continue
            if self.conf.get("default") and return_h.get("default"):
                defaults = deep_merge(return_h["default"], self.conf["default"])

            elif self.conf.get("default"):
                defaults = self.conf["default"]
            else:
                defaults = return_h["default"]

            return_h[v] = deep_merge(return_h[v], defaults)
            if "override" in return_h:
                return_h[v] = deep_merge(return_h["override"], return_h[v])
            if "override" in self.conf:
                return_h[v] = deep_merge(self.conf["override"], return_h[v])
        if "default" in return_h:
            del return_h["default"]
        if "override" in return_h:
            del return_h["override"]
        return return_h

    def AddParam(self, param):
        index = int(param.measure_name.split("__")[0][1:]) - 1
        try:
            self.Params[index] = self.Params[index]
        except IndexError:
            self.Params.insert(index, [])
        self.Params[index].insert(index, param)

    def create_views(self):
        in_hash = {}
        logger = Logger()
        if len(self.Params) == 0:
            return
        for i, par in enumerate(self.Params):
            outname = self.ymlFiles[i]
            outname = re.sub("dsi.yml", "dso.yml", outname)
            new_hash = {}
            for param in par:
                new_hash[param.name] = param.param_data
            with open(outname, "r") as f:
                #tmp_par = yaml.load(f, Loader=yaml.CLoader)
                tmp_par = yaml.load(f)
            logger.info(f"Read {outname} for view generation")
            for param, val in tmp_par.items():
                if new_hash[param] and new_hash[param].get("views"):
                    tmp_par[param]["views"] = new_hash[param]["views"]
        create_views(tmp_par, self.debug)

    def uniquify_params(self, yml_h: dict, count):
        logger = Logger()
        counter = count
        ignore = []
        while True:
            path = self.uniquify_find_path(yml_h, ignore)
            path_key = self.build_path_key(path)

            if len(path) == 0:
                return [yml_h, counter]

            old_param = list(path.keys())[0]
            old_param_dict = yml_h[old_param]
            if "views" in old_param_dict and "default" in old_param_dict["views"]:
                old_param_dict["views"][old_param] = old_param_dict["views"].pop(
                    "default"
                )
            array = self.uniquify_find_array(path, old_param_dict)
            if len(array) == 1:
                self.uniquify_fix_array(yml_h, array[0], path_key)
            elif isinstance(array, dict) and "type" in array:
                continue
            else:
                for arr in array:
                    paramname = old_param.split("__")[0] + "__" + str(counter)
                    counter += 1
                    yml_h[paramname] = deepcopy(yml_h[old_param])
                    if isinstance(arr, tuple):
                        sweep_k = arr[1]
                        arr = arr[0]
                        yml_h[paramname]["sweep_k"] = sweep_k
                    self.uniquify_fix_array(yml_h[paramname], arr, path_key[1:])
                if not len(array) == 1:
                    del yml_h[old_param]
                if counter > 100100:
                    raise DsiError("Error reading DSI file")

    def uniquify_fix_array(self, yml_h, newval, path_key: list):
        tmp = yml_h
        while len(path_key) > 1:
            tmp = tmp[path_key.pop(0)]
            if tmp is None:
                print(path_key)
                print(yml_h)
                raise DsiError("Error in uniquify_fix_array")
        tmp[path_key.pop(0)] = newval

    def build_path_key(self, path):
        ret = []
        if len(path) == 0:
            return ret
        # Assuming path is always one-element hashes all the way down
        tmp = path
        while type(tmp) == dict and "type" not in tmp:
            key = None
            key = list(tmp.keys())[0]
            if key:
                ret.append(key)
                tmp = list(tmp.values())[0]
        return ret

    def uniquify_find_path(self, yml_h, ignore=[]):
        foundit = {}
        for key, val in yml_h.items():
            if isinstance(val, list):
                break
        if not isinstance(val, list):
            key = None
            val = None
        if key == "corners":
            return foundit
        if key == "default":
            return foundit
        if key:
            foundit[key] = val
        else:
            if "sweep" in yml_h.keys():
                if (
                    yml_h["sweep"].get(1) in yml_h.get("stimuli", {})
                    and yml_h.get("definitions", {}).get("analysis_type")
                    and yml_h["definitions"]["analysis_type"][0]
                    not in ["c", "y", "h", "r", "s", "q"]
                ):
                    ignore = [yml_h["sweep"].get(1)]

            for key, val in yml_h.items():
                if isinstance(val, dict):
                    if key == "corners":
                        continue
                    if key in ignore:
                        continue
                    if key == "default":
                        continue
                    if key == "views":
                        continue
                    if key == "simulations":
                        continue
                    if "type" in val:  # signifies sweep to be expanded
                        foundit[key] = val
                        break
                    temp = self.uniquify_find_path(val, ignore)
                    if not len(temp) == 0:
                        foundit[key] = temp
                        break
        return foundit

    def uniquify_find_array(self, yml_h, curr_param):
        for key, val in convert_dict_units(yml_h).items():
            if isinstance(val, list):
                return val
            elif (
                isinstance(val, dict)
                and "type" in val
                and key in curr_param.get("stimuli", {})
                and key == curr_param.get("sweep", {}).get(1)
                and yml_h.get("definitions", {}).get("analysis_type")
                and yml_h["definitions"]["analysis_type"][0]
                not in ["c", "y", "h", "r", "s", "q"]
            ):
                return val
            elif isinstance(val, dict) and "type" in val:
                out = []
                l_val = None
                if needs_resolving(val, ["type"]):
                    if curr_param.get("device"):
                        dev_techdata = self.techdata.get(curr_param["device"], {})
                    st = build_symbol_table(
                        curr_param["instance parameters"],
                        self.techdata.get("techdata", {}).get("definitions", {}),
                        dev_techdata.get("definitions", {}),
                        curr_param.get("definitions", {}),
                    )
                    l_val = resolve_custom_expression(convert_dict_units(val), st)
                else:
                    l_val = convert_dict_units(val)
                for k, sweep_val in expand_generic_sweep(l_val, ""):
                    sweep_k = dict()
                    if curr_param.get("sweep"):
                        sweep_k[
                            list(curr_param["sweep"].keys())[
                                list(curr_param["sweep"].values()).index(key)
                            ]
                        ] = k

                        out.append((sweep_val, sweep_k))
                    else:
                        out.append(sweep_val)
                return out
            elif isinstance(val, dict):
                return self.uniquify_find_array(val, curr_param)
            else:
                raise DsiError("No array found")
