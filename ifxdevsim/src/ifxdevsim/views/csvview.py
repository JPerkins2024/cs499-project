#! /usr/bin/env python
"""
Created on Wed Jun  7 08:36:59 CDT 2023


@author: wellsjeremy
"""


from .baseview import BaseView
from copy import deepcopy
from . import ViewError
from ..logger import Logger
import flatten_json
import csv
from functools import cache
from frozendict import frozendict
import os


class DsoCsvError(Exception):
    """Csv View Error"""

    pass


class CsvView(BaseView):

    VALID_CATEGORY_OPTIONS = ["show_categories"]
    MULTILEVEL = ["simulations"]

    def __init__(self, id, view_type, *args):
        super().__init__(id, view_type)

    def init_view(self, *args):
        self.header = dict()
        self.rows = []

    def add_param(self, id, param_hash):
        dup_hash = {"paramname": id}
        dup_hash.update(param_hash)
        self.add_rows(dup_hash)
        super().add_param(id, param_hash)

    def add_opts(self, opts):
        self.opts = opts

    def add_rows(self, hash: dict):
        for k, v in hash.items():
            if isinstance(v, dict):
                for q, r in v.items():
                    self.header[k] = self.header.get(k) or {}
                    if isinstance(r, dict):
                        for n, _m in r.items():
                            self.header[k][q] = self.header[k].get(q) or dict()
                            self.header[k][q][n] = True
                    else:
                        self.header[k][q] = True
            else:
                self.header[k] = True
        self.rows.append(hash)

    def to_dso(self):
        output_file = self.opts.get("filename", None) or f"{self.id}.dso.csv"
        output_dir = self.params[list(self.params.keys())[0]].get('_dirname',os.getcwd())

        with open(os.path.join(output_dir,output_file), "w") as fout:
            columns = self.opts.get("columns", False) or self.header
            columns = self.expand_columns(columns)
            self.check_header(columns)
            file_header = self.flatten_header_keys(
                self.freeze_nested_dict(columns), False, False
            )
            writer = csv.DictWriter(fout, file_header)
            writer.writeheader()
            for row in self.rows:
                flat_row = self.flatten_row(row)
                out_row = {}
                for k in file_header.keys():
                    v = flat_row[k]
                    if isinstance(v, list):
                        out_row[k] = ";".join(map(str, v))
                    else:
                        out_row[k] = v
                writer.writerow(out_row)

    def expand_columns(self, columns):
        new_columns: dict = deepcopy(columns)
        for k, v in columns.items():
            if not ((isinstance(v, dict) and v.get("all"))):
                continue
            merge_check = self.header.get(k, {})
            if type(new_columns.get(k)) == type(merge_check):
                merge_in = new_columns.get(k, {})
                merge_in.update(merge_check)
                new_columns[k].update(merge_in)
                for q, r in v.items():
                    if isinstance(new_columns[k], dict) and q in new_columns[k].keys():
                        new_columns[k][q] = r
                if "all" in new_columns[k].keys():
                    del new_columns[k]["all"]
                new_columns[k] = self.expand_columns(new_columns[k])
        if "all" in new_columns.keys():
            del new_columns["all"]
        return new_columns

    def flatten_row(self, hash):
        logger = Logger()
        flat_row = {}
        subh = self.flatten_header_keys(
            self.freeze_nested_dict(self.header), True, True
        )
        key_h = self.flatten_header_keys(self.freeze_nested_dict(self.header))
        for i, k in enumerate(subh.keys()):
            if len(k.split(":")) >= 2:
                keys: list = k.split(":")
                option_skip = False
                val = hash
                while not len(keys) == 0:
                    val = val.get(keys.pop(0),{})
                    if isinstance(val, dict) and len(val) == 0:
                        val = None
                        break
                act_k = list(key_h.keys())[i]
                flat_row[act_k] = val
            else:
                act_k = list(key_h.keys())[i]
                flat_row[act_k] = hash[k]
        return flat_row

    def freeze_nested_dict(self, to_freeze):
        out = dict()
        for k, v in to_freeze.items():
            if isinstance(v, dict):
                out[k] = self.freeze_nested_dict(v)
            elif isinstance(v, list):
                out[k] = frozenset(v)
            else:
                out[k] = v
        return frozendict(out)

    def unfreeze_nested_dict(self, to_unfreeze):
        out = dict()
        for k, v in to_unfreeze.items():
            if isinstance(v, frozendict):
                out[k] = self.unfreeze_nested_dict(v)
            elif isinstance(v, frozenset):
                out[k] = list(v)
            else:
                out[k] = v
        return out

    @cache
    def flatten_header_keys(self, hash, show_categories=False, force=False):
        keys = []
        hash = self.unfreeze_nested_dict(hash)
        if not force:
            show_categories = hash.get("show_categories", False)
        force_show_categories = []
        check_data = {}
        for k, v in hash.items():
            if isinstance(v, dict) or isinstance(v, frozendict):
                check_data[k] = list(v.keys())

        for k, v in check_data.items():
            if any(
                map(
                    lambda q, r: q != k and any(map(lambda z: z in r, v)),
                    check_data.keys(),
                    check_data.values(),
                )
            ):
                force_show_categories.append(k)
        for k, v in hash.items():
            if isinstance(v, frozendict) or isinstance(v, dict):
                if k in CsvView.MULTILEVEL and not force:
                    subh = flatten_json.flatten(dict(v), separator=":")
                elif k in force_show_categories:
                    subh = flatten_json.flatten(dict(v), separator=":")
                else:
                    #subh = self.flatten_header_keys(v, show_categories, force)
                    subh = flatten_json.flatten(dict(v), separator=":")
                for q, r in subh.items():
                    if q in CsvView.VALID_CATEGORY_OPTIONS:
                        continue

                    if (
                        (not show_categories and v.get("show_categories", True))
                        or self.opts.get("show_categories")
                        or show_categories
                        or (k in force_show_categories)
                    ):
                        if r:
                            keys.append([f"{k}:{q}", r])
                    else:
                        keys.append([q, r])

            else:
                if v:
                    keys.append([k, v])
        return flatten_json.flatten(
            self.unfreeze_nested_dict(dict(keys)), separator=":"
        )

    def check_header(self, columns):
        for k in columns.keys():
            delete_keys = []
            if isinstance(columns[k], dict) and isinstance(self.header[k], dict):
                for v, r in self.header[k].items():
                    if (
                        "all" in columns[k].keys()
                        and columns[k]["all"]
                        and v not in columns[k].keys()
                    ):
                        columns[k][v] = r
                    elif k in CsvView.MULTILEVEL:
                        tmp_config = columns[k]
                        [
                            not self.header[k][delete_k] and delete_keys.push(delete_k)
                            for delete_k in tmp_config.keys()
                        ]
                        columns[k][v] = columns[k].get(v, {})
                        for tmp_k, tmp_v in tmp_config.items():
                            if not self.header[k].get(tmp_k):
                                columns[k][v][tmp_k] = tmp_v
                    if (
                        v not in self.header[k]
                        and v not in CsvView.VALID_CATEGORY_OPTIONS
                    ):
                        raise (
                            DsoCsvError(
                                f"Unknown key {k}:{v} requested for output csv",
                            )
                        )
                for to_del in delete_keys:
                    del columns[k][to_del]
                if "all" in columns[k].keys():
                    del columns[k]["all"]
            if k not in self.header and k not in CsvView.VALID_CATEGORY_OPTIONS:
                raise (DsoCsvError(f"Unknown key {k} requested for output csv"))

    def print_example_config(self):
        content = """
        # Replace filename with output dso.csv name
        # The columns option specifies desired columns in output csvs.
        # Columns are specified in the same hierarchy as the dso.yml output.  
        #  all: true means everything under that dictionary will be printed.
        #  show_categories sets everything underneath that setting to print a colon delimited header of the entire dict hierarchy if true.  -> ex: If true , header will be definitions:vdd, if false, header will be vdd.
        views:
          FILENAME:
            type: csv
            columns:
              show_categories: false
              device: true
              metrics: true
              definitions:
                all: false
                vdd: true
              instance parameters:
                all: true
              stimuli: 
                show_categories: true
                all: true
              stress stimuli: 
                show_categories: true
                all: true
              simulations:
                all: true 
        """
        print(content)



