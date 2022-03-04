import os
import numpy as np 
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib as mpl
import flopy
import pyemu

# --- pst files 
cwd = 'pst'
org_pst_name ='cal_ml.pst'
eval_pst_name = 'jactest.pst'

par_file = os.path.join('pst_master',org_pst_name.replace('pst','par'))
parrep=True

# read pest file  
pst = pyemu.Pst(os.path.join(cwd, org_pst_name))

# parrep 
if parrep : pst.parrep(os.path.join(cwd,par_file))


# generate jactest run list
jactest_df = pyemu.helpers.build_jac_test_csv(pst,5)
jactest_df.to_csv(os.path.join(cwd,'jactest_in.csv'))


# sweep option
pst.pestpp_options['sweep_parameter_csv_file'] = 'jactest_in.csv'
pst.pestpp_options['sweep_output_csv_file'] = 'jactest_out.csv'

# write
pst.write(os.path.join(cwd,eval_pst_name))

# run
pyemu.helpers.start_workers(cwd,'pestpp-swp',eval_pst_name,num_workers=64,
                              worker_root= 'workers',cleanup=False,
                                master_dir='pst_master')

