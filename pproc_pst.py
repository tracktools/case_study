import os, shutil
import numpy as np 
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib as mpl
import flopy
import pyemu

# completed PEST run dir - calibrated parameter set
cal_dir = 'master_glm' 
cal_pst_name ='cal_reg1.pst'
par_file = cal_pst_name.replace('pst','14.par')

# flag to copy calibrated model to cal dir 
store_cal = True
store_dir = 'store' # content will be cleared !

# evaluation dir (calibrated parameters -  noptmax=0) 
eval_dir = 'pst'  
eval_pst_name = 'eval.pst'

# calibration pst file 
cal_pst = pyemu.Pst(os.path.join(cal_dir, cal_pst_name))

# plot phi progress
phiprog = cal_pst.plot(kind='phi_progress')
phiprog.get_figure().savefig(os.path.join('fig','phiprog.png'))

# evaluation pst file (with best parameters)
cal_pst.parrep(os.path.join(cal_dir,par_file))
cal_pst.control_data.noptmax=0
cal_pst.write(os.path.join(eval_dir,eval_pst_name))

# run calibrated model 
pyemu.helpers.run(f'pestpp-glm {eval_pst_name}', cwd=eval_dir)

# copy calibrated ml files to cal dir
if store_cal:
    if os.path.exists(store_dir):
        shutil.rmtree(store_dir)
    cases_dirs = [d for d in os.listdir(eval_dir)\
        if (os.path.isdir(os.path.join(eval_dir,d)) and d.startswith('ml_'))]
    for d in (cases_dirs + ['com_ext']):
        shutil.copytree(os.path.join(eval_dir,d),os.path.join(store_dir,d))

# phie pie 
eval_pst = pyemu.Pst(os.path.join(eval_dir, eval_pst_name))
phipie = eval_pst.plot(kind="phi_pie")
phipie.get_figure().savefig(os.path.join('fig','phipie.png'))

# scatter plot 
one2one = eval_pst.plot(kind="1to1")
one2one[1].savefig(os.path.join('fig','one2one.png'))

#fetch residuals and add columns from name
res = eval_pst.res
res[['type', 'fmt', 'locname', 'time']] = res.name.apply(
    lambda x: pd.Series(
        dict([s.split(':') for s in x.split('_') if ':' in s]
            )))[['oname', 'otype', 'usecol', 'time']]


# --- plot one2one plot per obs. group 
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

# --- plot heads and particle tracks for all cases but simulation
case_dirs = sorted([os.path.join(eval_dir,d) for d in os.listdir(eval_dir) if d.startswith('ml_')])[:-1]

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
hkmap = pmv.plot_array(np.log10(ml.npf.k.data[0]))
cb = plt.colorbar(hkmap, shrink=0.5)
cb.ax.set_ylabel('log10(hk [m/s])', labelpad=5,rotation=270)
pmv.plot_bc('WEL',color='red')
pmv.plot_bc('DRN',color='black')
pmv.plot_bc('RIV',color='grey')
ax.set_xlim(407500,409500)
ax.set_ylim(6427500,6429500)
fig.autofmt_xdate()
fig.savefig(os.path.join('fig','hk.png'))


# Addtional plot function

def plot_phi_progress(pst, filename=None, pest = '++', log = True, **kwargs):
    """
    Plot of measurement_phi & regularization_phi vs number of model runs 

    Parameters
    -----------
    - pst (pyemu) : pst handler load from pyemu.Pst()
    - filename (str) : name of the output file containing the plot
    - pest (str) : type of pest algorithm used ('++' or 'hp')
    - log (bool) : plot phi in logaritmic scale

    Examples
    -----------
    >>> phiplot = plot_phi_progress(pst, filename='cal_phi_progress.pdf')
    """
    # ----- Get iobj file
    iobj_file = pst.filename.replace(".pst",".iobj")
    # ---- Load iobj data as dataframe
    df = pd.read_csv(iobj_file)
    # ---- Extract usefull data for plot
    it, phi, reg_phi = df.iteration, df.measurement_phi, df.regularization_phi
    # Prepare Plot figure
    plt.figure(figsize=(9,6))
    plt.rc('font', family='serif', size=10)
    ax = plt.subplot(1,1,1)
    ax1=ax.twinx()
    # ---- Plot processing
    lphi, = ax.plot(it, phi,color='tab:blue',marker='.', label='$\Phi_{measured}$')
    lphilim = ax.hlines(pst.reg_data.phimlim, 0, len(it)-1, lw = 1,
       colors='navy', linestyles='solid', label='$\Phi_{limit}$')
    lphiacc = ax.hlines(pst.reg_data.phimaccept, 0, len(it)-1, lw=1,
        colors='darkblue', linestyles='dotted', label='$\Phi_{accept}$')
    # Plot phi regularization
    lphireg, = ax1.plot(it,reg_phi,color='tab:orange',marker='+', label='$\Phi_{regul}$')
    # Add log scale if required
    if log == True:
        ax.set_yscale('log', basey = 10)
    # ---- Set labels
    ax.set_xlabel('Iterations')
    ax.set_ylabel('Measurement objective function ($\Phi_m$)',color='tab:blue')
    ax1.set_ylabel('Regularization objective function ($\Phi_r$)',color='tab:orange')
    # ---- Set grid & legend
    ax.grid()
    lines = [lphi, lphilim, lphiacc, lphireg]
    plt.legend(lines, [l.get_label() for l in lines],loc= 'upper center')
    plt.tight_layout()
    # ---- Export plot if requiered
    if filename is not None:
        plt.savefig(filename)
    return(ax)


