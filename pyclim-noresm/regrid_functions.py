#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Functions used for regridding 

@author: Ada Gjermundsen 

Created on Wednesday November 3 2021
"""

import xarray as xr
import xesmf as xe
import numpy as np
import warnings
warnings.simplefilter('ignore')

def make_bounds(modelname, ds, seaice=False):
    '''
    Parameters
    ----------
    modelname: str, name of model. NorESM2: The ocean/sea-ice grid of NorESM2 is a tripolar grid with 360 and 384 unique grid cells in i- and j-direction, respectively. 
    Due to the way variables are staggered in the ocean model, an additional j-row is required explaining the 385 grid cells in the j-direction for the ocean grid. 
    The row with j=385 is a duplicate of the row with j=384, but with reverse i-index.
    Ocean variables are on i=360, j=385 grid
    Sea-ice variables are on i=360, j=385
    
    ds : xarray.DataSet, with model grid information for the data which need to be regridded
                         on (i,j,vertices) format where the 4 vertices give grid corner information

    Returns
    -------
    ds_in :  xarray.DataSet, with 2D model grid information for the data which need to be regridded
    '''
    ny,nx = ds.lat.shape
    if modelname in ['NorESM2-LM', 'NorESM2-MM'] and seaice:
        #drop the last row with j=385 of area when dealing with the sea ice variables.
        ny = ny - 1
    if 'lat' in ds.lon.coords:
        lat_model = ds.lat.isel(j=slice(0,ny)).rename({'i':'x','j':'y'}).drop('lon').drop('lat')
        lon_model = ds.lon.isel(j=slice(0,ny)).rename({'i':'x','j':'y'}).drop('lon').drop('lat')
    else:
        lat_model = ds.lat.isel(j=slice(0,ny)).rename({'i':'x','j':'y'})
        lon_model = ds.lon.isel(j=slice(0,ny)).rename({'i':'x','j':'y'})
    lon_b_model = xr.concat([ds.vertices_longitude.isel(vertices=0), ds.vertices_longitude.isel(vertices=1,i=-1)],dim='i')
    lon_b_model = xr.concat([lon_b_model,xr.concat([ds.vertices_longitude.isel(vertices=3,j=-1), ds.vertices_longitude.isel(vertices=2,j=-1,i=-1)],dim='i')],dim='j')
    lat_b_model = xr.concat([ds.vertices_latitude.isel(vertices=0), ds.vertices_latitude.isel(vertices=1,i=-1)],dim='i')
    lat_b_model = xr.concat([lat_b_model,xr.concat([ds.vertices_latitude.isel(vertices=3,j=-1), ds.vertices_latitude.isel(vertices=2,j=-1,i=-1)],dim='i')],dim='j')

    if 'lat' in lon_b_model.coords:
        lon_b_model = lon_b_model.isel(j=slice(0,ny+1)).rename('lon_b').rename({'j':'y_b','i':'x_b'}).drop('lon').drop('lat')
        lat_b_model = lat_b_model.isel(j=slice(0,ny+1)).rename('lat_b').rename({'j':'y_b','i':'x_b'}).drop('lon').drop('lat')
    else:
        lon_b_model = lon_b_model.isel(j=slice(0,ny+1)).rename('lon_b').rename({'j':'y_b','i':'x_b'})
        lat_b_model = lat_b_model.isel(j=slice(0,ny+1)).rename('lat_b').rename({'j':'y_b','i':'x_b'})
    lat_b_model = lat_b_model.where(lat_b_model<90.0,90.0)
    lat_b_model = lat_b_model.where(lat_b_model>-90.0,-90.0)
    return xr.merge([lon_model,lat_model,lon_b_model,lat_b_model])

def mk_outgrid(ds):
    '''Using xesmf output grids can easily be generated by the use of 
    xe.util.grid_2D
    xe.util.grid_global
    But if a different grid is preferable, it can be generated by the use of the function 
    Parameters
    ----------
    ds : netcdf file with grid information on lat/lon grid

    Returns
    -------
    outgrid : xarray.DataSet with output grid information to be used for regridding files
    '''
    lon = ds.lon.rename({'lon':'x'})
    lat = ds.lat.rename({'lat':'y'})
    lat_b = xr.concat([ds.lat_bnds.isel(bnds=0),ds.lat_bnds.isel(lat=-1).isel(bnds=1)],dim='lat').rename('lat_b').rename({'lat':'y_b'})
    lon_b = xr.concat([ds.lon_bnds.isel(bnds=0),ds.lon_bnds.isel(lon=-1).isel(bnds=1)],dim='lon').rename('lon_b').rename({'lon':'x_b'})
    outgrid = xr.merge([lon,lat,lon_b,lat_b])
    return outgrid

def make_regridder(ds, outgrid, grid_weight_path, regrid_mode = 'conservative', reuse_weights=False):
    ''' The first step of the regridding routine!
    There is an important reason why the regridding is broken into two steps
    (making the regridder and perform regridding). For high-resolution grids, 
    making the regridder (i.e. “computing regridding weights”, explained later) 
    is quite computationally expensive, 
    but performing regridding on data (“applying regridding weights”) is still pretty fast.
    
    Parameters
    ----------
    ds : xarray.DataSet, with model grid information for the data which need to be regridded 
    outgrid : xarray.DataSet, with output grid information which the data will be regridded to
    regrid_mode : str,  ['bilinear', 'conservative', 'patch', 'nearest_s2d', 'nearest_d2s']
    grid_weight_path : str, path to where the  regridder weight file will be stored
    reuse_weights :  bool, set to True to read existing weights from disk.
                           set to False if new weights need to be calculated
    Returns
    -------
    regridder : xarray.DataSet with regridder weight file information
    '''
    ds_in = make_bounds(modelname, ds)
    regridder = xe.Regridder(ds_in, outgrid, regrid_mode,
                             filename=grid_weight_path+'model_to_grid_'+regrid_mode+'.nc',
                             reuse_weights=reuse_weights)
    return regridder





