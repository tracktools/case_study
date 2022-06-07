import os, sys, shutil
import re
import pandas as pd
import numpy as np
import flopy
import pyemu
import helpers

# --- settings
mf6_exe = 'mf6'

# simulation directory
sim_dir = 'sim'

# calibrated model 
org_model_ws = os.path.join('opt','ml_99')

# simulation model  
tmp_model_ws = os.path.join(sim_dir,'tmp')
sim_model_ws = os.path.join(sim_dir,'sim')

# ---- processing

# clear dir and cp calibrated model
if os.path.exists(tmp_model_ws):
    shutil.rmtree(tmp_model_ws)

shutil.copytree(org_model_ws, tmp_model_ws)

# load original model with props from ../com_ext
sim = flopy.mf6.MFSimulation.load(sim_ws=org_model_ws, exe_name=mf6_exe)

# set all_data_internal and write to tmp dir
sim.set_sim_path(tmp_model_ws)
sim.write_simulation() 
sim.tdis.perioddata = [ (99, 1, 1) ]

# clear former ext files 
ext_dir = os.path.join(tmp_model_ws,'ext')
helpers.clear_dirs([ext_dir])

# set simulation parameter data as external 
ml = sim.get_model('ml')
ml.riv.stress_period_data.store_as_external_file(os.path.join('ext','riv_spd_99.txt'))
ml.drn.stress_period_data.store_as_external_file(os.path.join('ext','drn_spd_99.txt'))
ml.wel.stress_period_data.store_as_external_file(os.path.join('ext','wel_spd_99.txt'))
ml.remove_package('obs')

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
prop_file = os.path.join('ext','drn_spd_99_1.txt')
pargp='hdrn'
hdrn_df = pf.add_parameters(filenames=prop_file, 
                  par_name_base='h',
                  pargp='hdrn', index_cols=[4], 
                  use_cols=[2],
                  transform='none',
                  par_type='grid',
                  par_style='direct')

# well discharge rate  
prop_file = os.path.join('ext','wel_spd_99_1.txt')
qwel_df = pf.add_parameters(filenames=prop_file, 
                  par_name_base='q',
                  pargp='qwel', index_cols=[3], 
                  use_cols=[2], use_rows=[7,8],
                  transform='none',
                  par_type='grid',
                  par_style='direct')


pst = pf.build_pst()
par = pst.parameter_data

par = pst.parameter_data 
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:bar','parval1'] = 9.
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:gal','parval1'] = 8.5
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21','parval1'] = -250./3600
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20','parval1'] = -250./3600


# write initial parameter value file 
parfile = os.path.join(sim_model_ws,'par.dat')

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

