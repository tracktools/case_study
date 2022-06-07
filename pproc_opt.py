import os,glob
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

# Load paths & file names
opt_dir  = 'opt'
pstfile = os.path.join(opt_dir,'opt_50.pst')

# long parameter names  (decision variables)
pnames = [
       'pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:bar',
       'pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:gal',
       'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21',
       'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20'
       ]

# short parameter names 
pids = ['H_BAR','H_GAL','Q_R20','Q_R21']

# long observation name 
onames = ['oname:glob_otype:lst_usecol:q_time:99.0',
 'oname:glob_otype:lst_usecol:mr_time:99.0',
 'oname:q_otype:lst_usecol:r21_time:99.0',
 'oname:q_otype:lst_usecol:r20_time:99.0',
 'oname:q_otype:lst_usecol:gal_time:99.0',
 'oname:mr_otype:lst_usecol:r21_time:99.0',
 'oname:mr_otype:lst_usecol:bar_time:99.0',
 'oname:q_otype:lst_usecol:bar_time:99.0',
 'oname:mr_otype:lst_usecol:r20_time:99.0',
 'oname:mr_otype:lst_usecol:gal_time:99.0']

# short observation name 
oids = ['Q','MR','Q_R21','Q_R20','Q_GAL','MR_R21','MR_BAR','Q_BAR','MR_R20','MR_GAL']

# replace dics
pdic = {long:short for long,short in zip(pnames,pids)}
odic = {long:short for long,short in zip(onames,oids)}


# number of completed iterations 
nit = len(glob.glob1(opt_dir, '*.sim.rei')) 

# get decision variable values from .par files 
dfs = [ pd.read_csv(pstfile.replace('.pst',f'.{i+1}.par'), skiprows = 1, 
                     header = None, index_col = 0, usecols = [0,1], 
                     names = ['name', 'value'], delim_whitespace = True) \
                     for i in range(nit)]

pdf = pd.concat(dfs,axis=1,)
pdf.columns = [ f'it{i+1}' for i in range(nit)]
pdf = pdf.T

# replace with short parameter names 
pdf.columns = [pdic[pname] if pname in pdic.keys() else pname for pname in pdf.columns]

# get simulated constraint values from .sim.rei files
dfs = [pd.read_csv(pstfile.replace('.pst',f'.{i+1}.sim.rei'), skiprows = 4, 
                         header = None, index_col = 0, usecols = [0,3], 
                         names = ['name', 'value'], delim_whitespace = True)
                     for i in range(nit)]

odf = pd.concat(dfs,axis=1,)
odf.columns = [ f'it{i+1}' for i in range(nit)]
odf=odf.T

# replace with short observation name 
odf.columns = [odic[oname] if oname in odic.keys() else oname for oname in odf.columns]

# concatenate in a single df
df = pd.concat([pdf.loc[:,pids],odf.loc[:,oids]],axis=1)
df['it'] =df.index

# group name by var types
qids = [oid for oid in oids if oid.startswith('Q')]
mrids = [oid for oid in oids if oid.startswith('MR')]
hids = [pid for pid in pids if pid.startswith('H')]

# get initial global values 
glob_it0_df =  pd.read_csv(os.path.join(opt_dir,'glob_it0.csv'))

# plot par vals along iterations 
fig,axs = plt.subplots(3,1,figsize=(4,6))
ax1,ax2,ax3 = axs

df[qids].plot(ax=ax1)
df[mrids].plot(ax=ax2)
df[hids].plot(ax=ax3)

fig.savefig(os.path.join('fig','opt_evol.png'))

# plot pareto
fig,ax= plt.subplots(1,1,figsize=(4,4))
df.plot.scatter('Q','MR',ax=ax)
ax.scatter(glob_it0_df.q,glob_it0_df.mr,c='red')
ax.annotate(
        'it0',
        (glob_it0_df.q,glob_it0_df.mr),
        textcoords="offset points",
        xytext=(6,6),
        ha='center',
        size = 8),

txt = df.apply(lambda x: ax.annotate(
        x.it,
        (x.Q,x.MR),
        textcoords="offset points",
        xytext=(6,6),
        ha='center',
        size = 8),
    axis=1)

fig.savefig(os.path.join('fig','opt_pareto.pdf'))

