mport os
import numpy as np 
import pandas as pd
from matplotlib import pyplot as plt
import pyemu


fosm_dir = 'master_fosm' 


dec_var = [
        'pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:bar',
        'pname:h_inst:0_ptype:gr_usecol:2_pstyle:m_idx0:gal',
        'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r21',
        'pname:q_inst:0_ptype:gr_usecol:2_pstyle:d_idx0:r20'
        ]


# pst file 
pst_file = os.path.join(fosm_dir,'fosm.pst')
pst = pyemu.Pst(pst_file)

par = pst.parameter_data
par.loc[dec_var,'partrans']='fixed'

# jacobian matrix 
jco_file = os.path.join(fosm_dir,'fosm.jcb')
jco = pyemu.Jco.from_binary(jco_file)

# prior parameter covariance matrix 
parcov_file = os.path.join(fosm_dir,'pcov.jcb')
parcov = pyemu.Cov.from_binary(parcov_file)

# observation covariance matrix 
obscov = pyemu.Cov.from_observation_data(pst)

sc = pyemu.Schur(
        pst=pst, 
        jco=jco, 
        parcov=parcov, 
        obscov=obscov, 
        forecasts=pst.forecast_names
        )

forecasts = sc.pst.forecast_names


sc.get_forecast_summary()
