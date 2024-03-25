#! /usr/bin/env python
"""
Created on Thu Jun  8 14:08:31 CDT 2023


@author: wellsjeremy
"""

from .viewerrors import ViewError
from .csvview import CsvView
from .assertcsvview import AssertCsvView
from .baseview import BaseView
from .tableview import TableView
from .texgraphview import TexGraphView
from ..logger import Logger
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import enlighten

views = {}
valid_views = {
    "csv": CsvView,
    "assert_csv": AssertCsvView,
    "table": TableView,
    "texgraph": TexGraphView,
}


def get_views():
    global views
    return views


def clear_views():
    global views
    views = {}


def print_config(viewname):
    get_view_type(viewname)("dum").print_example_config()


def print_valid_views():
    logger = Logger()
    logger.info("Valid Views: " + " ".join(valid_views.keys()))


def create_views(data: dict, debug=False):
    """
    create_views(data: dict)
    Where data is a dso.yml (nested dict) with parameter objects.
    This filters for parameters requesting a view and generates the views based on the configuration.
    """
    has_views = dict(filter(lambda k: "views" in k[1].keys(), data.items()))
    for paramid, par_h in has_views.items():
        if not isinstance(par_h, dict):
            continue
        for view_id, view_opts in par_h["views"].items():
            if view_id == "default":
                view_id = paramid
            if not view_opts["type"]:
                raise (ViewError, "Need view type under #{paramid}: #{view_id}")
            initialize_view(view_id, view_opts["type"])
            view_opts = view_opts.copy()
            del view_opts["type"]
            setup_view(view_id, paramid, has_views[paramid], view_opts)
    jobs = []
    logger = Logger()
    logger.info("Creating views...")
    manager = enlighten.get_manager()
    bar_format = "{desc}{desc_pad}{percentage:3.0f}%|{bar}| [elapsed: {elapsed}] [remaining: {eta}]"
    counter = None
    if not debug:
        counter = manager.counter(
            total=len(views.values()), desc="Creating views:", bar_format=bar_format
        )
        counter.refresh

    def make_and_update(v, counter):
        logger = Logger()
        try:
            v.to_dso()
        except Exception as e:
            logger.fatal(
                "View generation failed!  rerun with -d argument to get error message"
            )
        counter.update()
        counter.refresh()

    if not debug:
        with ThreadPoolExecutor(max_workers=8) as executor:
            for view in views.values():
                executor.submit(make_and_update, view, counter)

        counter.clear()
        counter.close()
    else:
        for viewid,view in views.items():
            logger.debug(f"Creating {viewid}: {view}")
            view.to_dso()



def get_pdf_outputs():
    pdfs = []
    for viewid,view in views.items():
        if getattr(view,"pdfname",False):
            pdfs.append(view.pdfname)
    return pdfs


    


def initialize_view(id, view_type):
    views[id] = views.get(id) or get_view_type(view_type)(id, view_type)


def get_view_type(view_type):
    return valid_views.get(view_type, BaseView)


def setup_view(id, paramid, in_hash, opts):
    new_hash = deepcopy(in_hash)
    del new_hash["views"]
    views[id].add_opt(opts)
    views[id].add_param(paramid, new_hash)
