#! /usr/bin/env python
"""
Created on Wed Jun 21 07:29:42 CDT 2023


@author: wellsjeremy
"""

#from ifxpymdm import Mdm, Sweep
from .logger import Logger
import os
import re
import ruamel.yaml
yaml=ruamel.yaml.YAML()
import socket
from .metrics import MdmParser
from copy import copy, deepcopy
from .meas_files.mdmhelper import MdmHelper
from .meas_files.dathelper import DatHelper
from .meas_files.meahelper import MeaHelper
from .utils import is_number, listfiles, get_site, to_number


class MeasHelper:
    def __init__(self, techdata):
        self.techdata = techdata
        self.update_device_map = False
        if os.path.isfile("devsim_device_map.yml"):
            with open("devsim_device_map.yml", "r") as f:
                self._device_map = yaml.load(f)
        else:
            self._device_map = dict()
            self._device_map["mdm"] = dict(default=dict())
            self._device_map["dat"] = dict(default=dict())
            self._device_map["mea"] = dict(default=dict())
        self.mdmhelper = MdmHelper(techdata)
        self.mdmhelper._device_map = self._device_map.get("mdm", {})
        self.dathelper = DatHelper(techdata)
        self.dathelper._device_map = self._device_map.get("dat", {})
        self.meahelper = MeaHelper(techdata)
        self.meahelper._device_map = self._device_map.get("mea", {})

    def import_dir(self, dir):
        self.mdmhelper.import_dir(dir)
        self.dathelper.import_dir(dir)
        self.meahelper.import_dir(dir)

    def create_meas_objects(self):
        self.mdmhelper.create_mdms()
        self.dathelper.create_datfiles()
        self.meahelper.create_meafiles()

    def write_device_map(self):
        logger = Logger()
        if any(
            [self.mdmhelper.update_device_map, self.dathelper.update_device_map]
        ) or not os.path.exists("devsim_device_map.yml"):
            logger.info(
                """
Writing guess of new device_types into devsim_device_map.yml
Edit this file and regenerate the dsi to have the correct values.
For MDM Files: This is keyed on the devtechno field in the mdm files and polarity.
For DAT Files: Group relevant files together using file globs.
For MEA Files: Use the same methodology as dat file.
"""
            )
            self._device_map["mdm"] = self.mdmhelper.device_map
            self._device_map["dat"] = self.dathelper.device_map
            self._device_map["mea"] = self.meahelper.device_map
            with open("devsim_device_map.yml", "w") as f:
                yaml.dump(self._device_map,f)

    def write_iv_dsi_file(self, file):
        logger = Logger()
        logger.info(f"Writing to {file}")
        out = dict()
        out["default"] = dict()
        out["default"]["control"] = dict()
        if (
            self.techdata.get("techdata", {})
            .get("control", {})
            .get("corners", {})
            .get("measure", False)
        ):
            out["default"]["control"]["corners"] = self.techdata["techdata"]["control"][
                "corners"
            ].get("measure")
            out["default"]["control"]["models path"] = self.techdata["techdata"][
                "control"
            ]["models path"]
            out["default"]["control"]["simulator"] = self.techdata["techdata"][
                "control"
            ]["simulator"]
        if len(self.mdmhelper.mdms) > 0:
            out.update(self.mdmhelper.gen_iv_dsi_file())
        if len(self.dathelper.dats) > 0:
            out.update(self.dathelper.gen_iv_dsi_file())
        if len(self.meahelper.meafiles) > 0:
            out.update(self.meahelper.gen_iv_dsi_file())
        with open(file, "w") as f:
            yaml.dump(out,f)


    def append_control_structures(self,out):
        if (
            self.techdata.get("techdata", {})
            .get("control", {})
            .get("corners", {})
            .get("measure", False)
        ):
            out["default"]["control"]["corners"] = self.techdata["techdata"]["control"][
                "corners"
            ].get("measure")
        if (
            self.techdata.get("techdata", {})
            .get("control", {})
            .get("models path",False)
        ):
            out["default"]["control"]["models path"] = self.techdata["techdata"][
                "control"
            ]["models path"]
        if (
            self.techdata.get("techdata", {})
            .get("control", {})
            .get("simulator",False)
        ):
            out["default"]["control"]["simulator"] = self.techdata["techdata"][
                "control"
            ]["simulator"]


    def write_metric_dsi_file(self, file):
        logger = Logger()
        out = dict()
        out["default"] = dict()
        out["default"]["control"] = dict()
        out["default"]["views"] = dict()
        self.append_control_structures(out)
        view_dict = out["default"]["views"][re.sub(".dsi.yml", "", file)] = dict(
            type="csv", columns=dict(show_categories=False),
        )
        view_dict["columns"]["device"] = True
        view_dict["columns"]["metrics"] = True
        view_dict["columns"]["instance parameters"] = dict(all=True)
        view_dict["columns"]["stimuli"] = dict(all=True)
        view_dict["columns"]["simulations"] = dict(all=True)
        if len(self.mdmhelper.mdms) > 0:
            out.update(self.mdmhelper.gen_metric_dsi_file())
        if len(self.dathelper.dats) > 0:
            out.update(self.dathelper.gen_metric_dsi_file())
        if len(self.meahelper.meafiles) > 0:
            out.update(self.meahelper.gen_metric_dsi_file())
        with open(file, "w") as f:
            yaml.dump(out,f)

    def write_meas_list(self, file):
        with open(file, "w") as fout:
            if len(self.mdmhelper.mdms) > 0:
                self.mdmhelper.write_meas_list(fout)
            if len(self.dathelper.dats) > 0:
                self.dathelper.write_meas_list(fout)
            if len(self.meahelper.meafiles) > 0:
                self.meahelper.write_meas_list(fout)

    def read_meas_list(self, file):
        if os.path.exists(file):
            with open(file, "r") as fin:
                for line in fin:
                    site, path, *rest = line.split(" ")
                    if line[0] == "#":
                        continue
                    if os.path.splitext(path)[1] == ".mdm":
                        self.mdmhelper.handle_meas_list_line(site, path, *rest)
                    if os.path.splitext(path)[1] == ".dat":
                        self.dathelper.handle_meas_list_line(site, path, *rest)
                    if os.path.splitext(path)[1] == ".mea":
                        self.meahelper.handle_meas_list_line(site, path, *rest)
