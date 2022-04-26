import os
import numpy as np 
import pandas as pd
from matplotlib import pyplot as plt
import os 
import matplotlib as mpl
import flopy
import pyemu

# --- pst files 
cwd = 'opt'
org_pst_name ='opt_50.pst'
pst_name = 'jactest.pst'

parrep=False
par_file = os.path.join('pst_master',org_pst_name.replace('pst','par'))

# read pest file  
pst = pyemu.Pst(os.path.join(cwd, org_pst_name))

pst.parameter_groups.loc[ 'hdrn','inctyp'] = 'absolute'
pst.parameter_groups.loc[ 'qwel','inctyp'] = 'absolute'
pst.parameter_groups.loc[ 'hdrn','derinc'] = 0.05 # m
pst.parameter_groups.loc[ 'qwell','derinc'] = 5./3600 # m

# parrep 
if parrep : pst.parrep(os.path.join(cwd,par_file))


# generate jactest run list

par_names = [
       'pname:h_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:bar',
       'pname:h_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:gal',
       'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21',
       'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20'
       ]

jactest_df = pyemu.helpers.build_jac_test_csv(pst,10,par_names)

jactest_df.to_csv(os.path.join(cwd,'jactest_in.csv'))

# sweep option
pst.pestpp_options['sweep_parameter_csv_file'] = 'jactest_in.csv'
pst.pestpp_options['sweep_output_csv_file'] = 'jactest_out.csv'

# write
pst.write(os.path.join(cwd,pst_name))

'''
# run
pyemu.helpers.start_workers(cwd,'pestpp-swp',pst_name,num_workers=64,
                              worker_root= 'workers',cleanup=False,
                                master_dir='pst_master')
'''

# plot
cwd = 'pst_master'
pdf_dir = os.path.join('fig','jactest')
csvin = os.path.join(cwd,'jactest_in.csv')
csvout = os.path.join(cwd,'jactest_out.csv')
targetobs = None # ['oname:h_otype:lst_usecol:p32_time:2.0']

targetobs = ['oname:mr_otype:lst_usecol:bar_time:1.0',
   'oname:mr_otype:lst_usecol:gal_time:1.0',
   'oname:mr_otype:lst_usecol:r20_time:1.0',
   'oname:mr_otype:lst_usecol:r21_time:1.0',
  'oname:q_otype:lst_usecol:bar_time:1.0',
  'oname:q_otype:lst_usecol:gal_time:1.0',
  'oname:q_otype:lst_usecol:r20_time:1.0',
  'oname:q_otype:lst_usecol:r21_time:1.0',
'oname:glob_otype:lst_usecol:mr_time:1.0',
 'oname:glob_otype:lst_usecol:q_time:1.0']

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
                    axes[row, col].plot(
                        group["increment"], group[obs_plotted[count]], "r"
                    )
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


