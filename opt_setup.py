import os, sys
import pandas as pd
import numpy as np
import flopy
import pyemu

mf6_exe = 'mf6'

# settings
org_dir = 'pst_master'
opt_dir = 'opt'

cal_pst ='cal_ml.pst' # parameter estimation completed
par_file = org_pst_name.replace('pst','par') # final par file 
eval_pst_name = 'eval_ml.pst' # new pest file 

# run pest with final (calibrated) parameter values
pst = pyemu.Pst(os.path.join(org_dir, cal_pst))
pst.control_data.noptmax=0
pst.write(os.path.join(org_dir,eval_pst_name))
pyemu.helpers.run(f'pestpp-glm {eval_pst_name}', cwd=org_dir)

# fetch arbitrary case to constitute base model 
case_dir = sorted([d for d in os.listdir(org_dir) if d.startswith('ml_')])[0]

# load model and set spatial reference (grid cell centroids)
sim = flopy.mf6.MFSimulation.load(sim_ws=case_dir, exe_name=mf6_exe)
ml = sim.get_model('ml')
ncpl = ml.modelgrid.ncpl
sr = {i:(x,y) for i,x,y in zip(range(ncpl),
    ml.modelgrid.xcellcenters,ml.modelgrid.ycellcenters)}

# save model in new dir



# ---- initialize PstFrom instance 
pf = pyemu.utils.PstFrom(original_d=org_ml_dir, new_d=pst_dir,
                 remove_existing=True,spatial_reference=sr,
                 longnames=True,
                 zero_based=False)


# ---- parameters  


# drn levels 
prop_filename = os.path.join(case_dir,'ext','drn_spd_1.txt')
pargp='cdrn'
pf.add_parameters(filenames=prop_filename, 
                  par_name_base=['cond'],
                  pargp=pargp, index_cols=[4], 
                  use_cols=[3],
                  lower_bound=par_df.loc[pargp,'faclbnd'], upper_bound=par_df.loc[pargp,'facubnd'],
                  ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                  par_type='grid')



# well discharge rate  


# ---- observations 

# drain discharge
drn_filename = os.path.join(case_dir,sim_dir,'drn.csv')

drn_df = pf.add_observations(drn_filename, insfile=drn_filename+'.ins',
        index_cols=0, prefix='q', obsgp = 'qdrn')

# mixing ratios 
mr_filename = os.path.join(case_dir,sim_dir,'mr.csv')

mr_df = pf.add_observations(mr_filename, insfile=mr_filename+'.ins',
        index_cols=0, prefix='mr',obsgp = 'mr')

pf.add_py_function('helpers.py','run_cases()',is_pre_cmd=False)
pf.add_py_function('helpers.py','ptrack_pproc()',is_pre_cmd=None)

# ---- Build Pst  
pst = pf.build_pst()

# replace python by python3
pst.model_command = ['python3 forward_run.py'] 

# --- parameter processing
par = pst.parameter_data 

# tie outer pp to 1st outer pp
par.loc[ppo_idx[1:],'partrans'] = 'tied'
par.loc[ppo_idx[1:],'partied'] = ppo_idx[0]

# tie riv and drn conds to 1st case (inst)
par['inst']=par.inst.astype(int)
ninst = len(par.loc[par.pargp=='criv','inst'].unique())

riv_inst0_idx = par.loc[(par.pargp=='criv') & (par.inst == 0)].index
riv_tied_idx = par.loc[(par.pargp=='criv') & (par.inst > 0)].index

drn_inst0_idx = par.loc[(par.pargp=='cdrn') & (par.inst == 0)].index
drn_tied_idx = par.loc[(par.pargp=='cdrn') & (par.inst > 0)].index

par.loc[riv_tied_idx,'partrans'] = 'tied'

for i in range(1,ninst):
    # tie criv
    idx = par.loc[(par.pargp=='criv') & (par.inst == i)].index
    par.loc[idx,'partied'] = riv_inst0_idx.values
    # tie cdrn
    idx = par.loc[(par.pargp=='cdrn') & (par.inst == i)].index
    par.loc[idx,'partied'] = drn_inst0_idx.values


# ---- observation processing  
obs = pst.observation_data

# load observation data
surveys_df = pd.read_excel(os.path.join(data_dir,'surveys.xlsx'), index_col = 0)

# extract obs type and loc from (long) name
obs[['prefix','type','loc','time']] = obs.obsnme.apply(
    lambda x: pd.Series(
        dict([s.split(':') for s in x.split('_') if ':' in s])))

# get ob id and case
obs['id'] = obs[['prefix', 'loc']].agg('_'.join, axis=1).str.upper()
obs['case'] = obs['time'].astype(float).astype(int)

# set obs values from surveys df
obs['obsval'] = [surveys_df.loc[case_id,obs_id]
        for case_id,obs_id in zip(obs.case,obs.id)]

# convert discharge rates from m3/h to m3/s
obs.loc[obs.obgnme == 'qdrn','obsval'] = obs.loc[obs.obgnme == 'qdrn','obsval']*(-1./3600)

# convert mixing ratios from % to [-]
obs.loc[obs.obgnme == 'mr','obsval'] = obs.loc[obs.obgnme == 'mr','obsval']/100.


# adjusting weights from measurement error 
weights_df = pd.read_excel(os.path.join(data_dir,'weights.xlsx'), index_col = 0)

for obgnme in obs.obgnme.unique():
    # weighting based on measurement error 
    obs.loc[obs.obgnme==obgnme,'weight'] = 1./weights_df.loc[obgnme,'sigma']
    # magnifying tuning factor 
    obs.loc[obs.obgnme==obgnme,'weight'] = obs.loc[obs.obgnme==obgnme,'weight']*weights_df.loc[obgnme,'factor']


# 0-weight to unavailable obs
obs.loc[obs.obsval.isna(),['weight','obsval']]=0

# phimlim =  nobs*tuning_factor
phimlim = np.array(
        [ weights_df.loc[obgnme,'factor']*(obs.obgnme==obgnme).sum() 
    for obgnme in obs.obgnme.unique()]
    ).sum()


#=================

# Tikhonov reg 
pyemu.helpers.zero_order_tikhonov(pst)
cov_mat = grid_gs.covariance_matrix(pp_df.x,pp_df.y,pp_df.name)
pyemu.helpers.first_order_pearson_tikhonov(pst,cov_mat,reset=False,abs_drop_tol=0.2)

# regularization settings
pst.reg_data.phimlim = phimlim
pst.reg_data.phimaccept = pst.reg_data.phimlim*1.1
pst.reg_data.fracphim = 0.10
pst.reg_data.wfmin = 1.0e-10
pst.reg_data.wfinit = 1e-3
pst.reg_data.wfac = 1.5
pst.reg_data.wtol = 1.0e-2

# pestpp-glm options 
pst.pestpp_options['svd_pack'] = 'redsvd'
pst.pestpp_options['uncertainty'] = 'false'
pst.pestpp_options['der_forgive'] = True

# run manager options 
pst.pestpp_options['overdue_resched_fac'] = 2
pst.pestpp_options['panther_agent_no_ping_timeout_secs'] = 3600
pst.pestpp_options['max_run_fail'] = 5

# set derinc values for pp
#pst.parameter_groups.loc['hk',"derinc"] = 0.10

# ---- write pst   
pst.write(os.path.join(pf.new_d, f'cal_{model_name}.pst'))

# ---- run  pst   
pyemu.helpers.run(f'pestpp-glm cal_{model_name}.pst', cwd=pf.new_d)
pst.control_data.noptmax=30
pst.write(os.path.join(pf.new_d, f'cal_{model_name}.pst'))

# start workers
pyemu.helpers.start_workers("pst",'pestpp-glm','cal_ml.pst',num_workers=64,
                              worker_root= 'workers',cleanup=False,
                                master_dir='pst_master')

'''
import pyemu
pyemu.helpers.start_workers("pst",'pestpp-glm','cal_ml.pst',num_workers=40,
                              worker_root= 'workers',cleanup=False,
                                master_dir='pst_master')
'''
