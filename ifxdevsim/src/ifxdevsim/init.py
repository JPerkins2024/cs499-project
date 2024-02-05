import os
import yaml
from .config_loader import config
from .cli import cli
from .logger import Logger

class Init:
    def find_config(self):
        logger = Logger()
        config_path = None
        search_path = os.getcwd()
        while(1):
            if os.path.realpath(search_path) == "/":
                logger.info("Hit root")
                break
            if os.path.isfile(search_path) and open(search_path).writable() == False:
                break
            if os.path.isfile("{search}/devsim_config.yml".format(search = search_path)):
                config_path = search_path
                break
            search_path = search_path + "/.."
            logger.info(search_path)
        return config_path
    
    def find_techfile(self, conf, config_path):
        if os.path.exists("./devsim.tf"):
            techfile = "./devsim.tf"

        elif os.path.exists("{config_path}/devsim.tf".format(config_path = config_path)):
            techfile = "{config_path}/devsim.tf".format(config_path = config_path)
        
        elif os.path.exists("{conftp}/info/tools/devsim/devsim.tf".format(conftp = conf['tech pointer'])):
            techfile = "{conftp}/info/tools/devsim/devsim.tf".format(conftp = conf['tech pointer'])
        
        else:
            techfile = None
        return techfile
    
    
