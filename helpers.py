import os
import pyemu
import pandas as pd 

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

if __name__ == "__main__":
    # execute only if run as a script
    run_cases()
