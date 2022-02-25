import os
import sys 
import numpy as np
import pandas as pd
import geopandas as gpd
from matplotlib import pyplot as plt

# main plot settings 
plt.style.use('default')
newparams = {'text.usetex': False,
        'font.size': 12,
        'legend.fontsize': 10,
        'xtick.major.size': 5.0,
        'xtick.minor.size': 3.0,
        'ytick.major.size': 5.0,
        'ytick.minor.size': 3.0,
        'axes.linewidth': 0.8,
        'savefig.dpi': 300}
plt.rcParams.update(newparams)

# initialize list of colors for plots
from matplotlib import cm
lcmap = cm.get_cmap('tab20b')
plt.set_cmap(lcmap)

# path to dirs
obs_dir = 'obs'
fig_dir = 'fig'

# generate dates over period of interest 
nper_date_start_string = '2014-01-01'       # Start simulation date (observations are available from 03/2013)
nper_date_end_string = '2016-01-01'         # End simulation date
freq = 'D'                                  # Simulation frequency as pandas.tseries.offset object
dates_out = pd.date_range(start = nper_date_start_string, end = nper_date_end_string, freq = freq) 

# --- collect records ids 

# observation wells from shapefile

# all observations (Thil + Suez + ADES)
all_obs_shp = gpd.read_file('./sig/sim/obs_points.shp' )
all_obs_ids = list(all_obs_shp.ID)

# observations from Thil-Gamarde
obs_shp = gpd.read_file('./sig/sim/obs_thil.shp' )
obs_ids = list(obs_shp.ID)

# river level
riv_ids = ['riv_ref_records']

# drain levels and discharge 
drain_ids = ['n_galerie','n_barbac']
Qdrain_ids = ['Q_galerie','Q_barbac']

# pumping well levels and discharge 
well_ids = ['BUSSAC', 'CANTINOLLE', 'DEMANES', 'GAJAC4', 'PRG', 'RUET', 'SMIM2', 'R20', 'R21']
Qwell_ids = [f'Q_{well_name}' for well_name in well_ids]

# full list of record ids 
loc_names = riv_ids + all_obs_ids + drain_ids + Qwell_ids + Qdrain_ids

# --- compile data 

# initialize observation df
df = pd.DataFrame({ 'date': dates_out})
df.set_index('date', inplace = True)

# merge file into single df 
for loc_name in loc_names:
    # ---- Read obs data
    loc_df = pd.read_csv(os.path.join(obs_dir,'{}.csv'.format(loc_name)),
            names=['date', loc_name], parse_dates = True,
            index_col = 0, header=0)
    # ---- Merge with simulation period
    df = pd.merge(df, loc_df, 'left', left_index = True, right_index = True)


# smooth records 
sdf = df.copy()
for col in df.columns:
    sdf[col] = df[col].rolling(window=7,min_periods=1,center=False).mean()


# surveys data
surveys_xls = os.path.join(obs_dir,'surveys.xlsx') 
surveys_df = pd.read_excel(surveys_xls, index_col = 0, parse_dates=['date'])

# --- plot
plt.ion()
plt.close('all')
plt.show()

# -- plot discharge and selected levels 
fig, axs = plt.subplots(2,1,sharex=True,figsize=(15,8))
ax0,ax1 = axs

# plot discharge rates 
#Q_ids = ['Q_R20','Q_R21','Q_barbac','Q_galerie']
Q_ids = ['Q_R20','Q_R21','Q_barbac']

Q_ids = Q_wells

ax0 = df.plot(y=Q_ids,ax=ax0,linewidth=1.)

ax0 = sdf.plot(y=Q_ids,ax=ax0,
        color='black',linewidth=0.4, linestyle='--',
        legend=False)


# plot selected levels  
level_ids =  riv_ids + drain_ids + obs_ids[1:]
#level_ids =  all_obs_ids
ax1 = df.plot(y=level_ids,ax=ax1)
#ax1.axhline(9.6,linestyle='--',c='green')#  barbac level

#ax1 = sdf.plot(y=level_ids,ax=ax1,
#        color='black',linewidth=0.4, linestyle='--',
#        legend=False)

# plot vertical lines for surveys 
for ax in axs:
    for date in surveys_df.date:
        ax.axvline(date, color='grey', linestyle="--")

fig.savefig(os.path.join(fig_dir,'fig_Qlevels_all.png'))

# -- plot all levels 

fig, ax = plt.subplots(figsize=(15,7))

# plot all levels
level_ids =  obs_ids[1:]
ax = df.plot(y=level_ids,ax=ax)
ax = sdf.plot(y=level_ids,ax=ax,
        color='black',linewidth=0.4, linestyle='--',
        legend=False)

for date in surveys_df.date:
    ax.axvline(date, color='grey', linestyle="--")

fig.savefig(os.path.join(fig_dir,'fig_all_levels.png'))


# extend surveys with level observations
surveys_ext_df = pd.merge(surveys_df,sdf,how='left',left_on='date',right_index=True,sort=True)
surveys_ext_df.to_excel(os.path.join(obs_dir,'surveys_ext.xlsx'),
        columns=sorted(surveys_ext_df.columns))


