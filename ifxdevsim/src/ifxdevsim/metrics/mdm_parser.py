#! /usr/bin/env python
"""
Created on Tue Jul 11 07:46:19 CDT 2023


@author: wellsjeremy
"""
from .metric_funcs import calc_vt, calc_max_gm, calc_id, calc_vtc, calc_vt_sat
from . import metric_funcs
import math
from ifxpymdm import Mdm
from ..logger import Logger
from .metric import Metric
from types import MethodType
from inspect import getmembers, isfunction
from ..calculator import resolve_custom_expression,build_symbol_table
from copy import deepcopy

def valid_routine(s):
    out = []
    for func in getmembers(metric_funcs,isfunction):
        if "calc" in func[0]:
            out.append(func[0])

    return s in out


def call_routine(s,data_x,data_y,*args):
    logger = Logger()
    for func in getmembers(metric_funcs,isfunction):
        if s == func[0]:
            logger.debug(f"Calling {func[0]} with args {args}")
            return func[1](data_x,data_y,*args)



def print_valid_routines():
    logger = Logger()
    out = []
    for func in getmembers(metric_funcs,isfunction):
        if "calc" in func[0]:
            out.append(func)
    s = "Valid Routines:\n"
    for func in out:
        s+=(f"\t{func[0]}: {func[1].__code__.co_varnames[:func[1].__code__.co_argcount][2:]}\n")
    logger.info(s)


def is_number(s):
    try:
        float(s)
        return True
    except:
        return False

def add_method(obj, method, name):
    if name is None:
        name = method.func_name
    setattr(obj, name, MethodType(method,obj))


def validate_meas_dict(meas_dict,metric_name):
    logger = Logger()
    if not meas_dict.get('routine'):
        logger.error(f"{metric_name} techfile configuration needs to have routine name and arguments")
    if not valid_routine(meas_dict['routine'].get('name','')):
        logger.error(f"{metric_name} techfile configuration needs to a valid routine name") 
    if not meas_dict.get('curve'):
        logger.error(f"{metric_name} techfile configuration needs to have a curve description with")


class MdmParser:
    def __init__(self, mdms,techdata):
        self._mdms = mdms
        self._metric_data = dict()
        self.techdata = techdata
        self._metrics = []

    @property
    def metrics(self):
        return self._metrics

    def parse_all_metrics(self):
        logger = Logger()
        for mdm in self._mdms:
            metrics = self.parse_metrics(mdm)
            for metric in metrics:
                self.metrics.append(metric)

    def parse_metrics(self,mdm):
        logger = Logger()
        device = mdm.devsim['model']
        tech_device = self.techdata.get(device)
        metrics = []
        if not tech_device:
            logger.warning(f"No device found for {device}!  Update either devsim_device_map or techfile")
            return []
        if not tech_device.get('metrics'):
            logger.warning_once(f"No metrics found for {device}!  Update techfile")
            return []
        for metric in tech_device['metrics']:
            metric_dict = self.techdata['metrics'].get(metric,False)
            if not metric_dict:
                logger.error(f"Metric {metric} not found in techfile")
                continue
            if not metric_dict.get('measure'):
                logger.warning_once(f"Metric {metric} does not have a measure configuration.  It will not be considered")
                continue
            meas_dict = metric_dict['measure']
            validate_meas_dict(meas_dict,metric)
            routine = meas_dict['routine']
            curve = meas_dict.get('curve',dict(x='fail',y='fail'))
            if curve['x']!=mdm.first_order_sweep.name or curve['y'] not in mdm.iccap_outputs.keys():
                continue
            valid_iccap_values = dict()
            in_spice = False
            for k,v in mdm.iccap_values.items():
                if k[0] == "_":
                    continue
                valid_iccap_values[k]=v
            reference_dict = build_symbol_table(
                tech_device.get('definitions',{}),
                valid_iccap_values,
                ignore=["port" "ports" "instance"],
            )
            meas_dict['stimuli'] = resolve_custom_expression(meas_dict['stimuli'],reference_dict)
            for md in mdm.to_dicts():
                if self.check_sweep_compatability(md,meas_dict,metric):
                    logger.setContext(f"Parsing {metric} in {mdm.fname}")
                    routine_name = routine['name']
                    routine_args = routine['args']
                    routine_args_dict = dict()
                    for arg in routine_args:
                        if arg in valid_iccap_values:
                            routine_args_dict[arg] = valid_iccap_values[arg]
                        elif arg in tech_device.get('definitions',{}):
                            routine_args_dict[arg]=tech_device['definitions'][arg]
                        else:
                            routine_args_dict[arg]=arg
                    reference_dict = build_symbol_table(
                        tech_device.get('definitions',{}),
                        valid_iccap_values,
                        ignore=["port" "ports" "instance"],
                    )
                    routine_args_dict = resolve_custom_expression(routine_args_dict,reference_dict)
                    evaluated_metric = call_routine(routine_name,md['data_x'],md['data_y'],*routine_args_dict.values())
                    ignore = ['fname', 'data_idx', 'x', 'y', 'dataorigin', '___context', 'date', 'version', 'bench' , 'lot', 'operator', 'wafer', 'die', 'dielist', 'block', 'subsite', 'routine', 'meascond', 'device', 'devicename', 'devtechno', 'devpolarity', 'setup', 'type', '___spice_instance', '___techno_instance', '___calibration',  'data_x', 'data_y'] 
                    pass_through  = dict()
                    for k in md.keys():
                        if k in ignore:
                            continue
                        elif k in map(lambda q: q.name, mdm.sweeps):
                            continue
                        else:
                            pass_through[k] = md[k]
                    metrics.append(Metric(metric,device,self.techdata,evaluated_metric,pass_through,md['fname']))
            logger.clearContext()
            
        return metrics 



    def select_mdms(self, criteria, metric):
        logger=Logger()
        curve = criteria.get('curve',dict(x='fail',y='fail'))
        valid_mdms = self._mdms
        valid_mdms = list(filter(lambda q: q.first_order_sweep.name == curve['x'] and curve['y'] in q.iccap_outputs.keys(),valid_mdms))
            
        if len(valid_mdms) == 0:
            logger.warning(f"Unable to find MDM for {metric} {criteria}")
            return None
        return valid_mdms

    def check_sweep_compatability(self, sweep_dict, criteria,metric_name):
        logger = Logger()
        bias_conditions = criteria["stimuli"]
        for node, bias in bias_conditions.items():
            logic= self.create_logic(str(bias))
            if node not in sweep_dict.keys() and sweep_dict['x'] != node:
                logger.fatal(f"Unable to find {node} from stimuli for {metric_name}\n{sweep_dict.keys()}\n{bias_conditions}")
            if sweep_dict['x'] == node:
                if not any(map(lambda x: logic(x),sweep_dict['data_x'])):
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
