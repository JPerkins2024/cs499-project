#! /usr/bin/env python
"""
Created on Tue Jul 25 13:30:57 CDT 2023


@author: wellsjeremy
"""
import pytest
from ifxdevsim.calculator import resolve_expressions




def test_resolve_expression_simple():
    test_data = dict(
        device='nshort',
        definitions=dict(
            device_type = 'nmos',
            vdd=3.3,
            vgg=3.3
        ),
        stimuli = dict(
            vd='vdd',
            vg='vgg',
        ),
        control = dict(
            temperature=25,
        )
    )
    techdata = dict(
        techdata=dict(
            control=dict(),
            definitions=dict(),
            corners=dict(),
        )
    )
    test_h = resolve_expressions(test_data,techdata)
    assert test_h['stimuli']['vd'] == 3.3
    assert test_h['stimuli']['vg'] == 3.3
    assert test_h['definitions']['device_type'] == 'nmos'


def test_resolve_complex():
    test_data = dict(
        device='nshort',
        definitions=dict(
            device_type = 'nmos',
            vdd=3.3,
            vgg=3.3,
            itar='cc * w / l',
            cc=1.0e-7,
        ),
        stimuli = dict(
            vd='vdd',
            vg='vgg',
        ),
        control = dict(
            temperature=25,
        ),
    )
    test_data['instance parameters']=dict(
            w=2e-6,
            l=3e-6
        )
    techdata = dict(
        techdata=dict(
            control=dict(),
            definitions=dict(),
            corners=dict(),
        )
    )
    test_h = resolve_expressions(test_data,techdata)
    test_itar = (1.0e-7*2e-6/3e-6)
    assert test_h['definitions']['itar'] == test_itar
