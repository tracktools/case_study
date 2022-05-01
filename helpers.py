import os, shutil
import pyemu
import pandas as pd 
import os
import multiprocessing as mp
import numpy as np
import pandas as pd
import pyemu

 
# pest-free run from par and template files  
def run(par_file = 'par.dat', info_file='ml_info.csv', cwd='.'):
    # read info file 
    info_df = pd.read_csv(os.path.join(cwd,info_file))
    for tpl_file,col_idx in zip(info_df.tpl_file,info_df.col_idx):
        # read parameter value file 
        parval_df = pd.read_csv(os.path.join(cwd,par_file),header=None,
                delim_whitespace=True, names = ['parnme','value'],
                index_col='parnme')
        # read tpl 
        tpl_df = pd.read_csv(os.path.join(cwd,tpl_file),skiprows=1,header=None)

        # get parameter names 
        row_idx = tpl_df[col_idx].str.startswith('~') # rows with parameters 
        parnames = tpl_df.loc[row_idx,col_idx].str.extract(r'~\s*(\S+)\s*~')[0].tolist()

        # get parameter values
        parvals = parval_df.loc[parnames,'value'].values

        # setup model parameter file 
        mlfile_df = tpl_df.copy()
        mlfile_df.loc[row_idx,col_idx] = parvals

        # write model file 
        mlfile = os.path.join(cwd,'ext',tpl_file.replace('.tpl',''))
        with open(mlfile,'w') as f:
            f.write(mlfile_df.to_string(index=False,header=False))

    # run model 
    run_case(case_dir=cwd)


# run simulation case only
def run_sim():
    run_case(case_dir='sim')

#  run series of cases 
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
    #ta.load_rivname_dic(rivname_file)
    ta.load_rivname_dic(mfriv_file= os.path.join(case_dir,'ext', 'riv_spd_1.txt'))
    
    # selection of river reaches to consider as contaminant source
    reach_list = ['THIL_AVAL','THIL_AMONT','MOULINAT_AMONT','GAJAC','BUSSAGUET_AMONT']
    agg_dic = {'river' : reach_list}

    # compute mixing ratio
    mr = ta.compute_mixing_ratio(
            #on='river',
            on=agg_dic,
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
def compute_glob(case_dir):
    # input files 
    mr_file = os.path.join(case_dir,'sim','mr.csv')
    drn_file = os.path.join(case_dir,'sim','drn.csv')
    wel_file = os.path.join(case_dir,'ext','wel_spd_1.txt')

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
def clear_dirs(dlist):
    for d in dlist:
        if os.path.exists(d):
           shutil.rmtree(d)
        os.mkdir(d)



def build_jac_test_csv(pst, num_steps, par_names=None, forward=True):
    """build a dataframe of jactest inputs for use with pestpp-swp

    Args:
        pst (`pyemu.Pst`): existing control file
        num_steps (`int`): number of pertubation steps for each parameter
        par_names [`str`]: list of parameter names of pars to test.
            If None, all adjustable pars are used. Default is None
        forward (`bool`): flag to start with forward pertubations.
            Default is True

    Returns:
        `pandas.DataFrame`: the sequence of model runs to evaluate
        for the jactesting.


    """
    if isinstance(pst, str):
        pst = pyemu.Pst(pst)
    # pst.add_transform_columns()
    pst.build_increments()
    incr = pst.parameter_data.increment.to_dict()
    irow = 0
    par = pst.parameter_data
    if par_names is None:
        par_names = pst.adj_par_names
    total_runs = num_steps * len(par_names) + 1
    idx = ["base"]
    for par_name in par_names:
        idx.extend(["{0}_{1}".format(par_name, i) for i in range(num_steps)])
    df = pd.DataFrame(index=idx, columns=pst.par_names)
    li = par.partrans == "log"
    lbnd = par.parlbnd.copy()
    ubnd = par.parubnd.copy()
    lbnd.loc[li] = lbnd.loc[li].apply(np.log10)
    ubnd.loc[li] = ubnd.loc[li].apply(np.log10)
    lbnd = lbnd.to_dict()
    ubnd = ubnd.to_dict()

    org_vals = par.parval1.copy()
    org_vals.loc[li] = org_vals.loc[li].apply(np.log10)
    if forward:
        sign = 1.0
    else:
        sign = -1.0

    # base case goes in as first row, no perturbations
    df.loc["base", pst.par_names] = par.parval1.copy()
    irow = 1
    full_names = ["base"]
    for jcol, par_name in enumerate(par_names):
        org_val = org_vals.loc[par_name]
        last_val = org_val
        # NOTE : not increment, but absolute values 
        incr_list = np.linspace(
                org_val-incr[par_name]*int(num_steps/2),
                org_val+incr[par_name]*int(num_steps/2),
                num_steps)
        for step in range(num_steps):
            vals = org_vals.copy()
            i = incr[par_name]
            #val = last_val + (sign * incr[par_name])
            val = incr_list[step]
            
            if val > ubnd[par_name]:
                sign = -1.0
                val = org_val + (sign * incr[par_name])
                if val < lbnd[par_name]:
                    raise Exception("parameter {0} went out of bounds".format(par_name))
            elif val < lbnd[par_name]:
                sign = 1.0
                val = org_val + (sign * incr[par_name])
                if val > ubnd[par_name]:
                    raise Exception("parameter {0} went out of bounds".format(par_name))

            vals.loc[par_name] = val
            vals.loc[li] = 10 ** vals.loc[li]
            df.loc[idx[irow], pst.par_names] = vals
            full_names.append(
                "{0}_{1:<15.6E}".format(par_name, vals.loc[par_name]).strip()
            )

            irow += 1
            last_val = val
    df.index = full_names
    return df


