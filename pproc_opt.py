#======================================================

import os
import pyemu, glob
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.ticker as mtick
from pylab import text

# Load paths & file names
opt_dir  = 'opt'
pst = os.path.join(opt_dir,'opt_50.pst')

#--------------------------- Read PEST control file ---------------------------
pst = pyemu.Pst(pst)


# Lists of names
# decision variables
dvar_nme = [
       'pname:h_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:bar',
       'pname:h_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:gal',
       'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21',
       'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20'
       ]

# constraints
c_nme = ['oname:glob_otype:lst_usecol:mr_time:1.0'] 

# short names 
pids = ['H_BAR','H_GAL','Q_R20','Q_R21']


oids = ['Q','MR','Q_R21','Q_R20','Q_GAL','MR_R21','MR_BAR','Q_BAR','MR_R20','MR_GAL']



#--------------------- Retrieve decision variable values ----------------------

# Create a dataframe containing decision variable values at each iteration '''
def param_vs_iteration(name_pst, dvar_nme):
    it_SLP = len(glob.glob1(opt_dir, '*.par')) - 1 # no. of *.i.par files = no. of SLP iterations
    df_par =  pd.DataFrame(columns = ['itSLP ' + str(i) for i in range(1, it_SLP + 1)], 
                            index = dvar_nme)    # initialize dataframe
    # retrieve param values from *.i.par files
    for i in range(1, it_SLP + 1):   
        colnme = 'itSLP ' + str(i) 
        # retrieve params from *.i.par file
        df = pd.read_csv(pst.replace('.pst','.' + str(i) + '.par'), skiprows = 1, 
                         header = None, index_col = 0, usecols = [0,1], 
                         names = ['parnme', 'value'], delim_whitespace = True)
        # keep only dvars
        df_par.loc[dvar_nme, colnme] = df.loc[dvar_nme, 'value']
    df_par = df_par.T
    return df_par


# Retrieve decision variables

dvars = param_vs_iteration(name_pst, dvar_nme)
dvars.columns = pids
dvars['phi'] = dvars.sum(axis=1)    # Objective function value


#------------------------- Retrieve constraint values -------------------------


def output_vs_iteration(name_pst, c_nme, column):
    
    ''' Create a dataframe containing constraint values (or residuals) at each iteration '''
    
    # choose which column to retrieve
    
    if column == 'modeled':
        usecols = [0,3]
    
    elif column == 'residual':
        usecols = [0,4]
    
    it_SLP = len(glob.glob1('./', '*.sim.rei')) # no. of *.i.sim.rei files = no. of SLP iterations
        
    df_obs =  pd.DataFrame(columns = ['itSLP ' + str(i) for i in range(1, it_SLP + 1)], 
                            index = c_nme)    # initialize dataframe
    
    # retrieve modeled values from *.i.sim.rei files
    
    for i in range(1, it_SLP + 1):
        
        colnme = 'itSLP ' + str(i)
        
        # retrieve params from *.i.sim.rei file
        df = pd.read_csv(name_pst + '.' + str(i) + '.sim.rei', skiprows = 4, 
                         header = None, index_col = 0, usecols = usecols, 
                         names = ['output_nme', 'value'], delim_whitespace = True)
        
        # keep only constraints
        df_obs.loc[c_nme, colnme] = df.loc[c_nme, 'value']
    
    df_obs = df_obs.T
    
    return df_obs

# Retrieve outputs at constraint locations
cons = output_vs_iteration(name_pst, c_nme, 'modeled')


#----------------------------------- Plots ------------------------------------

plt.rc('font', family = 'serif', size = 12)


# Plot decision objective function value vs SLP iteration

fig, ax = plt.subplots(1, 1, figsize=(6, 6))

ax.plot(dvars.index.values, dvars.phi, 
        marker='.', lw = 1, c='tab:red', 
        label='opt_recalc_chance_every(1)')

ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1e'))

ax.set_xlabel('Number of SLP iteration')
ax.set_ylabel('Total pumping rate (m$^{3}$/s)')
ax.set_title('Decision objective function vs SLP iteration')
plt.tight_layout()
plt.savefig('phi_vs_iteration.png')


# Plot decision variables vs SLP iteration

fig, ax = plt.subplots(1, 1, figsize=(8, 6))

for nme in dvar_nme:
    ax.plot(dvars.index.values, dvars.loc[:, nme], marker = '.', 
            lw = 1, label = nme)

ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1e'))
ax.legend(loc = 'center left', bbox_to_anchor = (1, 0.5), ncol = 1)

ax.set_xlabel('Number of SLP iteration')
ax.set_ylabel('Pumping rate (m$^{3}$/s)')
ax.set_title('Optimal pumping rates vs SLP iteration')
plt.tight_layout()
plt.savefig('dvars_vs_iteration.png')


# Plot output at constraint location vs SLP iteration

for nme in ['zmuni1_pct']:#c_nme:
    
    wellnme = nme.split('zmuni')[1].split('_')[0]
    
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    
    ax.plot(cons.index.values, cons.loc[:, nme], 
            marker='.', lw = 1, ls='-', c='tab:blue', label='FOSM udpate every 10')
        
    ax.axhline(y =  muni_data.loc[nme, 'zbotm'], lw = 0.75, ls = '--', color = 'k') # Well bottom elevation
    
    text(0.98, 0.05, '--- Well bottom elev.\n(constraint)', ha = 'right', va = 'center',
         transform = ax.transAxes)

    ax.set_xlabel('Number of SLP iterations')
    ax.set_ylabel('Elevation (masl)')
    ax.set_title('Constraint vs SLP iteration: 1% seawater salinity at muni. well ' + wellnme)
    plt.tight_layout()
    fig.savefig('cons_vs_iteration_' + nme + '.png')
