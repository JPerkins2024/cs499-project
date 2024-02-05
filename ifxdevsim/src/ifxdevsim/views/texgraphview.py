#! /usr/bin/env python
"""
Created on Tue Sep 12 14:52:54 CDT 2023


@author: wellsjeremy
"""

from .LaTeX.latex import Plot
from .baseview import BaseView
from ..logger import Logger
import itertools
import os

class TexGraphView(BaseView):

    
    def add_param(self, id, param_hash):
        logger = Logger()
        sim_hash = param_hash['simulations']
        if len(sim_hash) == 0:
            logger.warning(f"No simulation data in param id {id}.  Graph generation may fail")
        for corner,corner_hash in sim_hash.items():
            if "sweep" not in corner_hash:
                if "nominal" in corner_hash and "sweep_convert" in self.opts:
                    sweep_conv= self.opts['sweep_convert']
                    corner_hash['sweep'] = [[sweep_conv['x'],sweep_conv.get('p',None),corner_hash['nominal']]]
                else:
                    logger.fatal(f"There is no sweep in {corner} for parameter {id}.  Graph views only support sweep types.")
        super().add_param(id, param_hash)


    def get_config(self,corner):
        config = self.opts['config']
        new_config = dict()
        for name,conf in config.items():
            if isinstance(conf,dict):
                if conf.get(corner):
                    new_config[name] = conf[corner]
                else:
                    new_config[name] = conf.get('default')
            else: 
                new_config[name] = conf
        return config
        

    def to_dso(self):
        sweep_data = dict()
        for parid, par in self.params.items():
            sims = par['simulations']
            os.makedirs(os.path.join(par['_dirname'],'plots'),exist_ok=True)
            for corner, sim_dict in sims.items():
                sim_sweep_data = sim_dict['sweep']
                sweep_data[corner] = sweep_data.get(corner) or dict()
                sweep_data[corner]['data'] = sweep_data[corner].get('data') or dict()
                sweep_data[corner]['config'] = sweep_data[corner].get('config') or self.get_config(corner)
                sweep_data[corner]['config']['dirname'] = par['_dirname']
                if sweep_data[corner]['config']['title'] == "default":
                    sweep_data[corner]['config']['title'] = parid
                for key, group in itertools.groupby(sim_sweep_data, lambda x: x[1]):
                    sweep_data[corner]['data'][key] = sweep_data[corner]['data'].get(key) or []
                    x = list(group)
                    sweep_data[corner]['data'][key].extend(list(filter(lambda q: q[1] != "fail",map(lambda q: [q[0],q[2]],x))))
        plot =Plot(sweep_data,self._id)
        if getattr(plot,"pdfname",False):
            self.pdfname = plot.pdfname

    def print_example_config(self):
        content = """
# This is not an exhaustive configuration.  Any options are under config are added to the plot options.  Latex will sometimes warn about invalid options, but devsim will check if a plot is generated.
# All plots are generated under the plots directory in the same directory as the dsi.yml.
# See pgfplots documentation for full set of plot options: https://tikz.dev/pgfplots/reference-2dplots
# If a key is set to true, it is not a parameterized setting, it it will just print the key value. (e.g only marks)
# Parameterized parameters will print <param>=<value>
# Corner_specific defines settings for specific corners.  In this case measure is counted as a corner.
# Setting the rawdata flag will also print a raw data csv file in the plots directory.
views:
    FILENAME:
        type: texgraph
        config:
          title: TITLE
          xlabel: XLABEL
          ylabel: YLABEL
          plabel: PLABEL
          rawdata: true
          x dir: reverse
          y dir: reverse
          corner_specific:
            measure:
              only marks: true
              thin: true
              mark: o
              mark size: 1pt
            default:
              no markers: true
              solid: true

        """
        print(content)






