import argparse
import yaml
import os

class _Config:
    def __init__(self):
        
        #with open(os.path.join(os.sep.join(os.getcwd().split(os.sep)[:-1]),'conf','config.yml')) as yamlConfig:
        with open(os.path.join(os.path.dirname(__file__), '../conf/config.yml')) as yamlConfig:
            self.config = yaml.safe_load(yamlConfig)

    def __getitem__(self, name):
        try: 
            return self.config[name]
        except KeyError:
            print("No attr found")

    def get(self,name,default=None):
        return self.config.get(name,default)

            


config = _Config().config

