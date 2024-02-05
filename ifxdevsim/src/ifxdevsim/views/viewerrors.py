#! /usr/bin/env python
"""
Created on Thu Jun  8 13:34:11 CDT 2023


@author: wellsjeremy
"""

class ViewError(Exception):
    "Generic View Error"
    pass


class ViewNotImplementedError(Exception):
    "Raised when requested view is not implemented"
    pass
