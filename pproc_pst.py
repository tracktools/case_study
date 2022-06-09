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
pmv.plot_array(np.log10(ml.npf.k.data[0]))
pmv.plot_bc('WEL',color='red')
pmv.plot_bc('DRN',color='black')
ax.set_xlim(407000,410000)
ax.set_ylim(6427000,6429500)
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


'''
# def split_by_size(x, size):
#     """
#     -----------
#     Description
#     -----------
#     Split an input list with a determinated size
#     -----------
#     Parameters
#     -----------
#     - x (list) : data
#     - size (int) : size of intern splited list
#     -----------
#     Returns
#     -----------
#     Splited list
#     -----------
#     Examples
#     -----------
#     >>> sp_arr = split(list(range(64)),8)
#     """
#     res = [ x[i:i + size] for i in range(0, len(x), size) ]
#     return(res)

'''

# def plot_params_evolution(pst, params, filename, parnames=None, pest = '++', plot_type = 'bar'):
#     """
#     -----------
#     Description
#     -----------
#     Plot parameters evolution during pest processing
#     -----------
#     Parameters
#     -----------
#     - pst (pyemu) : pst handler load from pyemu.Pst()
#     - params (list) : required parameters to plot
#     - filename (str) : output pdf name
#     - pest (str) : type of pest algorithm used ('++' or 'hp')
#     - plot_type (str) : type of plot required, can be 'Line' or bar' (default 'bar')
#     -----------
#     Returns
#     -----------
#     Pdf with all plots
#     -----------
#     Examples
#     -----------
#     >>> plot_params_evolution(pst, params = ['trans','sto','alpha', 'beta'],
#         filename = 'params_evol.pdf', plot_type = 'bar'):
#     """
#     if pest == 'hp':
#         # ---- Get ofr filename
#         ofr_file = pst.filename.replace(".pst",".ofr")
#         # ---- Load ofr data as dataframe
#         ofr_df = pd.read_csv(ofr_file, skiprows = list(range(3)), sep = r'\s+', index_col = False)
#         # ---- Fetch number of iteration
#         n_it = len(ofr_df) - 1
#         # ---- Collect parameter values over iterations
#         ipar_list = []
#         for it in range(n_it):
#             par_df = pd.read_csv(pst.filename.replace('.pst', '.par.{}'.format(str(it + 1))),
#                                  skiprows = [0], usecols = [1],
#                                  header = None, sep = r'\s+', index_col = False)
#             par_df.set_index(pst.parameter_data.parnme, inplace = True)
#             par_df.columns = ['it' + str(it + 1)]
#             ipar_list.append(par_df.T)
#         # ---- Concat all values
#         df_ipar = pd.concat(ipar_list)
#     else:
#         # ---- Create dataframe with initial parameters + PEST iterations
#         df_ipar = pd.read_csv(pst.filename.replace('.pst','.ipar'))
#         df_ipar.index = ['it' + str(n_it) for n_it in df_ipar['iteration']]
#     # ---- Subset parameter data frame 
#     df_ss = df_ipar[params]
#     # ---- Split each figure page into 4 axes
#     n_param = len(params)
#     splited = split_by_size(x = list(range(n_param)), size = 4)
#     if parnames is not None:
#         names_splited = split_by_size(x = parnames, size = 4)
#     else:
#         names_splited = split_by_size(x = df_ss.columns, size = 4)
#     # ---- Set colors
#     colors = ['navy','red','green','grey']
#     # ---- Plot parameters evolution as scatter plot
#     with PdfPages(filename) as pdf:
#         mpl.rc('font', family='serif', size=11)                         # Custom font
#         for set_param, parnmes in zip(splited, names_splited):
#             fig, ax = plt.subplots(4, 1, sharex=True, figsize=(10, 10))     # Prepare subplot
#             for i, n in enumerate(set_param):
#                 x = df_ss.index.values
#                 y = df_ss.iloc[:,n]
#                 parnme = parnmes[i]
#                 # Bar plot
#                 if plot_type == 'bar':                         
#                     ax[i].bar(x, y, 0.4, label = parnme, color=colors[i]) 
#                 # Line plot
#                 if plot_type == 'line':
#                     ax[i].plot(x, y, marker='o', linestyle='-',
#                                      linewidth=1, markersize=3,
#                                      color=colors[i], label = parnme)
#                     ax[i].fill_between(x,y, color = colors[i], alpha = 0.2)
#                 ax[i].set_ylabel(parnme, color=colors[i])
#                 ax[i].tick_params(axis='y', which='both', colors=colors[i])
#                 # Log scale
#                 # if pst.parameter_data.partrans[parnme] == 'log':
#                 #     ax[i].set_yscale('log')
#             pdf.savefig()






# def plot_obs_sim_mr(pst, filename, grpnme = 'mr', legend_names=['Barbacanes', 'Galerie Gamarde', 'R20', 'R21']):
#     """
#     """
#     # ---- Set up mixing ratio data from pst.res
#     mr_df = pst.res.query(f"group == '{grpnme}'")
#     mr_df.set_index(mr_df['name'].apply(
#         lambda n: 'survey_' + n.split(':')[-1]), inplace=True)
#     mr_df['name'] = mr_df['name'].apply(lambda n:n.split(':')[-2].replace('_time', ''))
#     # Prepare plot area
#     fig = plt.figure(figsize=(10, 10))
#     ax = fig.add_subplot(1, 1, 1, aspect='equal')
#     plt.rc('font', family='serif', size=12)
#     plt.rc('legend', fontsize=18)
#     # Set title
#     ax.set_title('Mixing ratio : sim vs obs')
#     # Prepare colors
#     cmap = plt.get_cmap('Dark2')
#     colors = [cmap(i) for i in np.linspace(0, 1, len(mr_df['name'].unique()))]
#     # Prepare markers
#     markers = ['o', 'x', '+', '^']
#     # Make scatter plots
#     for color, marker, bd in zip(colors,markers,mr_df['name']):
#         print(bd)
#       x = mr_df.loc[mr_df['name'] == bd,'measured']
#       y = mr_df.loc[mr_df['name'] == bd,'modelled']
#       patch = ax.scatter(x, y, c = color, marker = marker, s = 150, zorder = 10)
#       for survey in mr_df.loc[mr_df['name'] == bd].index:
#         ax.annotate(survey.split('_')[1],
#                      (x[survey],y[survey]),
#                      textcoords="offset points",
#                      xytext=(6,6),
#                      ha='center',
#                      size = 12,
#                      zorder = 50)
#     # Fix limits between 0 - 100%
#     ax.set_ylim((-1,1))
#     ax.set_xlim((-1,1))
#     # Set xy_label
#     ax.set_ylabel('Simulated')
#     ax.set_xlabel('Observed')
#     # Add legend
#     from matplotlib.legend_handler import HandlerBase
#     class MarkerHandler(HandlerBase):
#         def create_artists(self, legend, tup,xdescent, ydescent,
#                             width, height, fontsize,trans):
#             return [plt.Line2D([width/2], [height/2.],ls="",markersize = 14,
#                            marker=tup[1],color=tup[0], transform=trans)]
#     ax.legend(list(zip(colors,markers)),legend_names, handler_map={tuple:MarkerHandler()})
#     # Add 1:1 line
#     l = ax.plot([-1, 1], [-1, 1], ls = "-", lw = 1.5, c = 'grey', zorder = 0)
#     # Save figure
#     ax.get_figure().savefig(filename)
#     print(f'---> 1to1 plot has been savec in {filename} succesfully! <---')





# # ---- Usage
# # Phi progress
filename=os.path.join('fig', 'phi_progress.pdf')
ax = plot_phi_progress(cal_pst, filename, pest='++', log=False)
# # Parameters evolution
# params, parnames = [], []
# for p in pst.parameter_data.index:
#     if not 'zone' in p:
#         params.append(p)
#         parnames.append(p.split(':')[-1])
# filename=os.path.join('fig', 'param_evolution.pdf')
# plot_params_evolution(pst, params, filename, parnames, pest = '++', plot_type = 'line')
# # Mixing ration 1 to 1
# filename=os.path.join('fig', 'mr_1to1.png')
# plot_obs_sim_mr(pst, filename, grpnme = 'mr')

# # ---- Export to .shp

# # input filename
# headif = os.path.join('...')
# pthif = os.path.join('...')
# edpif = os.path.join('...')

# # output filename
# headof = os.path.join('...')
# hkof = os.path.join('...')
# pthof = os.path.join('...')
# edpof = os.path.join('...')

# # load data
# head = flopy.utils.binaryfile.HeadFile(headf)
# pth = flopy.utils.PathlineFile(pthf)
# edp = flopy.utils.EndpointFile(edpf)

# # export to .shp
# flopy.export.utils.output_helper(headof, ml, {"hds":head})
# ml.npf.export(hkof)
# shp_pth = pthobj.write_shapefile(pathline_data=pth.get_alldata(),
#                                one_per_particle=True,
#                                direction='ending',
#                                mg = ml.modelgrid,
#                                shpname=pthof)

# shp_edp = edpobj.write_shapefile(endpoint_data=edp.get_alldata(),
#                                one_per_particle=True,
#                                direction='ending',
#                                mg = ml.modelgrid,
#                                shpname=edpof)

