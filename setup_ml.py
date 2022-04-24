import os, sys, shutil
import platform
import numpy as np 
import pandas as pd
import geopandas as gpd
from matplotlib import pyplot as plt
import matplotlib as mpl
import flopy
from flopy.utils.gridgen import Gridgen

from tracktools import ParticleGenerator

#-----------------------------------#
# ----- General settings ----                                                        
#-----------------------------------#

# see surveys.xlsx
# id < 99 for  history matching 
# id = 99 for simulation
case_ids = [i for i in range(1,11)]  + [99]
case_ids = [99]

mf6_exe = 'mf6'
mp7_exe = 'mp7'
gridgen_exe = 'gridgen'

#input dirs
data_dir = 'data'
gis_dir = 'gis'

# output dirs (relative to current dir)
tpl_ml_dir = 'ml_tpl'
ml_dir ='ml'
grd_dir = 'grd'
com_ext_dir = os.path.join(ml_dir,'com_ext')
sim_dir = os.path.join(tpl_ml_dir,'sim')
ext_dir = os.path.join(tpl_ml_dir,'ext')

dir_list = [tpl_ml_dir, ml_dir, grd_dir, 
        com_ext_dir, sim_dir, ext_dir]

# clean and (re)-build directory tree
for d in dir_list:
    if os.path.exists(d):
       shutil.rmtree(d)
    os.mkdir(d)

#-----------------------------------#
#       Model settings                                                         
#-----------------------------------#
grid_res = 400 # m, main grid resolution
nlay = 1                    
top = 30 # m 
thk = 50 #m 
botm = -20  # m
h_ghb = 22 # m 
hstart= 15. # m

#  particle tracking settings
well_shp = os.path.join(gis_dir,'prod_wells.shp')
drn_shp = os.path.join(gis_dir,'prod_drains.shp')
d = 25. # m 
n_part = 200

# prior (initial) parameter values 
par_df = pd.read_excel(os.path.join(data_dir,'par.xlsx'), index_col = 0)

# river data 
riv_df = pd.read_excel(os.path.join(data_dir,'riv_data.xlsx'), index_col = 0)

# observation surveys 
surveys_df = pd.read_excel(os.path.join(data_dir,'surveys.xlsx'), index_col = 0)
n_surveys = len(case_ids) # number of surveys

# GIS data
bbox_gdf = gpd.read_file(os.path.join(gis_dir,'bbox.shp'))
proj4 = bbox_gdf.crs.to_proj4()
epsg = bbox_gdf.crs.to_epsg()
xorigin, yorigin = bbox_gdf.MINX[0], bbox_gdf.MINY[0]
nrow, ncol = [int(round(v/grid_res)) for v in [bbox_gdf.HEIGHT, bbox_gdf.WIDTH ]]

#-----------------------------------#
#         grid generation                          
#-----------------------------------#
print('Grid generation...')

# --- base model with regular grid 
# Modflow simulation package
bsim = flopy.mf6.MFSimulation(sim_name= 'bmfsim', sim_ws = tpl_ml_dir, 
        exe_name = os.path.join('..',mf6_exe), version='mf6')

# Modflow groundwater flow model 
bml = flopy.mf6.ModflowGwf(bsim, modelname= 'bml')

# set spatial reference
bml.modelgrid.set_coord_info(proj4 = proj4, epsg = epsg)

gsdis = flopy.mf6.ModflowGwfdis(bml, length_units='METERS',
                                      xorigin=xorigin,
                                      yorigin=yorigin, 
                                      nlay=nlay,
                                      nrow=nrow,
                                      ncol=ncol,
                                      delr=grid_res,
                                      delc=grid_res,
                                      top=top,
                                      botm=botm)

# ---- Create gridgen object

g = Gridgen(gsdis, exe_name = gridgen_exe,  model_ws = grd_dir)

# ---- set active domain (idomain) for 1st layer 
g.add_active_domain(os.path.join('..', gis_dir, 'active'),[0])

# ---- set refinement zones 
for i in range(1,6): 
    g.add_refinement_features(
            os.path.join('..',gis_dir,'refine',f'refine_{i}'),
            'polygon', i, [0])

# ---- Build new grid ----
g.build(verbose=False)

#---------------------------------------------#
#    Grid intersections   
#---------------------------------------------#
print('Grid intersections...')

#  DISV properties
gridprops = g.get_gridprops_disv()
node_rec = g.get_nod_recarray()

# centroids coordinates
cx = [cell[1] for cell in gridprops['cell2d']]
cy = [cell[2] for cell in gridprops['cell2d']]

#  resolution dictionary
res_dic = {rec['node']: rec['dx'] for rec in node_rec}

#lists of intersections for all boundaries package settings
inter_dic = {'active':'polygon',
        'ghb':'line','prod_drains':'line', 'rivers':'line', 
        'obs_points':'point', 'wells':'point'}

icpl_dic = {}

for inter_id, inter_type in inter_dic.items():
    shp = os.path.join('..',gis_dir,inter_id)
    icpl_dic[inter_id] = g.intersect(shp, inter_type, 0)

# define integer ids for reach names 
# ids will be used as aux var in the riv package 
riv_names = [name.decode('utf8') for name in set(icpl_dic['rivers']['fid'])]
riv_ids = [i for i in range(len(riv_names))]
riv_names_dic = {riv_name:riv_id for riv_name,riv_id in zip(riv_names,riv_ids)}

# csv file will be used for post-processing
pd.DataFrame({'name':riv_names}, index=riv_ids).to_csv(
        os.path.join(tpl_ml_dir,'riv_ids.csv'), header=False)

#-----------------------------------#
#       template model setup 
#-----------------------------------#

# ---- Modflow simulation package
sim = flopy.mf6.MFSimulation(sim_name='mfsim', sim_ws = tpl_ml_dir, 
        exe_name = 'mf6')

sim.simulation_data.wrap_multidim_arrays = False

# ---- Time discretization package
perioddata = [ (1., 1, 1) ]
tdis = flopy.mf6.ModflowTdis(sim, time_units = 'seconds',
                                  nper=1, 
                                  perioddata = perioddata)

# ---- Modflow groundwater flow model
print('Processing ModflowGwf packages :')

modelname = 'ml'
ml = flopy.mf6.ModflowGwf(sim, modelname=modelname)
ml.modelgrid.set_coord_info(proj4 = proj4, epsg = epsg)

# ---- Iterative Model Solution (IMS) package
ims = flopy.mf6.ModflowIms(sim,
        outer_maximum=100,
        outer_dvclose=1e-5,
        inner_maximum=50,
        inner_dvclose=1e-6,
        rcloserecord=[1e-5,'STRICT'],
        print_option = 'ALL'
        )
sim.register_ims_package(ims, [ml.name])

# ---- Spatial discretization
print('Loading Flopy ModflowGwfdis')
disv = flopy.mf6.ModflowGwfdisv(ml, length_units='METERS',
                                      xorigin=xorigin,
                                      yorigin=yorigin, 
                                      nlay=nlay,
                                      ncpl = gridprops['ncpl'],
                                      nvert = gridprops['nvert'],
                                      vertices = gridprops['vertices'],
                                      cell2d = gridprops['cell2d'],
                                      top=gridprops['top'],
                                      botm=gridprops['botm'])

# ---- Initial conditions
ic = flopy.mf6.ModflowGwfic(ml, strt=hstart)  

# ---- NPF package (Node Property Flow)
print('ModflowGwfnpf...')

hk = par_df.loc['hk','val']

npf = flopy.mf6.ModflowGwfnpf(ml, icelltype=0,           
                                     k = hk,
                                     save_flows = True,
                                     save_specific_discharge = True )  

# ---- GHB package
print('ModflowGwfghb...')

ghb_h = 22 # m, constant
ghb_data = []

for ghb_cell in icpl_dic['ghb']:
    node = ghb_cell['nodenumber']
    ghb_id = ghb_cell['fid'].decode('utf-8')
    ghb_cond = par_df.loc['C_'+ghb_id,'val'] * res_dic[node]
    # [cellid, bhead, cond, aux, boundname], used format cellid = (lay,node)
    ghb_data.append([(0,node), ghb_h, ghb_cond, ghb_id])

ghb = flopy.mf6.ModflowGwfghb(ml, stress_period_data = ghb_data,          
                                         maxbound = len(ghb_data),
                                         boundnames = True,
                                         save_flows = True)

# ---- Recharge package
print('ModflowGwfrcha...')

rch_data = par_df.loc['rech','val'] # mm/y to m/s

rcha = flopy.mf6.ModflowGwfrcha(ml, recharge = rch_data,
                                        save_flows = True)

# ---- Observation package
print('ModflowUtlobs...')

hobs_points_list = [
        [obs_point.decode('utf-8'),
            'HEAD',
            (0, node) # (lay,node)
            ] 
        for node, obs_point in zip(
            icpl_dic['obs_points']['nodenumber'],
            icpl_dic['obs_points']['ID']
            )
    ]

obs_points_dic = {os.path.join('sim','hds.csv'): hobs_points_list}     
obs = flopy.mf6.ModflowUtlobs(ml, digits = 10, print_input = True, continuous=obs_points_dic)

# -- OC Package
print('ModflowGwfoc...')

oc_rec_list =[('HEAD', 'LAST'), ('BUDGET', 'LAST')]
#printrecord = [('HEAD', 'LAST')]
printrecord = None
oc = flopy.mf6.modflow.mfgwfoc.ModflowGwfoc(ml, 
    pname='oc', 
    saverecord = oc_rec_list, 
    head_filerecord=[modelname + '.hds'],
    budget_filerecord=[modelname +'.cbc'],
    printrecord = printrecord)


# --- Write flow model 
print('Writing model files files ...')
sim.write_simulation()

#-----------------------------------#
#       particle tracking 
#-----------------------------------#
print('Particle tracking setup...')

# -----  generation of particles 
pg = ParticleGenerator(ml = ml)
pg.gen_points(well_shp,  n = n_part)
pg.gen_points(drn_shp, n = n_part)
pgid_file = os.path.join(tpl_ml_dir,'pgroups.csv')
particlegroups = pg.get_particlegroups(pgid_file=pgid_file)

# mp7 setup
mpname =  'mp'

# ---- Build MODPATH7 model instance
print('mp7 setup...')
mp = flopy.modpath.Modpath7(modelname= mpname, flowmodel= ml,
        exe_name= mp7_exe,model_ws=tpl_ml_dir)

# ---- Set default iface for MODFLOW 6
defaultiface6 = {'RCH': 6, 'EVT': 6}

# ---- Build MODPATH7 BAS package
mpbas = flopy.modpath.Modpath7Bas(mp, porosity=0.1, defaultiface=defaultiface6)

# ---- Build MODPATH7 SIM package
mpsim = flopy.modpath.Modpath7Sim(mp, simulationtype='pathline',
                                      trackingdirection='backward',
                                      weaksinkoption='stop_at',
                                      weaksourceoption='stop_at',
                                      budgetoutputoption='no',
                                      stoptimeoption='extend',
                                      particlegroups= particlegroups)

# ---- Write modpath files
print('Witing mp7 files...')
mp.write_input()

#-----------------------------------#
#       survey specific packages 
#-----------------------------------#

# clear ml dir 
rm_dirs = sorted([d for d in os.listdir(ml_dir) if d.startswith('ml_')])
for case_dir in rm_dirs: shutil.rmtree(os.path.join(ml_dir,case_dir))

# iterate over cases
for case_id in case_ids:

    print(f'Processing survey {case_id}')

    case_dir = os.path.join(ml_dir,f'ml_{case_id:02d}')
    
    shutil.copytree(tpl_ml_dir,case_dir)
    
    # load base simulation 
    print('Loading replicated simlulation...')
    csim = flopy.mf6.MFSimulation.load(sim_ws=case_dir) 
    # write array data with single line
    csim.simulation_data.wrap_multidim_arrays = False

    # set length of stress period data as case id
    # perlen has no effect for s.s simulations
    # it is used hereafter to identify the survey 
    csim.tdis.perioddata = [ ( float(case_id), 1, 1) ]
    
    ml = csim.get_model('ml')

    # reset external files to common dir 
    ml.npf.k.store_as_external_file(os.path.join('..','com_ext','k.txt'))
    ml.ghb.stress_period_data.store_as_external_file(os.path.join('..','com_ext','ghb_spd.txt'))
    ml.rcha.recharge.store_as_external_file(os.path.join('..','com_ext','rech_spd.txt'))
 
    # ---- Well package
    print('ModflowGwfwel...')
    wells_data = []
    for well_cell in icpl_dic['wells']:
        node = well_cell['nodenumber']
        well_id = well_cell['fid'].decode('utf-8')
        well_Q = surveys_df.loc[case_id,'Q_'+well_id]*-1./3600. #m3/h to m3/s
        # [cellid, q, boundname]
        wells_data.append([(0,node),well_Q,well_id])

    wel = flopy.mf6.ModflowGwfwel(ml, save_flows = True,
                                     stress_period_data = wells_data,        
                                     maxbound=len(wells_data),
                                     boundnames = True)

    wel.stress_period_data.store_as_external_file(os.path.join('ext','well_spd.txt'))

    # ---- Drain package
    print('ModflowGwfdrn...')

    drn_data = []
    for drn_cell in icpl_dic['prod_drains']:
        node = drn_cell['nodenumber']
        drn_id = drn_cell['fid'].decode('utf-8')
        drn_h = surveys_df.loc[case_id,f'H_{drn_id}']
        drn_cond = par_df.loc['C_'+drn_id,'val'] * res_dic[node]
        # [cellid, elev, cond, boundname]
        drn_data.append([(0,node), drn_h, drn_cond, drn_id])

    drn_ids = [ drn_id.decode('utf8') for drn_id in np.unique(icpl_dic['prod_drains']['fid'])]
    drn_obs = {os.path.join('sim','drn.csv'): [(drn_id, 'DRN',drn_id) for drn_id in drn_ids]}

    drn = flopy.mf6.ModflowGwfdrn(ml, save_flows = True,
                                             stress_period_data = drn_data,        
                                             maxbound=len(drn_data),
                                             boundnames = True,
                                             observations=drn_obs)

    drn.stress_period_data.store_as_external_file(os.path.join('ext','drn_spd.txt'))

    # ---- Riv package
    print('ModflowGwfriv...')

    h_riv = surveys_df.loc[case_id,'H_RIV'] # Fetch h river (m)
    riv_data = []
    # ---- iterate over each reach
    for stream_cell in icpl_dic['rivers']:
        node = stream_cell['nodenumber']
        riv_name = stream_cell['fid'].decode('utf-8')
        zA, zB = riv_df.loc[riv_name,['A_abs_be','B_abs_be']] - 1. # zbot 
        xstart, xend= stream_cell['starting_distance'], stream_cell['ending_distance']
        L = stream_cell['L']
        xc = (xstart + (xstart - xend)/2)/L 
        if riv_df.loc[riv_name,'ref_type_A'] == 'rel':               
            hA = h_riv + riv_df.loc[riv_name,'relative_A']
        else :
            hA = riv_df.loc[riv_name,'absolute_A']
        if riv_df.loc[riv_name,'ref_type_B'] == 'rel':              
            hB = h_riv + riv_df.loc[riv_name,'relative_B']
        else :
            hB = riv_df.loc[riv_name,'absolute_B']
        # linear interpolation
        riv_stg = xc * hB + (1 - xc) * hA # stage                             
        z_bot = min(riv_stg-0.5, xc * zB + (1 - xc) * zA) # bottom (min 0.5m below stage)
        # conductivity (cell size dependent)
        riv_cond = par_df.loc['C_'+riv_name,'val'] * res_dic[node] 
        # integer river id as aux var
        riv_id = riv_names_dic[riv_name]
        # [cellid, stage, cond, rbot, aux, boundname]
        riv_data.append([(0,node), riv_stg, riv_cond, z_bot,riv_id, riv_name])

    riv = flopy.mf6.ModflowGwfriv(ml,auxiliary=['fid'], save_flows = True,
                                             stress_period_data = riv_data,        
                                             maxbound = len(riv_data),
                                             boundnames = True)

    riv.stress_period_data.store_as_external_file(os.path.join('ext','riv_spd.txt'))
    

    print('Writing model...')
    csim.write_simulation()


# -- initial forward run 
os.chdir(ml_dir)
sys.path.append('.')
import helpers
helpers.run_cases()


