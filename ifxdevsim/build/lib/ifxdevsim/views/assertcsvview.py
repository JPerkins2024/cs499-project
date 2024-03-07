#! /usr/bin/env python
"""
Created on Thu Jun  8 08:35:36 CDT 2023


@author: wellsjeremy
"""

from .csvview import CsvView
from .viewerrors import ViewNotImplementedError

class AssertCsvView(CsvView):
    def to_dso(self):
        raise(ViewNotImplementedError, f"{self.__class__.name} is not yet implemented")

