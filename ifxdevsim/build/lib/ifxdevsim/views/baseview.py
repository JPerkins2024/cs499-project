#! /usr/bin/env python
"""
Created on Tue Jun  6 13:46:22 CDT 2023


@author: wellsjeremy
"""
from .viewerrors import ViewNotImplementedError


class BaseView:
    "Base class for views"

    def __init__(self, id, *args):
        self._id = id
        self._type = self.__class__.__name__
        self._params = {}
        self.init_view(*args)

    @property
    def params(self):
        return self._params

    @property
    def id(self):
        return self._id

    @property
    def type(self):
        return self._type

    def init_view(self, *args):
        pass

    def add_param(self, id: str, param_hash: dict):
        self.params[id] = self.params.get(id) or param_hash

    def add_opt(self, opts):
        self.opts = opts

    def to_dso(self):
        raise (
            ViewNotImplementedError,
            f"{self.__class__.name} is not implemented as a view!",
        )
    
    def print_example_config(self):
        print("Invalid view type requested")
