#! /usr/bin/env python
"""
Created on Wed May 31 10:00:29 CDT 2023


@author: wellsjeremy
"""
from . import views
from . import devsim
from . import measures




def main():
    dev = devsim.DevSim()
    dev.main()


if __name__ == "__main__":
    main()
