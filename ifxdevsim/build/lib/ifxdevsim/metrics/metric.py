#! /usr/bin/env python
"""
Created on Tue Aug  1 08:19:18 CDT 2023


@author: wellsjeremy
"""
import re
import os
from ..logger import Logger
from copy import deepcopy
from ..utils import is_number,to_number,denumpy_dict,scale_param


class Metric:
    def __init__(self, metric, device, techdata, value, params_from_meas, fname):
        self.metric = metric
        self.device = device
        self.tech_device = techdata.get(device, {})
        self.techdata = techdata
        self.value = value
        self.params_from_meas = params_from_meas
        self.fname = self.fix_fname(fname)

    def __eq__(self, other):
        return (
            self.metric == other.metric
            and self.params_from_meas == other.params_from_meas
        )


    def fix_fname(self,name):
        """
        Fixes fnames so that .measures aren't screwed up by replacing tokens with values that spice doesn't hate.

        Args:
            name (file name): 

        Returns:
            modified name (str)
            
        """
        name = os.path.basename(name)
        name = os.path.splitext(name)[0]
        name = re.sub(r"\.","p",name)
        name = re.sub(r"=","_eq_",name)
        return name


    def to_dsi(self):
        out = dict()
        out["device"] = self.device
        out["metrics"] = self.metric
        out["control"] = dict()
        out["control"]["temperature"] = self.params_from_meas["temperature"]
        del self.params_from_meas["temperature"]
        out["instance parameters"] = dict()
        out["instance parameters"].update(self.params_from_meas)
        for param,val in out['instance parameters'].items():
            out['instance parameters'][param] = scale_param(param,val)
        out["definitions"] = dict()
        metric_dict = self.techdata["metrics"][self.metric]
        out["definitions"].update(self.tech_device["definitions"])
        out["definitions"].update(metric_dict.get("definitions", {}))
        out["stimuli"] = metric_dict.get("stimuli", {})
        if metric_dict.get("plot", False):
            out["views"] = out.get("views") or dict()
            for plot_def in metric_dict["plot"]:
                if self.valid_plot(out, plot_def):
                    view_id = self.gen_view_id_from_dict(out, plot_def)
                    out["views"][view_id] = dict()
                    out["views"][view_id]["type"] = "texgraph"
                    out["views"][view_id]["config"] = self.generate_graph_config(
                        out, plot_def
                    )
                    out["views"][view_id]["sweep_convert"] = dict(
                        x=self.find_param(plot_def["x"],out),
                        p=self.find_param(plot_def.get("p", ""),out),
                    )
        out["simulations"] = dict(measure=dict(nominal=float(self.value)))
        return denumpy_dict(out)

    def gen_view_id_from_dict(self, param_dict, plot_def):
        logger = Logger()
        name = f"{param_dict['device']}_{param_dict['metrics']}_x{plot_def['x']}"
        if plot_def.get('p'):
            name+=f"_p{plot_def['p']}"
        skip = [plot_def.get("x"), plot_def.get("p")]
        if not plot_def.get("params"):
            logger.fatal(
                f"Need to define parameter list for plot definition in {self.metric}"
            )
        for param in plot_def["params"]:
            if val := self.find_param(param, param_dict):
                if is_number(val):
                    name += f"_{param}={val:.3g}"
                else:
                    name += f"_{param}={val}"
        return name

    def generate_graph_config(self, param_dict, plot_def):
        view_config = dict(
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
            view_config["measure_corner"] = self.techdata["techdata"][
                "measure_corner"
            ]
        view_config["xlabel"] = plot_def["x"]
        units = self.techdata.get("metrics",{}).get(self.metric,{}).get('definitions',{}).get("units","")
        unit_str = ""
        if len(units) > 0 : 
            unit_str = f" ({units})"

        if plot_def.get("p"):
            view_config["plabel"] = plot_def["p"]
        view_config["ylabel"] = f"{self.metric}{unit_str}"
        view_config["title"] = self.resolve_title(param_dict, plot_def)
        return view_config

    def valid_plot(self, param_dict, plot_def):
        good_plot = True
        logger = Logger()
        if not plot_def.get("x"):
            return False
        for par in ["x", "p"]:
            if plot_def.get(par) and self.find_param(plot_def[par], param_dict) is None:
                logger.warning(
                    f"{par}:{plot_def[par]} not found, ignoring plot definition for {self.metric}:{self.fname}"
                )
                return False
        return good_plot

    def find_param(self, par, param_dict):
        if len(par) == 0:
            return None
        lookups = ["instance parameters", "stimuli", "control"]
        for name in lookups:
            if param_dict.get(name) and par in param_dict[name]:
                return param_dict[name][par]
        return None

    def resolve_title(self, param_dict, plot_def):
        logger = Logger()
        if not plot_def.get("title"):
            generated_title = f"{self.device} {self.metric} {plot_def['x']} trend"
            if plot_def.get("p"):
                generated_title += f" multiple {plot_def['p']}"
            return generated_title
        else:
            resolved = deepcopy(plot_def["title"])
            if "@device@" in resolved:
                resolved = re.sub("@device@", self.device, resolved)
            if "@metric@" in resolved:
                resolved = re.sub("@metric@", self.metric, resolved)
            if "@params@" in resolved:
                param_str = ""
                if not plot_def.get("params"):
                    logger.fatal(
                        f"Need to define parameter list for plot definition in {self.metric}"
                    )
                for param in plot_def["params"]:
                    if val := self.find_param(param, param_dict):
                        if is_number(val):
                            param_str += f" {param}={val:.3g}"
                        else:
                            param_str += f" {param}={val}"

                resolved = re.sub("@params@", param_str, resolved)
            return resolved
