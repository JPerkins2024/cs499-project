#! /usr/bin/env python
"""
Created on Tue Jul 25 10:46:05 CDT 2023


@author: wellsjeremy
"""

import cexprtk
from .logger import Logger
from copy import deepcopy
from pint import Quantity
from .utils import expand_generic_sweep,denumpy_dict
import re
from ruamel.yaml.compat import OrderedDict
import numpy as np


MAX_RECURSE = 10

def convert_dict_units(d):
    out = dict()
    for k, v in d.items():
        if issubclass(type(v), str):
            v = convert_unit(v)
            out[k] = v
        elif issubclass(type(v),list):
            new = []
            for q in v:
                if isinstance(q,str):
                    q = convert_unit(q)
                new.append(q)
            out[k]=new
        else:
            out[k] = v
    return out


def convert_unit(v):
    out = v
    if re.search(
        r"(^\d+|^-\d+)(\.\d+)?([eE][+-]?\d+)?[a-z]?$", v
    ):
        quant = Quantity(v + "m")
        out = quant.m_as("m")
    return out
    
    


def is_number(s):
    try:
        float(s)
        return True
    except:
        return False

def needs_resolving(d: dict,ignore=[]):
    for k,v in convert_dict_units(d).items():
        if k in ignore:
            continue
        if isinstance(v,list):
            for q in v:
                if not is_number(q):
                    return True
        elif not is_number(v):
            return True
    return False




def build_symbol_table(*dicts, ignore=[]) -> cexprtk.Symbol_Table:
    """
    Builds symbol table to be used in calculator resolve expressions
    This function takes in an arbitrary number of dictionaries as arguments, which are then merged with the later taking precidence for conflicts.
    Kwargs:
        ignore= None or List<str> : Used to pass in keys in dictionaries that should not be used to resolve equations.
    """
    st = dict()
    for d in dicts:
        st.update(convert_dict_units(d))
    if ignore and isinstance(ignore, list):
        for i in ignore:
            if i in st.keys():
                del st[i]

    pre_st = deepcopy(st)
    while True:

        curr_st = denumpy_dict(st)
        num_st = dict(filter(lambda k: type(k[1]) in [int, float], curr_st.items()))
        str_st = dict(filter(lambda k: type(k[1]) in [str], curr_st.items()))
        out = cexprtk.Symbol_Table(num_st, add_constants=True, string_variables=str_st)
        str_st = resolve_custom_expression(str_st,out, ignore=ignore,quiet=True)
        st.update(str_st)
        if pre_st == curr_st:
            st = deepcopy(curr_st)
            break
        pre_st = deepcopy(st)
    num_st = dict(filter(lambda k: type(k[1]) in [int, float], st.items()))
    str_st = dict(filter(lambda k: type(k[1]) in [str], st.items()))
    return cexprtk.Symbol_Table(num_st, add_constants=True, string_variables=str_st)


def resolve_custom_expression(param_h: dict, symbol_table: cexprtk.Symbol_Table, recurse = 0,ignore=[],strict=False,quiet=False):
    """
    Dynamic version of resolve_expression.
    to_resolve: variables to resolve
    symbol_table: table built with build_symbol_table function.
    """
    logger = Logger()
    error_msgs = []
    def resolve_callback(symbol):
        return [True, cexprtk.USRSymbolType.VARIABLE, symbol, ""]

    resolved_h = deepcopy(param_h)
    for k, v in param_h.items():
        if k in ignore:
            resolved_h[k]=v
            continue
        if type(v) in [int, float]:
            continue
        try:
            expression = cexprtk.Expression(v, symbol_table, resolve_callback)
            resolved_h[k] = expression.value()
        except TypeError as e:
            error_msgs.append(
                f"Unable to parse expression {v}.  Error was:\n{e}"
            )
            resolved_h[k] = v
        except AttributeError:
            resolved_h[k] = v
        except cexprtk.ParseException as e:
            error_msgs.append(
                f"Unable to parse expression {v}.  Error was:\n{e}"
            )
            resolved_h[k] = v

    if len(error_msgs) > 0 and recurse < MAX_RECURSE: 
        if not quiet:
            logger.debug(f"Retrying to resolve all values try {recurse}")
        resolved_h = resolve_custom_expression(param_h,symbol_table,recurse+1,strict=strict,quiet=quiet,ignore=ignore)
    else:
        if not quiet:
            for error in error_msgs:
                logger.error(error)
        if strict:
            logger.fatal(f"Could not resolve all expressions in {param_h}")
    return resolved_h


def resolve_expressions(param_h, techdata,recurse=0):
    """
    Basically a port of the ruby devsim's calculator function.
    This should be used for resolving parameters in simulation.
    """
    logger = Logger()
    custom_defs = dict()
    if not techdata:
        techdata = {}
    if param_h.get("device"):
        custom_defs["device"] = param_h["device"]
    if param_h.get("metric"):
        custom_defs["metric"] = param_h["metric"]
    custom_defs["temperature"] = param_h["control"]["temperature"]
    reference_dict = build_symbol_table(
        techdata.get("techdata", {}).get("control", {}),
        custom_defs,
        techdata.get("techdata", {}).get("definitions", {}),
        techdata.get("techdata", {}).get("corners", {}),
        param_h.get("definitions", {}),
        param_h.get("instance parameters", {}),
        ignore=[
            "port",
            "ports",
            "instance",
            "models path",
            "unit conversion",
            "reverse sweep",
            "model",
            "device_type",
            "analysis_type",
        ],
    )
    resolved_h = deepcopy(param_h)
    to_resolve = [
        "stimuli",
        "definitions",
        "instance parameters",
        "ic",
    ]
    modes = ["", "stress " "aged "]

    def resolve_callback(symbol):
        return [True, cexprtk.USRSymbolType.VARIABLE, symbol, ""]

    ignore = [
        "port",
        "ports",
        "instance",
        "models path",
        "unit conversion",
        "reverse sweep",
        "model",
        "device_type",
        "analysis_type",
    ]
    error_msgs = []
    for res in to_resolve:
        for mode in modes:
            key = f"{mode}{res}"
            if param_h.get(key) and (isinstance(param_h[key], dict) or issubclass(type(param_h[key]),OrderedDict)):
                for k, v in convert_dict_units(param_h[key]).items():
                    if type(v) in [int, float, bool, type(None)]:
                        continue
                    if type(v) == dict or issubclass(type(v),OrderedDict):
                        v = convert_dict_units(v)
                        for q, r in v.items():
                            if type(r) in [int, float, bool, type(None)]:
                                continue
                            else:
                                try:
                                    expression = cexprtk.Expression(
                                        r, reference_dict, resolve_callback
                                    )
                                    if np.isnan(expression.value()):
                                        error_msgs.append(
                                            f"Unable to parse expression {r}.  It evaluated to nan"
                                        )
                                        resolved_h[key][k][q] = expression.value()
                                    else:
                                        resolved_h[key][k][q] = r
                                except TypeError:
                                    resolved_h[key][k][q] = r
                                except AttributeError:
                                    resolved_h[key][k][q] = r

                                except cexprtk.ParseException as e:
                                    error_msgs.append(
                                        f"Unable to parse expression {r}.  Error was:\n{e}"
                                    )
                                    resolved_h[key][k][q] = r
                        continue
                    if k in ignore:
                        continue
                    try:
                        expression = cexprtk.Expression(
                            v, reference_dict, resolve_callback
                        )
                        if np.isnan(expression.value()):
                            error_msgs.append(
                                f"Unable to parse expression {v}.  It evaluated to nan"
                            )
                            resolved_h[key][k] = v
                        else:
                            resolved_h[key][k] = expression.value()
                    except TypeError:
                        resolved_h[key][k] = v
                    except AttributeError:
                        resolved_h[key][k] = v
                    except cexprtk.ParseException as e:
                        error_msgs.append(
                            f"Unable to parse expression {v}.  Error was:\n{e}"
                        )
                        resolved_h[key][k] = v

    if len(error_msgs) > 0 and recurse < 10 : 
        logger.debug(f"Retrying to resolve all values try {recurse}")
        resolved_h = resolve_expressions(resolved_h,techdata,recurse+1)
    else:
        for error in error_msgs:
            logger.error(error)
    return resolved_h
