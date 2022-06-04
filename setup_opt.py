import os, sys, shutil
import pandas as pd
import numpy as np
import flopy
import pyemu
import helpers

# data and gis dir
data_dir = 'data'
gis_dir = 'gis'

# calibrated ml dir  
cal_dir = 'store'

# optimization dir
opt_dir = 'opt'

# simulation directory
sim_dir = 'ml_99'

# mf6 exe
mf6_exe = 'mf6'

# parameter data (prior confidence interval) 
par_df = pd.read_excel(os.path.join(data_dir,'par.xlsx'), index_col = 0)

# -----------------------------------------------------------------
# ---------------     Simulation model setup    -------------------
# -----------------------------------------------------------------

# ---- load mf model and fetch spatial reference (grid cell centroids)
sim = flopy.mf6.MFSimulation.load(sim_ws=os.path.join(cal_dir,sim_dir),exe_name=mf6_exe)

ml = sim.get_model('ml')
ncpl = ml.modelgrid.ncpl

sr = {i:(x,y) for i,x,y in zip(range(ncpl),
    ml.modelgrid.xcellcenters,ml.modelgrid.ycellcenters)}

# new drn cond values should be written in the sim drn ext file 
# drn levels are set to 1, they will be handled with multipliers

# get template drn ext file 
case_id=2
tpl_drn_file = os.path.join(cal_dir,'ml_02','ext',f'drn_spd_{case_id:02d}_1.txt')
tpl_drn_df = pd.read_csv(tpl_drn_file,delim_whitespace=True, header=None)

# fetch parameter from drn ext file 
case_id=99
sim_drn_file = os.path.join(cal_dir,sim_dir,'ext',f'drn_spd_{case_id:02d}_1.txt')
sim_drn_df = pd.read_csv(sim_drn_file,delim_whitespace=True, header=None)
sim_drn_df.iloc[:,3]=tpl_drn_df.iloc[:,3]

# write sim df with updated parameter values
with open(sim_drn_file, 'w') as f:
        f.write(
            sim_drn_df.to_string(
                header=False,
                index=False,
            )
            + '\n'
        )

helpers.run_case(os.path.join(cal_dir,sim_dir))

# -----------------------------------------------------------------
# ---------------  initialize PstFrom instance  -------------------
# -----------------------------------------------------------------

pf = pyemu.utils.PstFrom(original_d=cal_dir, new_d=opt_dir,
                 remove_existing=True,spatial_reference=sr,
                 longnames=True,
                 zero_based=False)

# -----------------------------------------------------------------
# ---  parameter and observation settings for history matching  ---
# -----------------------------------------------------------------

# fetch list of history matching case directories
case_dirs = sorted([d for d in os.listdir(cal_dir) if d.startswith('ml_')])[:-1]

# --- process case independent parameters
# a = twice largest spacing between pp
v = pyemu.geostats.ExpVario(contribution=1.0,a=500.)
grid_gs = pyemu.geostats.GeoStruct(variograms=v, transform='log')

prop_filename =os.path.join(cal_dir,'com_ext','k.txt')
pp_filename =os.path.join('..',gis_dir,'pp.shp')

zone_array = np.ones((1,ml.modelgrid.ncpl))
pargp='hk'

pp_df = pf.add_parameters(filenames=prop_filename, par_type="pilotpoint",
                   par_name_base='hk',pargp=pargp, geostruct=grid_gs,
                   lower_bound=par_df.loc[pargp,'faclbnd'], upper_bound=par_df.loc[pargp,'facubnd'],
                   ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                   zone_array=zone_array,pp_space=os.path.join('..',gis_dir,'pp.shp'))

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
    prop_filename = os.path.join(case_dir,'ext',f'drn_spd_{case_id:02d}_1.txt')
    pargp='cdrn'
    pf.add_parameters(filenames=prop_filename, 
                      par_name_base=['cond'],
                      pargp=pargp, index_cols=[4], 
                      use_cols=[3],
                      lower_bound=par_df.loc[pargp,'faclbnd'], upper_bound=par_df.loc[pargp,'facubnd'],
                      ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                      par_type='grid')

    # river cond
    prop_filename = os.path.join(case_dir,'ext',f'riv_spd_{case_id:02d}_1.txt')
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
    hds_filename = os.path.join(case_dir,'sim','hds.csv')

    hds_df = pf.add_observations(hds_filename, insfile=hds_filename+'.ins',
            index_cols='time', obsgp = 'heads',
            prefix='h')

    # drain discharge
    drn_filename = os.path.join(case_dir,'sim','drn.csv')

    drn_df = pf.add_observations(drn_filename, insfile=drn_filename+'.ins',
            index_cols=0, prefix='q', obsgp = 'qdrn')

    # mixing ratios 
    mr_filename = os.path.join(case_dir,'sim','mr.csv')

    mr_df = pf.add_observations(mr_filename, insfile=mr_filename+'.ins',
            index_cols=0, prefix='mr',obsgp = 'mr')


# -----------------------------------------------------------------
# -------------- simulation settings for optimization  ------------
# -----------------------------------------------------------------

case_id = 99

# river cond
prop_filename = os.path.join(sim_dir,'ext',f'riv_spd_{case_id:02d}_1.txt')
pargp='criv'
pf.add_parameters(filenames=prop_filename, 
                  par_name_base='riv',
                  pargp=pargp, index_cols=[6], 
                  use_cols=[3],
                  lower_bound=par_df.loc[pargp,'faclbnd'], upper_bound=par_df.loc[pargp,'facubnd'],
                  ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                  par_type='grid')

# ---- decision variables  
# drn levels 
# NOTE : in the present version of add_parameters (and most likely the mult2model function)
# all columns are parameterized with the same style. Here, multipliers.
# It would be more convenient to use direct style for decision variables.
# Instead, we use multipliers with initial values in the model files set to 1.
# Doing so, multiplier values correspond to parameter values. 


prop_file = os.path.join(sim_dir,'ext',f'drn_spd_{case_id:02d}_1.txt')
drn_df = pf.add_parameters(filenames=prop_file, 
                  par_name_base=['h','cond'],
                  pargp=['hdrn','cdrn'], index_cols=[4], 
                  lower_bound=[par_df.loc['hdrn','parlbnd'],par_df.loc['cdrn','parlbnd']],
                  upper_bound=[par_df.loc['hdrn','parubnd'], par_df.loc['cdrn','parubnd']],
                  ult_lbound=[par_df.loc['hdrn','parlbnd'], par_df.loc['cdrn','parlbnd']],
                  ult_ubound=[par_df.loc['hdrn','parubnd'],par_df.loc['cdrn','parubnd']],
                  use_cols=[2,3],
                  par_type='grid'
                  )

# well discharge rate  
prop_file = os.path.join(sim_dir,'ext',f'wel_spd_{case_id:02d}_1.txt')
pargp='qwel'
qwel_df = pf.add_parameters(filenames=prop_file, 
                  par_name_base='q',
                  pargp=pargp, index_cols=[3], 
                  use_cols=[2], use_rows=[7,8],
                  lower_bound=par_df.loc[pargp,'parlbnd'], upper_bound=par_df.loc[pargp,'parubnd'],
                  ult_lbound=par_df.loc[pargp,'parlbnd'], ult_ubound=par_df.loc[pargp,'parubnd'],
                  transform='fixed',
                  par_type='grid',
                  par_style='direct')

# ---- simulation directory :  objective and constraints 
 
# mixing ratios 
mr_file = os.path.join(sim_dir,'sim', 'mr.csv')

sim_mr_df = pf.add_observations(mr_file, insfile=mr_file+'.ins',
        index_cols=0, prefix='mr', obsgp = 'sim_mr')

# discharge values 
q_file = os.path.join(sim_dir,'sim','q.csv')

sim_q_df = pf.add_observations(q_file, insfile=q_file+'.ins',
        index_cols=0, prefix='q',obsgp = 'sim_q')

# global values
glob_file = os.path.join(sim_dir,'sim','glob.csv')

glob_df = pf.add_observations(glob_file, insfile=glob_file+'.ins',
        index_cols=0, prefix='glob',obsgp = 'glob')

# set list of forecasts 
forecasts = sim_mr_df.index.to_list() + sim_q_df.index.to_list() + glob_df.index.to_list()

# -------------------------------------------------------
# --------------      pst setup         -----------------
# -------------------------------------------------------

# functions for forward_run.py
pf.add_py_function('helpers.py','run_cases()',is_pre_cmd=False)
pf.add_py_function('helpers.py','run_case()',is_pre_cmd=None)
pf.add_py_function('helpers.py','ptrack_pproc()',is_pre_cmd=None)
pf.add_py_function('helpers.py','compute_glob()',is_pre_cmd=None)

# ---- Build Pst  
pst = pf.build_pst()

# replace python by python3
pst.model_command = ['python3 forward_run.py'] 

# run manager options 
pst.pestpp_options['overdue_resched_fac'] = 2
pst.pestpp_options['panther_agent_no_ping_timeout_secs'] = 3600
pst.pestpp_options['max_run_fail'] = 5

# --- Parameter processing
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

# ---- Observation processing  
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

for obgnme in ['heads','qdrn','mr']:
    # weighting based on measurement error 
    obs.loc[obs.obgnme==obgnme,'weight'] = 1./weights_df.loc[obgnme,'sigma']

# 0-weight to unavailable obs
obs.loc[obs.obsval.isna(),['weight','obsval']]=0


# --- Bounds and initial values for decision variables 

par = pst.parameter_data
#list of decision variables 
dec_var = [
        'pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:bar',        
        'pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:gal',
        'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21',
        'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20'
        ]

par.loc[dec_var,'partrans']='none'


# initial value
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:bar','parval1'] = 9.
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:gal','parval1'] = 9.
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21','parval1'] = -100./3600
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20','parval1'] = -100./3600

# lower bound
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:bar','parlbnd'] = 8.50
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:gal','parlbnd'] = 8.00
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21','parlbnd'] = -500./3600
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20','parlbnd'] = -500./3600

# upper bound
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:bar','parubnd'] = 9.65
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:gal','parubnd'] = 9.65
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21','parubnd'] = -50./3600 
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20','parubnd'] = -50./3600


# --- Derivative calculation
pst.parameter_groups['forcen'] = 'always_5'
pst.parameter_groups['dermthd'] = 'best_fit'

pst.parameter_groups.loc['derinc'] = 0.1
pst.parameter_groups.loc['hdrn','inctyp'] = 'absolute'
pst.parameter_groups.loc['qwel','inctyp'] = 'absolute'
pst.parameter_groups.loc['hdrn','derinc'] = 0.05 # m
pst.parameter_groups.loc['qwel','derinc'] = 10./3600 # m

# --- Prior parameter covariance matrix 

# multipliers bounds from parameter bounds 
pgroups = ['hk', 'criv', 'cdrn', 'cghb', 'rech']
for pg in pgroups:
    par.loc[par.pargp == pg,'parlbnd'] = par_df.loc[pg,'priorlbnd']/par_df.loc[pg,'val']
    par.loc[par.pargp == pg,'parubnd'] = par_df.loc[pg,'priorubnd']/par_df.loc[pg,'val']

cov = pf.build_prior(fmt='coo', filename=os.path.join(opt_dir,'pcov.jcb'),sigma_range=6)
cov.to_uncfile(os.path.join(opt_dir,'pcov.unc'))

# ---- Forecast definition  
pst.pestpp_options['forecasts'] = forecasts
pst.observation_data.loc[forecasts,'weight']=0.

# ---- compute jacobian matrix for FOSM
pst_name = 'fosm.pst'
pst.control_data.noptmax=-1
pst.write(os.path.join(pf.new_d, pst_name))
#pyemu.helpers.run(f'pestpp-glm {pst_name}', cwd=pf.new_d)


pyemu.helpers.start_workers('opt','pestpp-glm',pst_name,num_workers=64,
                              worker_root= 'workers',cleanup=False,
                                master_dir='master_fosm')

# ---- Optimization settings

# constraint definition (mr < ref_value)
obs.loc['oname:glob_otype:lst_usecol:mr_time:99.0','weight']=1
obs.loc['oname:glob_otype:lst_usecol:mr_time:99.0','obsval']=0.1
obs.loc['oname:glob_otype:lst_usecol:mr_time:99.0','obgnme']='l_mr'
pst.pestpp_options['opt_constraint_groups'] = ['l_mr']

# decision variables (well discharge rates and drain levels)
pst.pestpp_options['opt_dec_var_groups'] = ['qwel','hdrn']

# objective function definition 
obj_obsnme = 'oname:glob_otype:lst_usecol:q_time:99.0'
obs.loc[obj_obsnme,'weight']=0.
pst.pestpp_options['opt_obj_func'] = obj_obsnme
pst.pestpp_options['opt_direction'] = 'min'

# prior parameter covariance matrix 
pst.pestpp_options['parcov'] = 'pcov.unc'


# Number of SLP iterations (if noptmax = 1: LP)
pst.control_data.noptmax = 5

# SLP options 
pst.pestpp_options['opt_coin_log'] = 4 # verbosity level of simplex solver 
pst.pestpp_options['opt_recalc_chance_every'] = 1

# risk 
risk = 0.5
pst.pestpp_options['opt_risk'] = risk

# ---- Write pst   
pst_name = f'opt_{int(risk*100):02d}.pst'
pst.write(os.path.join(pf.new_d, pst_name))

# --- Run pestpp-opt
#pyemu.helpers.run(f'pestpp-opt {pst_name}', cwd=pf.new_d)

# start workers
pyemu.helpers.start_workers('opt','pestpp-opt',pst_name,num_workers=10,
                              worker_root= 'workers',cleanup=False,
                                master_dir='master_opt')
