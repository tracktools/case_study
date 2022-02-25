import os, sys, shutil
import platform
import numpy as np 
import pandas as pd
import geopandas as gpd
from matplotlib import pyplot as plt
import matplotlib as mpl
import flopy
from flopy.utils.gridgen import Gridgen


sim = flopy.mf6.MFSimulation.load() 
ml = sim.get_model('ml')

fig = plt.figure(figsize=(6,6))
ax = fig.add_subplot(1, 1, 1, aspect='equal')

mm = flopy.plot.PlotMapView(model=ml,ax=ax)
mm.plot_grid(linewidth=0.3)


# plot 
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1, aspect='equal')
ax.set_title('Modpath7 pathlines)'
 
pmv = flopy.plot.PlotMapView(model=ml, ax=ax)
pmv.plot_grid(lw = 0)
    
# ---- Plot heads as background
hds = sim.simulation_data.mfdata[ml.name,'HDS','HEAD'][-1,-1,-1,:]
heads = pmv.plot_array(hds, masked_values=[1.e+30], alpha=0.5)
cb = plt.colorbar(heads, shrink = 0.5)

# ---- Plot pathlines for each group
pth = flopy.utils.PathlineFile('mp.mppth')
rec = pth.get_alldata()
pmv.plot_pathline(rec, layer = 'all', lw = 0.03, alpha = 0.8)


# ---- Plot boundaries
bc_colors_dic = { 'RIV': 'cyan', 'DRN': 'red', 'WEL': 'coral'}
for bc in bc_colors_dic.keys():
    bounds = pmv.plot_bc(bc, color = bc_colors_dic[bc])

# ---- Plot legend
leg = ax.legend(loc = 'lower right',fontsize = 6)
for line in leg.get_lines():
    line.set_linewidth(2)
'''
