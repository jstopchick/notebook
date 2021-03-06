
# coding: utf-8

# # Convert OOI Parsed pwrsys JSON to NetCDF file
# using CF-1.6, Discrete Sampling Geometry (DSG) conventions, **`featureType=timeSeries`**

# In[1]:

get_ipython().magic('matplotlib inline')
import json
import pandas as pd
import numpy as np

from pyaxiom.netcdf.sensors import TimeSeries


# In[2]:

infile = '/usgs/data2/notebook/data/20170130.superv.json'
infile = '/sand/usgs/users/rsignell/data/ooi/endurance/cg_proc/ce02shsm/D00004/buoy/pwrsys/20170208.pwrsys.json'

outfile = '/usgs/data2/notebook/data/20170208.pwrsys.nc'
with open(infile) as jf:
    js = json.load(jf)
    df = pd.DataFrame({})
    for k, v in js.items():
        df[k] = v
    df['time'] = pd.to_datetime(df.time, unit='s')
    df['depth'] = 0.
df.head()


# In[3]:

df['solar_panel4_voltage'].plot();


# In[4]:

df.index = df['time']
df['solar_panel4_voltage'].plot();


# ### Define the NetCDF global attributes

# In[5]:

global_attributes = {
    'institution':'Oregon State University', 
    'title':'OOI CE02SHSM Pwrsys Data',
    'summary':'OOI Pwrsys data from Coastal Endurance Oregon Shelf Surface Mooring',
    'creator_name':'Chris Wingard',
    'creator_email':'cwingard@coas.oregonstate.edu',
    'creator_url':'http://ceoas.oregonstate.edu/ooi'
}


# ### Create initial file

# In[6]:

ts = TimeSeries(
    output_directory='.',
    latitude=44.64,
    longitude=-124.31,
    station_name='ce02shsm',
    global_attributes=global_attributes,
    times=df.time.values.astype(np.int64) // 10**9,
    verticals=df.depth.values,
    output_filename=outfile,
    vertical_positive='down'
)


# ### Add data variables

# In[7]:

df.columns.tolist()


# In[8]:

# create a dictionary of variable attributes
atts = {
        'main_current':{'units':'volts', 'long_name':'main current'},
        'solar_panel3_voltage':{'units':'volts', 'long_name':'solar panel 3 voltage'}
       }


# In[9]:

print(atts.get('main_current'))


# In[10]:

# if we ask for a key that doesn't exist, we get a value of "None"
print(atts.get('foobar'))


# In[11]:

for c in df.columns:
    if c in ts._nc.variables:
        print("Skipping '{}' (already in file)".format(c))
        continue
    if c in ['time', 'lat', 'lon', 'depth', 'cpm_date_time_string']:
        print("Skipping axis '{}' (already in file)".format(c))
        continue
    if 'object' in df[c].dtype.name: 
        print("Skipping object {}".format(c))
        continue
        
    print("Adding {}".format(c))
    # add variable values and variable attributes here
    ts.add_variable(c, df[c].values, attributes=atts.get(c))


# In[12]:

df['error_flag3'][0]


# In[13]:

ts.ncd


# In[14]:

import netCDF4
nc = netCDF4.Dataset(outfile)


# In[15]:

nc['main_current']


# In[16]:

nc.close()


# In[ ]:



