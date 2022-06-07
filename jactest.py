import os
import numpy as np 
import pandas as pd
from matplotlib import pyplot as plt
import os 
import matplotlib as mpl
import flopy
import pyemu
import helpers

# --- pst files 
opt_dir = 'opt'
org_pst_name ='opt_50.pst'
pst_name = 'jactest.pst'

parrep=False
par_file = os.path.join('pst_master',org_pst_name.replace('pst','par'))

# read pest file  
pst = pyemu.Pst(os.path.join(opt_dir, org_pst_name))

pst.parameter_groups.loc[ 'hdrn','inctyp'] = 'absolute'
pst.parameter_groups.loc[ 'qwel','inctyp'] = 'absolute'
pst.parameter_groups.loc[ 'hdrn','derinc'] = 0.15 # m
pst.parameter_groups.loc[ 'qwell','derinc'] = 50./3600 # m

par = pst.parameter_data 
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:bar','parval1'] = 9.
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:gal','parval1'] = 8.8
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21','parval1'] = -250./3600
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20','parval1'] = -250./3600

par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:bar','parlbnd'] = 8.00
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:gal','parlbnd'] = 8.00
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21','parlbnd'] = -500./3600
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20','parlbnd'] = -500./3600

par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:bar','parubnd'] = 9.65
par.loc['pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:gal','parubnd'] = 9.65
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21','parubnd'] = -50./3600 
par.loc['pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20','parubnd'] = -50./3600

# parrep 
if parrep : pst.parrep(os.path.join(opt_dir,par_file))


# long parameter names 
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

# target obs for PyEMU func
targetobs = onames

# generate jactest run list
#jactest_df = pyemu.helpers.build_jac_test_csv(pst,8,pnames)
jactest_df = helpers.build_jac_test_csv(pst,10,pnames)
jactest_df.to_csv(os.path.join(opt_dir,'jactest_in.csv'))

# sweep option
pst.pestpp_options['sweep_parameter_csv_file'] = 'jactest_in.csv'
pst.pestpp_options['sweep_output_csv_file'] = 'jactest_out.csv'

# write
pst.write(os.path.join(opt_dir,pst_name))

# run
pyemu.helpers.start_workers(opt_dir,'pestpp-swp',pst_name,num_workers=2,
                              worker_root= 'workers',cleanup=False,
                                master_dir='master_swp')

# plot
cwd = 'master_swp'
pdf_dir = os.path.join('fig','jactest')
csvin = os.path.join(cwd,'jactest_in.csv')
csvout = os.path.join(cwd,'jactest_out.csv')


maxoutputpages=1
outputdirectory=pdf_dir
filetype='pdf'

# ----- plot_jac_test --------------------------------

localhome = os.getcwd()
# check if the output directory exists, if not make it

if outputdirectory is not None and not os.path.exists(os.path.join(localhome, outputdirectory)):
    os.mkdir(os.path.join(localhome, outputdirectory))

if outputdirectory is None:
    figures_dir = localhome
else :
    figures_dir = os.path.join(localhome, outputdirectory)

# read the input and output files into pandas dataframes
jactest_in_df = pd.read_csv(csvin, engine="python", index_col=0)
jactest_in_df.index.name = "input_run_id"
jactest_out_df = pd.read_csv(csvout, engine="python", index_col=1)

# subtract the base run from every row, leaves the one parameter that
# was perturbed in any row as only non-zero value. Set zeros to nan
# so round-off doesn't get us and sum across rows to get a column of
# the perturbation for each row, finally extract to a series. First
# the input csv and then the output.
base_par = jactest_in_df.loc["base"]
delta_par_df = jactest_in_df.subtract(base_par, axis="columns")
delta_par_df.replace(0, np.nan, inplace=True)
delta_par_df.drop("base", axis="index", inplace=True)
delta_par_df["change"] = delta_par_df.sum(axis="columns")
delta_par = pd.Series(delta_par_df["change"])

#base_obs = jactest_out_df.loc["base"]
#delta_obs = jactest_out_df.subtract(base_obs)

delta_obs = jactest_out_df
delta_obs.drop("base", axis="index", inplace=True)


# if targetobs is None, then reset it to all the observations.
if targetobs is None:
    targetobs = jactest_out_df.columns.tolist()[8:]

delta_obs = delta_obs[targetobs]

# get the Jacobian by dividing the change in observation by the change in parameter
# for the perturbed parameters
#jacobian = delta_obs.divide(delta_par, axis="index")
jacobian = delta_obs
# use the index created by build_jac_test_csv to get a column of parameter names
# and increments, then we can plot derivative vs. increment for each parameter
extr_df = pd.Series(jacobian.index.values).str.extract(r"(.+)_(.+$)", expand=True)
extr_df.rename(columns={0: "parameter", 1: "increment"}, inplace=True)
extr_df['increment'] = extr_df.increment.astype(float)
extr_df.index = jacobian.index

# make a dataframe for plotting the Jacobian by combining the parameter name
# and increments frame with the Jacobian frame
plotframe = pd.concat([extr_df, jacobian], axis=1, join="inner")

# get a list of observations to keep based on maxoutputpages.
if maxoutputpages > 10:
    print("WARNING, more than 10 pages of output requested per parameter")
    print("maxoutputpage reset to 10.")
    maxoutputpages = 10

num_obs_plotted = np.min(np.array([maxoutputpages * 32, len(targetobs)]))

if num_obs_plotted < len(targetobs):
    # get random sample
    index_plotted = np.random.choice(len(targetobs), num_obs_plotted, replace=False)
    obs_plotted = [targetobs[x] for x in index_plotted]
    real_pages = maxoutputpages
else:
    obs_plotted = targetobs
    real_pages = int(len(targetobs) / 32) + 1


from matplotlib import ticker


# make a subplot of derivative vs. increment one plot for each of the
# observations in targetobs, and outputs grouped by parameter.
for param, group in plotframe.groupby("parameter"):
    for page in range(0, real_pages):
        fig, axes = plt.subplots(8, 4, sharex=True, figsize=(10, 15))
        for row in range(0, 8):
            for col in range(0, 4):
                count = 32 * page + 4 * row + col
                if count < num_obs_plotted:
                    axes[row, col].scatter(
                        group["increment"], group[obs_plotted[count]]
                    )
                    #axes[row, col].plot(
                    #    group["increment"], group[obs_plotted[count]], "r"
                    #)
                    axes[row, col].set_title(obs_plotted[count])
                    axes[row, col].tick_params(direction="in")  
                    axes[row, col].xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.2f}'))
        plt.tight_layout()
        if filetype is None:
            plt.show()
        else:
            plt.savefig(
                os.path.join(
                    figures_dir, "{0}_jactest_{1}.{2}".format(param, page, filetype)
                )
            )
        plt.close()

# plot selection only

df=plotframe.copy()
df.parameter = df.parameter.replace(pdic)
df.columns = pd.Series(df.columns).replace(odic)


# short parameter names 
plist = ['H_BAR','H_GAL','Q_R20','Q_R21']
olist = ['MR_BAR','MR_GAL','MR_R20','MR_R21']

fig,axs = plt.subplots(4,4,figsize=(10,10))

for oname,j in zip(olist,range(4)):
    for pname,i in zip(plist,range(4)):
        ax = axs[i,j]
        idx = df.parameter == pname
        ax.scatter(df.loc[idx,'increment'],df.loc[idx,oname])
        ax.plot(df.loc[idx,'increment'],df.loc[idx,oname], "r")
        ax.tick_params(direction="in")  
        ax.set_xlabel(pname)
        ax.set_ylabel(oname)
        ax.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.2f}'))

plt.tight_layout()

fig.savefig(os.path.join('fig','jactest_explicit.png'),dpi=150)



fig,axs = plt.subplots(1,2,figsize=(7,5))
pname ='H_GAL'
oname = 'Q_GAL'
ax = axs[0]
idx = df.parameter == pname
ax.scatter(df.loc[idx,'increment'],df.loc[idx,oname])
ax.plot(df.loc[idx,'increment'],df.loc[idx,oname], "r")
ax.tick_params(direction="in")  
ax.set_xlabel(pname)
ax.set_ylabel(oname)
ax.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.2f}'))

pname ='H_BAR'
oname = 'Q_BAR'
ax = axs[1]
idx = df.parameter == pname
ax.scatter(df.loc[idx,'increment'],df.loc[idx,oname])
ax.plot(df.loc[idx,'increment'],df.loc[idx,oname], "r")
ax.tick_params(direction="in")  
ax.set_xlabel(pname)
ax.set_ylabel(oname)
ax.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.2f}'))

fig.savefig(os.path.join('fig','jactest_qdrn.png'),dpi=150)




