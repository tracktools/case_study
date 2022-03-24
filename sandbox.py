from flopy.utils import EndpointFile, PathlineFile, CellBudgetFile
from flopy.mf6.utils import MfGrdFile
import os 
import pandas as pd
import numpy as np 

pathline_file = 'mp.mppth'
endpoint_file = 'mp.mpend'
grd_file = 'ml.disv.grb'
cbc_file = 'ml.cbc'

edp = EndpointFile(endpoint_file)
pth = PathlineFile(pathline_file)
bgf = MfGrdFile(grd_file)
cbc = CellBudgetFile(cbc_file)
flowja = cbc.get_data(text='FLOW-JA-FACE')[0][0, 0, :]
ia = bgf._datadict['IA'] - 1

#  get cell inflows from flowja given node 
def get_cell_inflows(node):
    inflows = []
    for ipos in range(ia[node]+1, ia[node+1]):
        flow = flowja[ipos]
        if flow > 0 : inflows.append(flow)
    return(np.array(inflows).sum())

# river data from cbc
riv_leak_df = pd.DataFrame(
        cbc.get_data(text='RIV')[0])
riv_leak_df.set_index('node', drop=False, inplace=True)
riv_cells = riv_leak_df.index.values

# particle groups
pgrp_df = pd.read_csv('pgroups.csv', header=None, names=['gid','name'], index_col=0) 

#  river ids
rivid_df = pd.read_csv('riv_ids.csv', header=None, names=['id','name'], index_col=0)

# endpoint file 
edp_df = pd.DataFrame(edp.get_alldata())
edp_df = edp_df.astype({'node': int})


# add particle group name (without apply)
edp_df['grpnme'] = pgrp_df.loc[edp_df.particlegroup,'name'].values

# mark point ending in river
edp_df['endriv'] = edp_df.node.apply(
        lambda n: n in riv_cells)


# get river leakage 
edp_df['riv_leak'] = 0.
edp_df.loc[edp_df.endriv,'riv_leak'] = edp_df.loc[edp_df.endriv,'node'].apply(
                lambda n: riv_leak_df.loc[n,'q'].sum())


# keep only highest flow values 
riv_leak_df['node'] = riv_leak_df.index.values
riv_df =  riv_leak_df.sort_values('q', ascending=False).drop_duplicates(['node'])
riv_df = riv_df.astype({'FID': int})
riv_df['name'] = rivid_df.loc[riv_df.FID.to_list(),'name'].values
edp_df['src'] = 'OTHERS'
edp_df.loc[edp_df.endriv,'src'] = riv_df.loc[edp_df.loc[edp_df.endriv].node,'name'].values

# get cell inflows
edp_df['cell_inflows'] = edp_df.node.apply(get_cell_inflows)

# compute particle mixing ratio
edp_df['alpha'] = edp_df['riv_leak']/(edp_df['riv_leak']+edp_df['cell_inflows'])
edp_df.loc[edp_df.alpha.isnull(),'alpha']=0.

# get all particle path data
allpdata = pth.get_alldata()

# sort by rising pid and time 
spdata = [ pdata[np.lexsort((pdata['particleid'], pdata['time']))] for pdata in allpdata]


'''
# get index of time = 1.0
idx = [ int(np.argwhere(pdata['time']==1.)) for  pdata in spdata]
# get particle ids, dt, dx, dy, v
pid = np.array([pdata['particleid'][i]  for i, pdata in zip(idx,spdata)])
dt = np.array([pdata['time'][i+1] -1. for i, pdata in zip(idx,spdata)])
dx = np.array([ pdata['x'][i+1] - pdata['x'][i]  for i, pdata in zip(idx,spdata)])
dy = np.array([ pdata['y'][i+1] - pdata['y'][i]  for i, pdata in zip(idx,spdata)])
v = np.sqrt(dx**2+dy**2)/dt
'''
# get particle ids, dt, dx, dy, v
pid = np.array([pdata['particleid'][0]  for pdata in spdata])
dt = np.array([pdata['time'][1] for pdata in spdata])
dx = np.array([ pdata['x'][1] - pdata['x'][0]  for pdata in spdata])
dy = np.array([ pdata['y'][1] - pdata['y'][0]  for pdata in spdata])
v = np.sqrt(dx**2+dy**2)/dt


# return df 
v_df = pd.DataFrame({'pid':pid,'v':v})
v_df.set_index('pid', inplace=True)

# merge df 
edp_df.loc[v_df.index,'v'] = v_df.loc[v_df.index,'v']

# compute mixing ratios by weighted average 
mr = edp_df.groupby(edp_df.grpnme).apply(lambda d: np.average(d.alpha, weights=d.v))

mr =  edp_df.groupby(['grpnme','src']).apply(lambda d: np.average(d.alpha, weights=d.v))

grp_ids = set(mr.index.get_level_values(0))
for gid in grp_ids: mr.loc[gid]['OTHERS'] = 1. - mr[gid].sum()

gb = ['grpnme','src']
mr = edp_df.groupby(gb).apply(lambda d: np.average(d.alpha, weights=d.v))
grp_ids = set(mr.index.get_level_values(0))
for gid in grp_ids: mr.loc[gid]['OTHERS'] = 1. - mr[gid].sum()

#return as DataFrame (unpacking multindex)
mr_df = mr.unstack(level=0, fill_value=0)

# cas non détaillé 

mr = edp_df.groupby(edp_df.grpnme).apply(lambda d: np.average(d.alpha, weights=d.v))

if isinstance(mr.index,pd.MultiIndex):
    mr_df = mr.unstack(level=0, fill_value=0)
else:
    mr_df = mr.to_frame()

mr_df['OTHERS'] = mr_df.apply(lambda s: 1 - s.sum(), axis=1)


# non détaillé : 

             RIV    OTHERS
grpnme                    
BAR     0.001938  0.998062
GAL     0.086715  0.913285
R20     0.129836  0.870164
R21     0.130381  0.869619

# détaillé 
            RIV1      RIV2        RIV3    RIV4  OTHERS
grpnme                                               
BAR     0.001938  0.998062   0.9980620.9980620.998062
GAL     0.086715  0.913285   0.9132850.9132850.913285
R20     0.129836  0.870164   0.8701640.8701640.870164
R21     0.130381  0.869619   0.8696190.8696190.869619



from flopy.utils import EndpointFile, PathlineFile, CellBudgetFile
from flopy.mf6.utils import MfGrdFile
import os 
import pandas as pd
import numpy as np 


def get_cell_inflows(node):
    inflows = []
    for ipos in range(ia[node]+1, ia[node+1]):
        flow = flowja[ipos]
        if flow > 0 : inflows.append(flow)
    return(np.array(inflows).sum())

pathline_file = 'mp.mppth'
endpoint_file = 'mp.mpend'
grd_file = 'ml.disv.grb'
cbc_file = 'ml.cbc'

edp = EndpointFile(endpoint_file)
pth = PathlineFile(pathline_file)
bgf = MfGrdFile(grd_file)
cbc = CellBudgetFile(cbc_file)
flowja = cbc.get_data(text='FLOW-JA-FACE')[0][0, 0, :]
ia = bgf._datadict['IA'] - 1

# river leakage from cbc
riv_leak_df = pd.DataFrame(cbc.get_data(text='RIV')[0])
riv_leak_df['node'] = riv_leak_df['node'] - 1 # back to 0-based
riv_leak_df.set_index('node', drop=False, inplace=True)

# river cells 
riv_cells = riv_leak_df.index.values

# inter-cell flows (FLOW-JA-FACE)
flowja = cbc.get_data(text='FLOW-JA-FACE')[0][0, 0, :]

# IA information from binary grid file
ia = bgf._datadict['IA'] - 1


# pgroups
pg_df = pd.read_csv('pgroups.csv', header=None, names=['id','name'])
pgrpname_dic = {gid:gnme for gid,gnme in zip(pg_df.id, pg_df.name)}
        
# endpoint file 
edp_df = pd.DataFrame(edp.get_alldata())
edp_df = edp_df.astype({'node': int})
edp_df['grpnme'] = [pgrpname_dic[gid] for gid in edp_df.particlegroup.values]

# identify endpoints in river cells
edp_df['endriv'] = edp_df.node.apply(lambda n: n in riv_cells)

# add river leakage 
edp_df['riv_leak'] = 0.
edp_df.loc[edp_df.endriv,'riv_leak'] = edp_df.loc[
        edp_df.endriv,
        'node'].apply(
                lambda n: riv_leak_df.loc[n,'q'].sum())

# compute cell inflows from cbc
edp_df.loc[edp_df.endriv,'rivcell_q'] = edp_df.loc[edp_df.endriv,
        'node'].apply(get_cell_inflows)

# compute particle mixing ratio
edp_df['alpha'] = edp_df['riv_leak']/ (edp_df['riv_leak']+edp_df['rivcell_q'])
edp_df.loc[edp_df.alpha.isnull(),'alpha']=0.

# add particle velocity and merge value into edp_df
alldata = pth.get_alldata()
spdata = [ pdata[np.lexsort((pdata['particleid'], pdata['time']))] for pdata in alldata]
pid = np.array([pdata['particleid'][0]  for pdata in spdata])
dt = np.array([pdata['time'][2] -pdata['time'][1] for pdata in spdata])
dx = np.array([ pdata['x'][2] - pdata['x'][1]  for pdata in spdata])
dy = np.array([ pdata['y'][2] - pdata['y'][1]  for pdata in spdata])
v = np.sqrt(dx**2+dy**2)/dt


v_df = pd.DataFrame({'pid':pid,'v':v,'dt':dt})
v_df.set_index('pid', inplace=True)

edp_df.loc[edp_df.particleid,'v'] = v_df.loc[edp_df.particleid,'v']

# without budget, without velocity weighing
#edp_df['alpha'] = edp_df['endriv'].astype(int)
#edp_df.loc[edp_df.particleid,'v'] = 1.

# Grouped weighted average of mixing ratios
# When they are provided, results are labeled with particle group names 
# and bc id names, rather than integer ids.
edp_df['src'] = edp_df.endriv.replace({True : 'river', False : 'others'})
    

# compute group mixing ratios from weighted average of particle mixing ratios
contrib = edp_df.groupby(
        ['grpnme', 'src'], dropna=False).apply(
                            lambda d: np.sum(d.alpha*d.v))

mr = contrib/edp_df.groupby(
        ['grpnme'], dropna=False).apply(
                            lambda d: np.sum(d.v))


# return mixing ratios as DataFrame
mr_df = mr.unstack(level=0, fill_value=0)
mr_df.loc['others'] = 1 - mr_df.sum()

mr_df


edp_df.loc[(edp_df.grpnme == 'BAR') & (edp_df.endriv==True),['grpnme', 'endriv', 'riv_leak',
       'rivcell_q', 'alpha', 'v', 'src']]

edp_df.loc[(edp_df.grpnme == 'BAR') & (edp_df.endriv==True),'v'].mean()

