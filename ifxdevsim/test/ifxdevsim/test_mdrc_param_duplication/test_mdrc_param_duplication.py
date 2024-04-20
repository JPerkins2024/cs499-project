import pytest
import sys
from ifxdevsim.devsim import DevSim
import subprocess

#command = [i]
print(sys.argv)
sys.argv = ["dvsim","-i", " mdrc.dsi.yml","-tf","mxs8.tf.yml"]
command = ["dvsim","-i", "~/cs499project/cs499-project/ifxdevsim/test/ifxdevsim/test_mdrc_param_duplication/mdrc.dsi.yml","-tf","~/cs499project/cs499-project/ifxdevsim/test/ifxdevsim/test_mdrc_param_duplication/mxs8.tf.yml"]
print(sys.argv)
subprocess.Popen(command)
#DevSim()
