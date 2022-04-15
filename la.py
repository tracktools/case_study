import os
import numpy as np 
import pandas as pd
from matplotlib import pyplot as plt
import pyemu


# completed PEST run - calibrated parameter set
cal_dir = 'pst_master' 

pst_file ='cal.pst'
jco_file = pst_file.replace('.pst','.jcb')     


css_df=la.get_par_css_dataframe()
css_df['hill_css'].plot.bar()

# directory for output files
cwd = 'la'

# read pp template file 
pp_file = os.path.join(cal_dir,'hk_inst0pp.dat')
pp_df = pyemu.pst.pst_utilsread_parfile(pp_file)
pp_names = pyemu.pst.pst_utils.parse_tpl_file(pp_file+'.tpl')
pp_df.set_index(pp_names,inplace=True)

pst = pyemu.Pst(os.path.join(cal_dir, pst_file))
la = pyemu.Schur(jco=os.path.join(cal_dir, jco_file),verbose=False)

la.parcov.to_uncfile(os.path.join(cwd, 'parcov.unc'), covmat_file=os.path.join(cwd,'parcov.mat'))
la.obscov.to_uncfile(os.path.join(cwd, 'obscov.unc'), covmat_file=None)

la.posterior_parameter.to_ascii(os.path.join(cwd, 'posterior.mat'))

par_sum = la.get_parameter_summary().sort_index()
par_sum.loc[par_sum.index[:100],'percent_reduction'].plot(kind='bar',figsize=(10,4),edgecolor='none')
par_sum.iloc[0:10,:]

