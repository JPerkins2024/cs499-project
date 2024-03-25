#! /usr/bin/env python
"""
Created on Tue Dec 12 13:56:23 CST 2023


@author: wellsjeremy
"""

from .metric_funcs import calc_vt, calc_max_gm, calc_id, calc_vtc, calc_vt_sat
from . import metric_funcs
import math
from ..logger import Logger
from .metric import Metric
from types import MethodType
from inspect import getmembers, isfunction
from ..calculator import resolve_custom_expression, build_symbol_table
from copy import deepcopy
import os
from .mdm_parser import (
    valid_routine,
    call_routine,
    print_valid_routines,
    is_number,
    add_method,
    validate_meas_dict,
)


class MeaParser:
    def __init__(self, meafiles, techdata):
        self._meafiles = meafiles
        self._metric_data = dict()
        self.techdata = techdata
        self._metrics = []

    @property
    def metrics(self):
        return self._metrics

    def parse_all_metrics(self):
        logger = Logger()
        for dat in self._meafiles:
            metrics = self.parse_metrics(dat)
            for metric in metrics:
                self.metrics.append(metric)


    def get_instance_params(self,md):
        ignore = [
                            "x",
                            "y",
                            "p",
                            "data_x",
                            "data_y",
                            "page_idx",
                            "curve_idx",
                            "fname",
                            "name",
                            "group",
                            "datatype",
                            "page",
        ] 
        return dict(filter(lambda q: q[0] not in ignore, md.items()))


    def parse_metrics(self, mea):
        """
        I copied this from dat_helper.py and hacked.

        Probably some things here can be deleted.  If it works I'm not going to.

        Args: mea (FlatMea): 

        Returns List[Metric]:
            
        """
        logger = Logger()
        device = mea.devsim["model"]
        tech_device = self.techdata.get(device)
        metrics = []
        if not tech_device:
            logger.warning(
                f"No device found for {device}!  Update either devsim_device_map or techfile"
            )
            return
        if not tech_device.get("metrics"):
            logger.warning_once(f"No metrics found for {device}!  Update techfile")
            return []
        for metric in tech_device["metrics"]:
            metric_dict = self.techdata["metrics"].get(metric, False)
            if not metric_dict:
                logger.error(f"Metric {metric} not found in techfile")
                continue
            if not metric_dict.get("measure"):
                logger.warning_once(
                    f"Metric {metric} does not have a measure configuration.  It will not be considered"
                )
                continue
            meas_dict = metric_dict["measure"]
            validate_meas_dict(meas_dict, metric)
            routine = meas_dict["routine"]
            curve = meas_dict.get("curve", dict(x="fail", y="fail"))
            for md in mea.curves:
                mea_instance_dict = tech_device.get('instance parameters')
                mea_instance_dict.update(self.get_instance_params(md))
                if "t" in mea_instance_dict:
                    mea_instance_dict["temperature"] = mea_instance_dict["t"]
                    del mea_instance_dict["t"]
                ignore = ["port", "ports", "instance","device_type"]
                reference_dict = build_symbol_table(
                    tech_device.get("definitions", {}),
                    mea_instance_dict,
                    ignore=ignore,
                )
                meas_dict["stimuli"] = resolve_custom_expression(
                    meas_dict["stimuli"], reference_dict,ignore=ignore
                )
                if self.check_sweep_compatability(md, meas_dict, metric):
                    logger.setContext(f"Parsing {metric} in {mea.fname}")
                    routine_name = routine["name"]
                    routine_args = routine["args"]
                    routine_args_dict = dict()
                    for arg in routine_args:
                        if arg in mea_instance_dict:
                            routine_args_dict[arg] = mea_instance_dict[arg]
                        elif arg in tech_device.get("definitions", {}):
                            routine_args_dict[arg] = tech_device["definitions"][arg]
                        else:
                            routine_args_dict[arg] = arg
                    instance_params = deepcopy(tech_device.get('instance parameters',{}))
                    instance_params.update(mea_instance_dict)
                    reference_dict = build_symbol_table(
                        tech_device.get("definitions", {}),
                        instance_params,
                        ignore=ignore,
                    )

                    routine_args_dict = resolve_custom_expression(
                        routine_args_dict, reference_dict
                    )
                    evaluated_metric = call_routine(
                        routine_name,
                        md["data_x"],
                        md["data_y"],
                        *routine_args_dict.values(),
                    )
                    pass_through = dict()
                    for k in mea_instance_dict.keys():
                        if k in [
                            "x",
                            "y",
                            "data_x",
                            "data_y",
                            "page_idx",
                            "curve_idx",
                            "fname",
                            "group",
                            "datatype",
                            "page",
                            *meas_dict['stimuli'].keys(),
                            md['x']
                        ]:
                            continue
                        else:
                            pass_through[k] = mea_instance_dict[k]
                    metrics.append(
                        Metric(
                            metric,
                            device,
                            self.techdata,
                            evaluated_metric,
                            pass_through,
                            f"Page_{md['page_idx']}_curve_{md['curve_idx']}_{os.path.basename(mea.fname)}",
                        )
                    )
            logger.clearContext()

        return metrics

    def check_sweep_compatability(self, sweep_dict, criteria, metric_name):
        logger = Logger()
        bias_conditions = criteria["stimuli"]
        if (
            criteria["curve"]["x"] != sweep_dict["x"]
            or criteria["curve"]["y"] != sweep_dict["y"]
        ):
            return False
        for node, bias in bias_conditions.items():
            logic = self.create_logic(str(bias))
            if node not in sweep_dict.keys() and sweep_dict["x"] != node:
                if bias == 0:
                    sweep_dict[bias] = 0
                    continue
                logger.warning(
                    f"Unable to find {node} from stimuli for {metric_name}\n{sweep_dict.keys()}\n{bias_conditions}"
                )
                return False
            if sweep_dict["x"] == node:
                if not any(map(lambda x: logic(x), sweep_dict["data_x"])):
                    return False
            elif not logic(sweep_dict[node]):
                return False
        return True

    def create_logic(self, string):
        if "<" == string[0]:
            return lambda q: q < float(string[1:])
        elif ">" == string[0]:
            return lambda q: q > float(string[1:])
        elif is_number(string):
            return lambda q: math.isclose(q, float(string))
        else:
            return lambda q: q == string
