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

# set path, relative to ml dir
com_ext_dir = 'com_ext'

# set paths, relative to case_dirs
sim_dir =  'sim' 
ext_dir = 'ext'

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
case_dirs = sorted([d for d in os.listdir('ml') if d.startswith('ml_')])

# --- Process case independent parameters
v = pyemu.geostats.ExpVario(contribution=1.0,a=300)
grid_gs = pyemu.geostats.GeoStruct(variograms=v, transform='log')

prop_filename =os.path.join('com_ext','k.txt')
pp_filename =os.path.join('..',gis_dir,'pp.shp')

zone_array = np.ones((1,ml.modelgrid.ncpl))
pp_df = pf.add_parameters(filenames=prop_filename, par_type="pilotpoints",
                   par_name_base="hk",pargp="hk", geostruct=grid_gs,
                   upper_bound=10.,lower_bound=0.1,ult_ubound=100,ult_lbound=0.01,
                   zone_array=zone_array,pp_space=os.path.join('..',gis_dir,'pp.shp'))

# get names of outer pp (will be tied)
ppo_idx = pp_df.loc[pp_df.name.str.startswith('ppo')].index

# recharge
prop_filename = os.path.join('com_ext','rech_spd_1.txt')
pf.add_parameters(filenames=prop_filename, 
                  par_name_base='rc',
                  pargp='rech', upper_bound=10.,
                  lower_bound=0.1,
                  par_type='constant')

# ghb cond
prop_filename = os.path.join('com_ext','ghb_spd_1.txt')
pf.add_parameters(filenames=prop_filename, 
                  par_name_base='d',
                  pargp='ghb', index_cols=[4], 
                  use_cols=[3], upper_bound=10.,
                  lower_bound=0.1,
                  par_type='grid')

# -- Iterate over cases
for case_dir in case_dirs:

    case_id = int(case_dir.split('_')[1])

    # --- Case-dependent parameter processing 

    # drn cond
    prop_filename = os.path.join(case_dir,'ext','drn_spd_1.txt')
    pf.add_parameters(filenames=prop_filename, 
                      par_name_base=['cond'],
                      pargp='drn', index_cols=[4], 
                      use_cols=[3], upper_bound=10.,
                      lower_bound=0.1,
                      par_type='grid')

    # river cond
    prop_filename = os.path.join(case_dir,'ext','riv_spd_1.txt')
    pf.add_parameters(filenames=prop_filename, 
                      par_name_base='riv',
                      pargp='riv', index_cols=[6], 
                      use_cols=[3], upper_bound=10.,
                      lower_bound=0.1,
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

# tie riv and drn conds to 1st inst
par['inst']=par.inst.astype(int)
riv_inst0_idx = par.loc[(par.pargp=='riv') & (par.inst == 0)].index
riv_tied_idx = par.loc[(par.pargp=='riv') & (par.inst > 0)].index
ninst = len(par.loc[par.pargp=='riv','inst'].unique())

par.loc[riv_tied_idx,'partrans'] = 'tied'

for i in range(1,ninst):
    idx = par.loc[(par.pargp=='riv') & (par.inst == i)].index
    par.loc[idx,'partied'] = riv_inst0_idx.values

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

# 0-weight to unavailable obs
obs.loc[obs.obsval.isna(),['weight','obsval']]=0

# 100-weight to mixing ratios
obs.loc[obs.obgnme=='qdrn','weight']=10
obs.loc[obs.obgnme=='mr','weight']=100

# ---- write pst   
pst.write(os.path.join(pf.new_d, f'cal_{model_name}.pst'))


# ---- run  pst   
pyemu.helpers.run(f'pestpp-glm cal_{model_name}.pst', cwd=pf.new_d)
pst.control_data.noptmax=30
pst.write(os.path.join(pf.new_d, f'cal_{model_name}.pst'))

'''
pyemu.helpers.start_workers("pst",'pestpp-glm','cal_ml.pst',num_workers=64,
                                  master_dir="pst_master")
'''
