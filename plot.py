import os
import numpy as np 
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib as mpl
import flopy
import pyemu

# --- pst files 
cwd = 'pst_master'
cwd = 'ml'
run_model=False

'''
org_pst_name ='cal_ml.pst'
eval_pst_name = 'caleval_ml.pst'

# read pest control file 
pst = pyemu.Pst(os.path.join(cwd, org_pst_name))

# plot calibration results
phiprog = pst.plot(kind='phi_progress')
phiprog.get_figure().savefig(os.path.join('fig','phiprog.png'))

phipie = pst.plot(kind="phi_pie")
phipie.get_figure().savefig(os.path.join('fig','phipie.png'))

# not intuitive 
one2one = pst.plot(kind="1to1")
one2one[1].savefig(os.path.join('fig','one2one.png'))


#fetch residuals and add columns from name
res = pst.res
res[['type', 'fmt', 'locname', 'time']] = res.name.apply(
    lambda x: pd.Series(
        dict([s.split(':') for s in x.split('_') if ':' in s]
            )))[['oname', 'otype', 'usecol', 'time']]



# --- plot for one obs group 
for g in ['heads', 'qdrn', 'mr']:
    res_g = res.loc[(res.group == g) & (res.weight > 0), :]
    mx = max(res_g.measured.max(), res_g.modelled.max())
    mn = min(res_g.measured.min(), res_g.modelled.min())
    mx *= 1.1
    mn *= 0.9
    fig, ax = plt.subplots()
    ax.axis('square')
    locnames = res_g.locname.unique()
    cmap = plt.get_cmap('Dark2')    
    colors = [cmap(i) for i in np.linspace(0, 1, len(locnames))]
    for locname in locnames:
        res_gg = res_g.loc[res_g.locname == locname, :]
        scat = ax.scatter(res_gg.measured, res_gg.modelled, 
                label=locname)
    ax.plot([mn, mx], [mn, mx], 'k--', lw=1.0)
    xlim = (mn, mx)
    ax.set_xlim(mn, mx)
    ax.set_ylim(mn, mx)
    ax.grid()
    ax.set_xlabel('observed', labelpad=0.1)
    ax.set_ylabel('simulated', labelpad=0.1)
    ax.set_title(
        'group:{0}, {1} observations'.format(
             g, res_g.shape[0]
        ),
        loc='left'
    )
    ax.legend()
    txt = res_g.apply(lambda x: ax.annotate(
        x['time'],
        (x['measured'],x['modelled']),
        textcoords="offset points",
        xytext=(6,6),
        ha='center',
        size = 8),
        axis=1)
    fig.savefig(os.path.join('fig',f'one2one_{g}.png'))

# run model with final parameters 
if run_model : 
    par_file = org_pst_name.replace('pst','par')
    pst.parrep(os.path.join(cwd,par_file))
    pst.control_data.noptmax=0
    pst.write(os.path.join(cwd,eval_pst_name))
    pyemu.helpers.run(f'pestpp-glm {eval_pst_name}', cwd=cwd)

'''
# --- plot heads and particle tracks for all cases 
case_dirs = sorted([os.path.join(cwd,d) for d in os.listdir(cwd) if d.startswith('ml_')])

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
    fig.savefig(os.path.join('fig',f'map_{case_id}.png'))

    # zoom in
    vmin, vmax = 5,12
    ax.set_xlim(408000,410000)
    ax.set_ylim(6427500,6429500)
    heads.set_clim(vmin,vmax)
    fig.savefig(os.path.join('fig',f'zmap_{case_id}.png'))


# --- plot hk map
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1, aspect='equal')
ax.set_title('log10(hk)')
pmv = flopy.plot.PlotMapView(model=ml, ax=ax)
pmv.plot_grid(lw = 0)
pmv.plot_array(np.log10(ml.npf.k.data[0]))
pmv.plot_bc('WEL',color='red')
pmv.plot_bc('DRN',color='black')
ax.set_xlim(407000,410000)
ax.set_ylim(6427000,6429500)
fig.savefig(os.path.join('fig','hk.png'))

