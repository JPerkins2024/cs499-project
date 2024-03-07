#! /usr/bin/env python
"""
Created on Wed Aug  9 14:00:11 CDT 2023


@author: wellsjeremy
"""

import itertools
import numpy as np
from .logger import Logger
import os
import re
import socket
import math

scale = 1.0
def set_scale(value):
    global scale
    scale = value

def scale_param(paramname,value):
    global scale
    scale_params = ["w","l","pd","ps","sa","sb","perim","pj"]
    double_scale_params = ["area","ad","as"]
    if paramname in scale_params:
        value*=scale
    if paramname in double_scale_params:
        value*=scale*scale
    return value



def grouper(iterable, n, incomplete="fill", fillvalue=None):
    args = [iter(iterable)] * n
    if incomplete == "fill":
        return itertools.zip_longest(*args, fillvalue=fillvalue)
    if incomplete == "strict":
        return zip(*args, strict=True)
    if incomplete == "ignore":
        return zip(*args)
    else:
        raise ValueError("Expected fill, strict, or ignore")


def expand_generic_sweep(sweep_dict: dict, k: str):
    """
    Generator of sweeps and modify k iterators to have unique identifiers.
    Sweep dict can be of type: [lin log list] based on "type" key.  Descriptors are as follows:
    lin: sweep dictionary must have the following keys:
        type: lin
        start: start value
        stop: stop value
        step: step size
          OR
        num steps: number of steps
    log:
        type: log
        start: start value
        stop: stop value
        step: steps/dec.
    list:
        type: list
        list: array of values

    Args:
        sweep_dict (dict):
        k (str): iterator for instance and measures.

    Yields: [point, k_{point_index}]

    """
    for q, r in {
        "lin": expand_lin_sweep,
        "log": expand_log_sweep,
        "list": expand_list_sweep,
    }[sweep_dict["type"]](sweep_dict, k):
        yield [q, float(r)]


def fix_step_sign(start, stop, step):
    fixed = step
    if stop < start and step > 0:
        fixed *= -1
    elif stop > start and step < 0:
        fixed *= -1
    return float(f"{fixed:.5g}")


def expand_lin_sweep(sweep_dict, k):
    start = sweep_dict["start"]
    stop = sweep_dict["stop"]
    if "step" in sweep_dict:
        step = sweep_dict["step"]
        step = fix_step_sign(start, stop, step)
        for i, point in enumerate(np.arange(start, stop + step, step)):
            point = float(f"{point:.5g}")
            yield [f"{k}_{i}", point]
    elif "num steps" in sweep_dict:
        for i, point in enumerate(np.linspace(start, stop, sweep_dict["num steps"])):
            point = float(f"{point:.5g}")
            yield [f"{k}_{i}", point]


def expand_log_sweep(sweep_dict, k):
    start = sweep_dict["start"]
    stop = sweep_dict["stop"]
    steps_per_decade = sweep_dict["step"]
    num_steps = int(np.ceil(steps_per_decade * np.log10(stop / start)))
    for i, point in enumerate(
        np.logspace(np.log10(start), np.log10(stop), num=num_steps)
    ):
        point = float(f"{point:.5g}")
        yield [f"{k}_{i}", point]


def expand_list_sweep(sweep_dict, k):
    for i, point in enumerate(sweep_dict["list"]):
        yield [f"{k}_{i}", point]


def make_sweep_dict(data_x):
    """
    Guess what type of dataset a sweep of data is, and convert it to a sweep dictionary

    Args:
        data_x (list-like): x-data sweep

    Returns:
        Sweep dictionary
        
    """
    return {
        "lin": get_lin_sweep,
        "log": get_log_sweep,
        "list": lambda q: dict(type="list", list=q),
        "single": lambda q: q,
    }[get_sweep_type(data_x)](data_x)


def get_sweep_type(arr):
    """
    Determine whether a datasweep is a linear or logarithimic dataset.
    Defaults to list if not able to determine.

    Args:
        arr (list-like): x-data sweep

    Returns:
        
    """
    if len(arr) <= 1:
        return "single"
    # Calculate the differences between adjacent elements
    differences = np.diff(arr)

    # Check if the differences are constant (linear sweep)
    if np.allclose(differences, differences[0]):
        return "lin"

    # Check if the differences form a geometric sequence (logarithmic sweep)
    ratios = differences[1:] / differences[:-1]
    if np.allclose(ratios, ratios[0]):
        return "log"

    return "list"


def get_lin_sweep(data_x):
    """
    Convert linear data sweep to dictionary.  Does no checking on validity of sweep.

    Args:
        data_x (list-like):  List of x-values

    Returns:
        
    """
    step = data_x[1] - data_x[0]
    start = data_x[0]
    stop = data_x[-1]
    return dict(start=float(start), stop=float(stop), step=float(step), type="lin")


def get_log_sweep(data_x):
    """
    Convert logarithimic data sweep to dictionary.  Does no checking on validity of sweep.
    

    Args:
        data_x (list-like):  List of x-values

    Returns:
        
    """
    step = len(data_x)
    start = data_x[0]
    stop = data_x[-1]
    return dict(start=float(start), stop=float(stop), step=float(step), type="log")


def is_number(s):
    try:
        float(s)
        return True
    except:
        return False


def listfiles(dir, search=None, ext=None):
    logger = Logger()
    if not os.path.exists(dir):
        logger.fatal(f"Measure path {dir} does not exist")
    for root, folders, files in os.walk(dir):
        for filename in folders + files:
            fullpath = os.path.join(root, filename)
            if os.path.isdir(fullpath):
                continue
            else:
                if search and re.match(search, filename):
                    yield (os.path.join(root, filename))
                elif not search:
                    yield (os.path.join(root, filename))


def get_site():
    return socket.gethostname()[0:3]


def to_number(num_maybe):
    try:
        num = float(num_maybe)
        return num
    except:
        return num_maybe


def denumpy_dict(d):
    for num,val in d.items():
        if isinstance(val,dict):
            d[num] = denumpy_dict(val)
        elif isinstance(val,list):
            d[num] = map(to_number, val)
        elif isinstance(val,bool):
            continue
        else: 
            d[num] = to_number(val)
    return d 
