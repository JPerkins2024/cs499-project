#! /usr/bin/env python
"""
Created on Wed Jun 28 15:21:04 CDT 2023


@author: wellsjeremy
"""
from ..logger import Logger
import math

logger = Logger()




def calc_vtc(data_x, data_y, itar,polarity=1):
    data_x = list(map(lambda q: polarity * q,data_x))
    data_y = list(map(lambda q: polarity * q,data_y))
    if data_x[0] > data_x[-1]:
        data_x = list(reversed(data_x))
        data_y = list(reversed(data_y))
    return polarity * xval(itar*polarity, data_x, data_y)


def linear_X_interp(x1, x2, y1, y2, x):
    if x1 == x2 and x2 == x:
        return (y1 + y2) / 2.0
    ratio = (x - x1) / (x2 - x1)
    if ratio < 0 or ratio > 1:
        print(f"Cannot extrapolate x (x1:{x1} x2:{x2} y1:{y1} y2:{y2} ratio:{ratio})")
    return ratio * (y2 - y1) + y1


def linear_y_interp(x1, x2, y1, y2, y):
    if y1 == y2 and y2 == y:
        return (x1 + x2) / 2.0
    ratio = (y - y1) / (y2 - y1)
    if ratio < 0 or ratio > 1:
        print(f"Cannot extrapolate y (x1:{x1} x2:{x2} y1:{y1} y2:{y2} ratio:{ratio})")
    return ratio * (x2 - x1) + x1


def xval(cur, data_x, data_y):
    if cur < data_y[0] and cur < data_y[-1]:
        logger.warning("data_y below current target")
    if cur > data_y[0] and cur > data_y[-1]:
        logger.warning("data_y above current target")
    indx = 0
    try:
        while data_y[indx] < cur:
            indx += 1
    except:
        return float("NaN")
    if indx == 0:
        return float("NaN")
    indx -= 1
    return linear_y_interp(
        data_x[indx], data_x[indx + 1], data_y[indx], data_y[indx + 1], cur
    )


def yval(data_x, data_y, x_val):
    """
    return y value at given x value.
    Will interpolate if x-value is not exactly in the dataset.


    Args:
        data_x (List[float]): list of x values
        data_y (List[float]): list of y values
        x_val (float): 

    Returns: y_val (float)
        
    """
    indx = 0
    dir = "increasing"
    if data_x[0] > data_x[1]:
        dir = "decreasing"
    try:
        if dir == "increasing":
            while data_x[indx] < x_val:
                indx += 1
        elif dir == "decreasing":
            while data_x[indx] > x_val:
                indx += 1
    except:
        return float("NaN")
    indx -= 1
    return linear_X_interp(
        data_x[indx], data_x[indx + 1], data_y[indx], data_y[indx + 1], x_val
    )


def calc_vt(xvec, yvec, drain_bias):
    if len(xvec) != len(yvec):
        raise Exception("Bad input vector for VT Calc")
    if len(xvec) == 1:
        return False
    vt = 0.0
    max_delta = 0
    for i, y in enumerate(yvec):
        if 0 == i:
            continue
        if 0 == yvec[i - 1]:
            continue
        delta_y = yvec[i] - yvec[i - 1]
        if delta_y > max_delta:
            max_delta = delta_y
            vt = (
                xvec[i]
                - yvec[i] * ((xvec[i] - xvec[i - 1]) / delta_y)
                - 0.5 * drain_bias
            )
            bias_for_max_gm = 0.5 * (xvec[i] + xvec[i - 1])
            if i == len(yvec) - 1:
                logger.warning("Gm still rising at highest Vg bias.")
    return vt


def calc_max_gm(xvec, yvec):
    if len(xvec) != len(yvec):
        raise Exception("Bad input vector for VT Calc")
    if len(xvec) == 1:
        return False
    vt = 0.0
    max_delta = 0
    for i, y in enumerate(yvec):
        if 0 == i:
            continue
        if 0 == yvec[i - 1]:
            continue
        delta_y = yvec[i] - yvec[i - 1]
        if delta_y > max_delta:
            max_delta = delta_y
            if i == len(yvec) - 1:
                logger.warning("Gm still rising at highest Vg bias.")
    return max_delta / (xvec[1] - xvec[0])


def calc_vt_sat(xvec, yvec, drain_bias):
    if len(xvec) != len(yvec):
        raise (Exception("Bad input vector for VT Calc"))
    if 1 == len(xvec):
        return False
    vt = 0.0
    max_delta = 0
    yvec_root = list(map(lambda id: 0 if id < 0 else math.sqrt(id), yvec))
    for i, y in enumerate(yvec_root):
        if 0 == i:
            continue
        if 0 == yvec_root[i - 1]:
            continue
        delta_y = yvec_root[i] - yvec_root[i - 1]
        if delta_y > max_delta:
            max_delta = delta_y
            bias_for_max_gm = 0.5 * (xvec[i] + xvec[i - 1])
            rootid_at_max_gm = (yvec_root[i] + yvec_root[i - 1]) / 2.0
            vt = bias_for_max_gm - (
                rootid_at_max_gm / delta_y * (xvec[i] - xvec[i - 1])
            )
            if i == len(yvec_root) - 1:
                logger.warning("SQRT ID still rising at highest Vg bias.")

    return vt


def calc_id(data_x, data_y, vgg):
    return yval(data_x, data_y, vgg)


