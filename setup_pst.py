import os, sys
import pandas as pd
import numpy as np
import flopy
import pyemu

mf6_exe = 'mf6'

# set paths, relative to cwd
data_dir = 'data'
gis_dir = 'gis'
tpl_ml_dir = 'ml_tpl'
org_ml_dir = 'ml'
pst_dir = 'pst'

pst_name_suffix = ''

# set path, relative to ml dir
com_ext_dir = 'com_ext'

# set paths, relative to case_dirs
sim_dir =  'sim' 
ext_dir = 'ext'

# parameter upper/lower bounds 
par_df = pd.read_excel(os.path.join(data_dir,'par.xlsx'), index_col = 0)

# ---- load mf model and set spatial reference (grid cell centroids)
model_name = 'ml' 

sim = flopy.mf6.MFSimulation.load(sim_ws=tpl_ml_dir,exe_name=mf6_exe)

ml = sim.get_model(model_name)
ncpl = ml.modelgrid.ncpl

sr = {i:(x,y) for i,x,y in zip(range(ncpl),
    ml.modelgrid.xcellcenters,ml.modelgrid.ycellcenters)}

# ---- initialize PstFrom instance 
pf = pyemu.utils.PstFrom(original_d=org_ml_dir, new_d=pst_dir,
                 remove_existing=True,spatial_reference=sr,
                 longnames=True,
                 zero_based=False)

# fetch list of case directories
case_dirs = sorted([d for d in os.listdir('ml') if d.startswith('ml_')])[:-1]

# --- Process case independent parameters
# a = twice largest spacing between pp
v = pyemu.geostats.ExpVario(contribution=1.0,a=2000.)
grid_gs = pyemu.geostats.GeoStruct(variograms=v, transform='log')

prop_filename =os.path.join('com_ext','k.txt')
pp_filename =os.path.join('..',gis_dir,'pp_refined.shp')

zone_array = np.ones((1,ml.modelgrid.ncpl))
pargp='hk'

pp_df = pf.add_parameters(filenames=prop_filename, par_type="pilotpoint",
                   par_name_base='hk',pargp=pargp, geostruct=grid_gs,
                   lower_bound=par_df.loc[pargp,'faclbnd'], upper_bound=par_df.loc[pargp,'facubnd'],
                   ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                   zone_array=zone_array,pp_space=pp_filename)

# get names of outer pp (will be tied)
ppo_idx = pp_df.loc[pp_df.name.str.startswith('ppo')].index

# recharge
prop_filename = os.path.join('com_ext','rech_spd_1.txt')
pargp = 'rech'  
pf.add_parameters(filenames=prop_filename, 
                  par_name_base='rc',
                  pargp=pargp,
                  lower_bound=par_df.loc[pargp,'faclbnd'], upper_bound=par_df.loc[pargp,'facubnd'],
                  ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                  par_type='constant')

# ghb cond
prop_filename = os.path.join('com_ext','ghb_spd_1.txt')
pargp='cghb'
pf.add_parameters(filenames=prop_filename, 
                  par_name_base='d',
                  pargp=pargp, index_cols=[4], 
                  use_cols=[3],
                  lower_bound=par_df.loc[pargp,'faclbnd'], upper_bound=par_df.loc[pargp,'facubnd'],
                  ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                  par_type='grid')

# -- Iterate over cases
for case_dir in case_dirs:

    case_id = int(case_dir.split('_')[1])

    # --- Case-dependent parameter processing 

    # drn cond
    prop_filename = os.path.join(case_dir,'ext','drn_spd_1.txt')
    pargp='cdrn'
    pf.add_parameters(filenames=prop_filename, 
                      par_name_base=['cond'],
                      pargp=pargp, index_cols=[4], 
                      use_cols=[3],
                      lower_bound=par_df.loc[pargp,'faclbnd'], upper_bound=par_df.loc[pargp,'facubnd'],
                      ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                      par_type='grid')

    # river cond
    prop_filename = os.path.join(case_dir,'ext','riv_spd_1.txt')
    pargp='criv'
    pf.add_parameters(filenames=prop_filename, 
                      par_name_base='riv',
                      pargp=pargp, index_cols=[6], 
                      use_cols=[3],
                      lower_bound=par_df.loc[pargp,'faclbnd'], upper_bound=par_df.loc[pargp,'facubnd'],
                      ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                      par_type='grid')

    # --- Observation processing
    # heads
    hds_filename = os.path.join(case_dir,sim_dir,'hds.csv')

    hds_df = pf.add_observations(hds_filename, insfile=hds_filename+'.ins',
            index_cols='time', obsgp = 'heads',
            prefix='h')

    # drain discharge
    drn_filename = os.path.join(case_dir,sim_dir,'drn.csv')

    drn_df = pf.add_observations(drn_filename, insfile=drn_filename+'.ins',
            index_cols=0, prefix='q', obsgp = 'qdrn')

    # mixing ratios 
    mr_filename = os.path.join(case_dir,sim_dir,'mr.csv')

    mr_df = pf.add_observations(mr_filename, insfile=mr_filename+'.ins',
            index_cols=0, prefix='mr',obsgp = 'mr')

pf.add_py_function('helpers.py','run_cases()',is_pre_cmd=False)
pf.add_py_function('helpers.py','run_case()',is_pre_cmd=None)
pf.add_py_function('helpers.py','ptrack_pproc()',is_pre_cmd=None)
pf.add_py_function('helpers.py','compute_glob()',is_pre_cmd=None)

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
par.loc[drn_tied_idx,'partrans'] = 'tied'

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
cov_mat = grid_gs.covariance_matrix(pp_df.x,pp_df.y,pp_df.parnme)
# mind that no warning is generated when names in cov_mat do not match names in pst
pyemu.helpers.first_order_pearson_tikhonov(pst,cov_mat,reset=False,abs_drop_tol=0.2)

# regularization settings
pst.reg_data.phimlim = phimlim*1.5
pst.reg_data.phimaccept = pst.reg_data.phimlim*1.1
pst.reg_data.fracphim = 0.1
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
pst.parameter_groups.loc[ pst.parameter_groups.index,'forcen'] = 'always_3'
pst.parameter_groups.loc[ pst.parameter_groups.index,'dermthd'] = 'best_fit'

pst.parameter_groups.loc[ pst.parameter_groups.index,'derinc'] = 0.10
pst.parameter_groups.loc['hk',"derinc"] = 0.15

# ---- write pst   
pst_name = f'cal{pst_name_suffix}.pst' 
pst.write(os.path.join(pf.new_d,pst_name ))

# ---- run  pst with noptmax=0
pyemu.helpers.run(f'pestpp-glm {pst_name}', cwd=pf.new_d)

# write pst with noptmax =30
pst.control_data.noptmax=30
pst.write(os.path.join(pf.new_d, pst_name))

# start workers
pyemu.helpers.start_workers("pst",'pestpp-glm',pst_name,num_workers=64,
                              worker_root= 'workers',cleanup=False,
                                master_dir='master_glm')
