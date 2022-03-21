import os
import multiprocessing as mp
import numpy as np
import pandas as pd
import pyemu

# function added thru PstFrom.add_py_function()
def run_cases():
    print("running models")
    ml_name = 'ml'
    mp_name = 'mp'
    cases_dirs = [d for d in os.listdir() if (os.path.isdir(d) and d.startswith('ml_'))]
    for case_dir in cases_dirs :
        # run flow model
        pyemu.os_utils.run('mf6',cwd=case_dir)
        # run particle tracking
        pyemu.os_utils.run('mp7 mp',cwd=case_dir)
        # post-proc particle tracking
        ptrack_pproc(case_dir,ml_name,mp_name)



# function added thru PstFrom.add_py_function()
def ptrack_pproc(case_dir, ml_name, mp_name):

    print('Post-processing particle tracking data...')

    from tracktools import TrackingAnalyzer

    case_id = int(case_dir.split('_')[1])

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
    mr = ta.compute_mixing_ratio()

    # write sim file
    if 'river' not in mr.columns : mr['river']=0.
    sim_df = pd.DataFrame(
            [[case_id]+mr['river'].to_list()],
            columns=['time']+mr.index.to_list()
            )
    sim_df.set_index('time',inplace=True)
    sim_df.to_csv(mr_file)


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
    pyemu.helpers.apply_list_and_array_pars(arr_par_file='mult2model_info.csv',chunk_len=50)
    run_cases()

if __name__ == '__main__':
    mp.freeze_support()
    main()

