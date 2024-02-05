#! /usr/bin/env python
"""
Created on Thu Jun  8 10:58:39 CDT 2023


@author: wellsjeremy
"""


import pytest
import yaml
import os
import csv


from ifxdevsim.views import (
    BaseView,
    CsvView,
    AssertCsvView,
    TableView,
    create_views,
    initialize_view,
    get_view_type,
    setup_view,
    get_views,
    clear_views,
)


@pytest.fixture
def setup_create_views():
    print("Setup called")
    clear_views()


def test_get_view_type():
    value = get_view_type("dum")
    assert value == BaseView
    value = get_view_type("csv")
    assert value == CsvView
    value = get_view_type("assert_csv")
    assert value == AssertCsvView


def test_create_views_empty(setup_create_views):
    create_views({"dum": {"dum2": {}}})
    assert len(get_views()) == 0


def test_create_views_some_data(setup_create_views):
    yaml_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "example",
        "input_output",
        "regression_rf_aps.dso.yml",
    )
    yaml_fs = open(yaml_file, "r")
    data = yaml.safe_load(yaml_fs)
    yaml_fs.close()
    example_csv = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "example",
        "input_output",
        "regression_rf_aps.dso.csv",
    )
    golden = open(example_csv, "r")
    gold_reader = csv.DictReader(golden)
    gold_data = []
    for dat in gold_reader:
        gold_data.append(dat)
    golden.close()
    create_views(data,True)
    new_data = []
    new_file = open("regression_rf_aps.dso.csv", "r")
    new_reader = csv.DictReader(new_file)
    for dat in new_reader:
        new_data.append(dat)
    new_file.close()
    assert len(get_views()) != 0
    assert len(new_data) == len(gold_data)
    for d1, d2 in zip(gold_data, new_data):
        checks = [
            "metrics",
            "device",
            "top_tt_esd:nominal",
            "toprf_tt:nominal",
            "w",
            "l",
            "wr",
            "lr",
            "nf",
            "nr",
            "s",
            "stm",
            "spm",
        ]
        for check in checks:
            assert d1[check] == d2[check]

    if os.path.exists("regression_rf_aps.dso.csv"):
        try:
            os.remove("regression_rf_aps.dso.csv")
        except OSError as e:
            print(f"Cleanup failed : {e}")

def test_tableview():
    """Docstring"""
    yaml_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "example",
        "input_output",
        "regression_rf_aps_table_test_data.dso.yml",
    )
    yaml_fs = open(yaml_file, "r")
    data = yaml.safe_load(yaml_fs)
    yaml_fs.close()
    create_views(data,True)
