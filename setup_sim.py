import os, sys, shutil
import re
import pandas as pd
import numpy as np
import flopy
import pyemu
import helpers

# --- settings
mf6_exe = 'mf6'

# parameter data (initial values)
par_df = pd.read_excel(os.path.join('data','par.xlsx'), index_col = 0)

# simulation directory
sim_dir = 'sim'

# calibrated model 
org_model_ws = os.path.join('pst','ml_01')

# temporary model 
tmp_model_ws = os.path.join(sim_dir,'tmp')

# simulation model  
sim_model_ws = os.path.join(sim_dir,'sim')

# ---- processing

# clear dirs
helpers.clear_dirs([tmp_model_ws,sim_model_ws])

# clear dir and cp calibrated model
if os.path.exists(tmp_model_ws): shutil.rmtree(tmp_model_ws)

shutil.copytree(org_model_ws, tmp_model_ws)

# load original model with props from ../com_ext
sim = flopy.mf6.MFSimulation.load(sim_ws=org_model_ws, exe_name=mf6_exe)

# set all_data_internal and write to tmp dir
sim.set_sim_path(tmp_model_ws)
sim.write_simulation() 
sim.tdis.perioddata = [ (1, 1, 1) ]

# clear former ext files 
ext_dir = os.path.join(tmp_model_ws,'ext')
helpers.clear_dirs([ext_dir])

# set simulation parameter data as external 
ml = sim.get_model('ml')
ml.drn.stress_period_data.store_as_external_file(os.path.join('ext','drn_spd.txt'))
ml.wel.stress_period_data.store_as_external_file(os.path.join('ext','wel_spd.txt'))

# write simulation with new external files 
sim.write_simulation()

# run model 
helpers.run_case(case_dir=tmp_model_ws)

# ---- initialize PstFrom instance 
pf = pyemu.utils.PstFrom(original_d=tmp_model_ws, new_d=sim_model_ws,
                 remove_existing=True,
                 longnames=True,
                 zero_based=False)

# ---- parameters  

# drn levels 
prop_file = os.path.join('ext','drn_spd_1.txt')
pargp='hdrn'
hdrn_df = pf.add_parameters(filenames=prop_file, 
                  par_name_base='h',
                  pargp='hdrn', index_cols=[4], 
                  use_cols=[2],
                  transform='none',
                  par_type='grid',
                  par_style='direct')

# well discharge rate  
prop_file = os.path.join('ext','wel_spd_1.txt')
qwel_df = pf.add_parameters(filenames=prop_file, 
                  par_name_base='q',
                  pargp='qwel', index_cols=[3], 
                  use_cols=[2], use_rows=[7,8],
                  transform='none',
                  par_type='grid',
                  par_style='direct')

# ---- observations 

# mixing ratios 
mr_file = os.path.join('sim', 'mr.csv')

mr_df = pf.add_observations(mr_file, insfile=mr_file+'.ins',
        index_cols=0, prefix='mr', obsgp = 'mr')

# discharge values 
q_file = os.path.join('sim','q.csv')

q_df = pf.add_observations(q_file, insfile=q_file+'.ins',
        index_cols=0, prefix='q',obsgp = 'q')

# global values
glob_file = os.path.join('sim','glob.csv')

glob_df = pf.add_observations(glob_file, insfile=glob_file+'.ins',
        index_cols=0, prefix='glob',obsgp = 'glob')

pf.add_py_function('helpers.py', 'run_case()',is_pre_cmd=False)
pf.add_py_function('helpers.py', 'ptrack_pproc()',is_pre_cmd=None)
pf.add_py_function('helpers.py', 'compute_glob()',is_pre_cmd=None)

# ---- build Pst  
pst = pf.build_pst()

par = pst.parameter_data

# get parnames to query par_df excel file 
idx = (par.pname.str.upper() + '_' + par.idx0.str.upper()).values
par['parval1'] = par_df.loc[idx,'val'].values
par['parlbnd'] = par_df.loc[idx,'parlbnd'].values
par['parubnd'] = par_df.loc[idx,'parubnd'].values

# set obsval to 0.
obs = pst.observation_data
obs['obsval']=0.

# replace python by python3
pst.model_command = ['python3 forward_run.py'] 

# test model run with pest
pst_name = 'sim.pst'
pst.write(os.path.join(pf.new_d, pst_name))
pyemu.helpers.run(f'pestpp-glm {pst_name}', cwd=pf.new_d)


# --- setup pest-free model interface 

# write initial parameter value file 
parfile = os.path.join(pf.new_d,'par.dat')

with open(parfile,'w') as f:
    f.write(par['parval1'].to_string())

# write ml_info file for helpers.run()
tpl_files = pst.template_files
col_idx = [2,2]
info_df = pd.DataFrame({'tpl_file':tpl_files,'col_idx':col_idx})
info_file = os.path.join(pf.new_d,'ml_info.csv')
info_df.to_csv(info_file,index=False)

# check model run 

import helpers
cwd = 'sim/sim'
helpers.run(cwd=cwd)

