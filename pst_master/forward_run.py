import os
import multiprocessing as mp
import numpy as np
import pandas as pd
import pyemu

# function added thru PstFrom.add_py_function()
def run_cases(cwd='.', cases_dirs = None):
    print("running models")
    bwd = os.getcwd()
    os.chdir(cwd)
    if cases_dirs == None : 
        cases_dirs = [d for d in os.listdir() if (os.path.isdir(d) and d.startswith('ml_'))]
    for case_dir in cases_dirs :
        run_case(case_dir=case_dir)
    os.chdir(bwd)

# run single case 


# function added thru PstFrom.add_py_function()
def run_sim():
    run_case(case_dir='ml_99')

#  run series of cases 


# function added thru PstFrom.add_py_function()
def run_case(case_dir='.'):
    ml_name = 'ml'
    mp_name = 'mp'
    # run flow model
    pyemu.os_utils.run('mf6', cwd=case_dir)
    # run particle tracking
    pyemu.os_utils.run('mp7 mp', cwd=case_dir)
    # post-proc particle tracking
    ptrack_pproc(case_dir, ml_name, mp_name)
    # compute global q and mr 
    compute_glob(case_dir)



# function added thru PstFrom.add_py_function()
def ptrack_pproc(case_dir, ml_name, mp_name):

    print('Post-processing particle tracking data...')

    from tracktools import TrackingAnalyzer

    #  attempt to infer case id from dir name 
    try : 
        case_id = int(case_dir.split('_')[1])
    except :
        case_id = 1.

    cbc_file = os.path.join(case_dir,ml_name + '.cbc')
    grb_file = os.path.join(case_dir,ml_name + '.disv.grb')
    endpoint_file = os.path.join(case_dir, mp_name + '.mpend')
    pathline_file = os.path.join(case_dir,mp_name + '.mppth')
    mr_file = os.path.join(case_dir,'sim','mr.csv')
    pgrpname_file = os.path.join(case_dir,'pgroups.csv')
    rivname_file = os.path.join(case_dir,'riv_ids.csv')

    ta = TrackingAnalyzer(
            endpoint_file=endpoint_file,
            pathline_file=pathline_file,
            cbc_file = cbc_file,
            grb_file = grb_file,
            )

    ta.load_pgrp_names(pgrpname_file)
    ta.load_rivname_dic(rivname_file)

    # compute mixing ratio
    mr = ta.compute_mixing_ratio(
            on='river',
            edp_cell_budget = True, 
            v_weight = True
            )

    # write sim file
    if 'river' not in mr.columns : mr['river']=0.
    sim_df = pd.DataFrame(
            [[case_id]+mr['river'].to_list()],
            columns=['time']+mr.index.to_list()
            )
    sim_df.set_index('time',inplace=True)
    sim_df.to_csv(mr_file)

# compute global variables (Q and mr)


# function added thru PstFrom.add_py_function()
def compute_glob(case_dir):
    # input files 
    mr_file = os.path.join(case_dir,'sim','mr.csv')
    drn_file = os.path.join(case_dir,'sim','drn.csv')
    wel_file = os.path.join(case_dir,'ext','well_spd_1.txt')

    # load input files
    mr_df = pd.read_csv(mr_file,index_col=0)
    q_df = pd.read_csv(drn_file,index_col=0)

    # fetch qwells from mf spd file
    qwel_df = pd.read_csv(wel_file,
            delim_whitespace=True,
            names=['lay','node','q','name'])
    qwel_df.name = qwel_df.name.str.upper()
    qwel_df.set_index('name',inplace=True)

    # append well rates to q_df
    q_df['R20'] = qwel_df.loc['R20','q']
    q_df['R21'] = qwel_df.loc['R21','q']

    # global discharge rate and mr
    glob_df = pd.DataFrame(q_df.sum(axis=1),columns=['q'])
    glob_df['mr'] = (q_df*mr_df).sum(axis=1)/q_df.sum(axis=1)

    # write output csv files 
    q_file = os.path.join(case_dir,'sim','q.csv')
    glob_file = os.path.join(case_dir,'sim','glob.csv')
    q_df.to_csv(q_file)
    glob_df.to_csv(glob_file)

# clear list of directories 

def main():

    try:
       os.remove(r'ml_01/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_01/sim/hds.csv')
    try:
       os.remove(r'ml_01/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_01/sim/drn.csv')
    try:
       os.remove(r'ml_01/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_01/sim/mr.csv')
    try:
       os.remove(r'ml_02/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_02/sim/hds.csv')
    try:
       os.remove(r'ml_02/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_02/sim/drn.csv')
    try:
       os.remove(r'ml_02/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_02/sim/mr.csv')
    try:
       os.remove(r'ml_03/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_03/sim/hds.csv')
    try:
       os.remove(r'ml_03/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_03/sim/drn.csv')
    try:
       os.remove(r'ml_03/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_03/sim/mr.csv')
    try:
       os.remove(r'ml_04/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_04/sim/hds.csv')
    try:
       os.remove(r'ml_04/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_04/sim/drn.csv')
    try:
       os.remove(r'ml_04/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_04/sim/mr.csv')
    try:
       os.remove(r'ml_05/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_05/sim/hds.csv')
    try:
       os.remove(r'ml_05/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_05/sim/drn.csv')
    try:
       os.remove(r'ml_05/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_05/sim/mr.csv')
    try:
       os.remove(r'ml_06/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_06/sim/hds.csv')
    try:
       os.remove(r'ml_06/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_06/sim/drn.csv')
    try:
       os.remove(r'ml_06/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_06/sim/mr.csv')
    try:
       os.remove(r'ml_07/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_07/sim/hds.csv')
    try:
       os.remove(r'ml_07/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_07/sim/drn.csv')
    try:
       os.remove(r'ml_07/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_07/sim/mr.csv')
    try:
       os.remove(r'ml_08/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_08/sim/hds.csv')
    try:
       os.remove(r'ml_08/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_08/sim/drn.csv')
    try:
       os.remove(r'ml_08/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_08/sim/mr.csv')
    try:
       os.remove(r'ml_09/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_09/sim/hds.csv')
    try:
       os.remove(r'ml_09/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_09/sim/drn.csv')
    try:
       os.remove(r'ml_09/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_09/sim/mr.csv')
    try:
       os.remove(r'ml_10/sim/hds.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_10/sim/hds.csv')
    try:
       os.remove(r'ml_10/sim/drn.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_10/sim/drn.csv')
    try:
       os.remove(r'ml_10/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_10/sim/mr.csv')
    try:
       os.remove(r'ml_99/sim/mr.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_99/sim/mr.csv')
    try:
       os.remove(r'ml_99/sim/q.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_99/sim/q.csv')
    try:
       os.remove(r'ml_99/sim/glob.csv')
    except Exception as e:
       print(r'error removing tmp file:ml_99/sim/glob.csv')
    pyemu.helpers.apply_list_and_array_pars(arr_par_file='mult2model_info.csv',chunk_len=50)
    run_cases()
    run_sim()

if __name__ == '__main__':
    mp.freeze_support()
    main()

