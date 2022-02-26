import os
import numpy as np 
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib as mpl
import flopy
import pyemu
'''
# --- pst post-proc
pst = pyemu.Pst(os.path.join('pst_master', 'cal_ml.pst'))

phiprog = pst.plot(kind='phi_progress')
phiprog.get_figure().savefig('hello')
phiprog.get_figure().savefig(os.path.join('fig','phiprog.png'))

one2one = pst.plot(kind="1to1")
one2one[1].savefig(os.path.join('fig','one2one.png'))

# --- run model with adjusted parameters 
pst.parrep(os.path.join('pst_master','cal_ml.par'))
pst.control_data.noptmax=0
pst.write(os.path.join('pst_master','caleval_ml.pst'))
'''

pyemu.helpers.run('pestpp-glm caleval_ml.pst', cwd='pst_master')

case_dirs = sorted([os.path.join('pst_master',d) for d in os.listdir('pst_master') if d.startswith('ml_')])


# --- plot heads and particle tracks for all cases 
for case_dir in case_dirs: 

    # load case 
    sim = flopy.mf6.MFSimulation.load(sim_ws=case_dir)
    ml = sim.get_model('ml')

    # plot case 
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, aspect='equal')
    ax.set_title('Modpath7 pathlines')
    pmv = flopy.plot.PlotMapView(model=ml, ax=ax)
        
    # heads in background
    hds = sim.simulation_data.mfdata[ml.name,'HDS','HEAD'][-1,-1,-1,:]
    heads = pmv.plot_array(hds, masked_values=[1.e+30], alpha=0.5)
    cb = plt.colorbar(heads, shrink = 0.5)

    # pathlines for each group
    pth = flopy.utils.PathlineFile(os.path.join(case_dir,'mp.mppth'))
    rec = pth.get_alldata()
    pmv.plot_pathline(rec, layer = 'all', lw = 0.1, alpha = 0.8)

    # plot boundaries
    bc_colors_dic = { 'RIV': 'cyan', 'DRN': 'red', 'WEL': 'coral'}
    for bc in bc_colors_dic.keys():
        bounds = pmv.plot_bc(bc, color = bc_colors_dic[bc])

    # legend
    leg = ax.legend(loc = 'lower right',fontsize = 6)
    for line in leg.get_lines():
        line.set_linewidth(2)

    # save fig 
    case_id = case_dir.split('_')[-1]
    fig.savefig(os.path.join('fig',f'ptrack_{case_id}.png'))


# --- plot hk map
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1, aspect='equal')
ax.set_title('log10(hk)')
pmv = flopy.plot.PlotMapView(model=ml, ax=ax)
pmv.plot_grid(lw = 0)
pmv.plot_array(np.log10(ml.npf.k.data[0]))
fig.savefig(os.path.join('fig','hk.png'))

