#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 27 16:30:24 2021

@author: Ada Gjermundsen

General python functions for analyzing NorESM data 

"""
import xarray as xr
import numpy as np
import warnings
warnings.simplefilter('ignore')

def consistent_naming(ds):
    '''
    The naming convention for coordinates and dimensions are not the same 
    for noresm raw output and cmorized variables. This function rewrites the 
    coords and dims names to be consistent and the functions thus work on all
    Choose the cmor naming convention.

    Parameters
    ----------
    ds : xarray.Daraset 

    Returns
    -------
    ds : xarray.Daraset

    '''
    if 'latitude' in ds.coords and 'lat' not in ds.coords:
        ds = ds.rename({'latitude':'lat'})
    if 'longitude' in ds.coords and 'lon' not in ds.coords:
        ds = ds.rename({'longitude':'lon'})
    if 'region' in ds.dims:
        ds = ds.rename({'region':'basin'}) # are we sure that it is the dimension and not the variable which is renamed? Probably both   
        # note in BLOM raw, region is both a dimension and a variable. Not sure how xarray handles that
        # in cmorized variables sector is the char variable with the basin names, and basin is the dimension 
        # don't do this -> ds = ds.rename({'region':'sector'})
    if 'x' in ds.dims:
        ds = ds.rename({'x':'i'})
    if 'y' in ds.dims:
        ds = ds.rename({'y':'j'})
    if 'depth' in ds.dims:
        ds = ds.rename({'depth':'lev'})
    if 'bounds' in ds.dims:
        ds = ds.rename({'bounds':'bnds'})
    return ds


def global_mean(ds):
    '''Calculates globally averaged values

    Parameters
    ----------
    ds : xarray.DaraArray i.e. ds[var]

    Returns
    -------
    ds_out :  xarray.DaraArray with globally averaged values
    '''
    # to include functionality for subsets or regional averages:
    if 'time' in ds.dims:
        weights = xr.ufuncs.cos(xr.ufuncs.deg2rad(ds.lat))*ds.notnull().mean(dim=('lon','time'))
    else:
        weights = xr.ufuncs.cos(xr.ufuncs.deg2rad(ds.lat))*ds.notnull().mean(dim=('lon'))
    ds_out = (ds.mean(dim='lon')*weights).sum(dim='lat')/weights.sum()
    if 'long_name'  in ds.attrs:
        ds_out.attrs['long_name']= 'Globally averaged ' + ds.long_name
    if 'units'  in ds.attrs:
        ds_out.attrs['units']=ds.units
    if 'standard_name'  in ds.attrs:
        ds_out.attrs['standard_name']=ds.standard_name
    return ds_out

def yearly_avg(ds):
    ''' Calculates timeseries over yearly averages from timeseries of monthly means
    The weighted average considers that each month has a different number of days.

    Parameters
    ----------
    ds : xarray.DaraArray i.e. ds[var]

    Returns
    -------
    ds_weighted : xarray.DaraArray with yearly averaged values
    '''
    month_length = ds.time.dt.days_in_month
    weights = month_length.groupby('time.year') / month_length.groupby('time.year').sum()
    # Test that the sum of the weights for each year is 1.0
    np.testing.assert_allclose(weights.groupby('time.year').sum().values,
                               np.ones(len(np.unique(ds.time.dt.year))))
    # Calculate the weighted average:
    ds_weighted = (ds * weights).groupby('time.year').sum(dim='time')
    if 'long_name'  in ds.attrs:
        ds_weighted.attrs['long_name']= 'Annual mean ' + ds.long_name
    if 'units' in ds.attrs:
        ds_weighted.attrs['units']=ds.units
    if 'standard_name'  in ds.attrs:
        ds_weighted.attrs['standard_name']=ds.standard_name

    return ds_weighted

def seasonal_avg_timeseries(ds, var=''):
    '''Calculates timeseries over seasonal averages from timeseries of monthly means
    The weighted average considers that each month has a different number of days.
    Using 'QS-DEC' frequency will split the data into consecutive three-month periods, 
    anchored at December 1st. 
    I.e. the first value will contain only the avg value over January and February 
    and the last value only the December monthly averaged value
    
    Parameters
    ----------
    ds : xarray.DaraArray i.e.  ds[var]
        
    Returns
    -------
    ds_out: xarray.DataSet with 4 timeseries (one for each season DJF, MAM, JJA, SON)
            note that if you want to include the output in an other dataset, e.g. dr,
            you should use xr.merge(), e.g.
            dr = xr.merge([dr, seasonal_avg_timeseries(dr[var], var)])
    '''
    month_length = ds.time.dt.days_in_month
    sesavg = ((ds * month_length).resample(time='QS-DEC').sum() /
              month_length.where(ds.notnull()).resample(time='QS-DEC').sum())
    djf = sesavg[0::4].to_dataset(name = var + '_DJF').rename({'time':'time_DJF'})
    mam = sesavg[1::4].to_dataset(name = var +'_MAM').rename({'time':'time_MAM'})
    jja = sesavg[2::4].to_dataset(name = var +'_JJA').rename({'time':'time_JJA'})
    son = sesavg[3::4].to_dataset(name = var +'_SON').rename({'time':'time_SON'})
    ds_out = xr.merge([djf, mam, jja, son])
    ds_out.attrs['long_name']= 'Seasonal mean ' + ds.long_name
    ds_out.attrs['units']=ds.units
    if 'standard_name'  in ds.attrs:
        ds_out.attrs['standard_name']=ds.standard_name
    return ds_out

def seasonal_avg(ds):
    '''Calculates seasonal averages from timeseries of monthly means
    The time dimension is reduced to 4 seasons: 
        * season   (season) object 'DJF' 'JJA' 'MAM' 'SON'
    The weighted average considers that each month has a different number of days.
    
    Parameters
    ----------
    ds : xarray.DaraArray i.e.  ds[var]
        
    Returns
    -------
    ds_weighted : xarray.DaraArray 
    '''
    month_length = ds.time.dt.days_in_month
    # Calculate the weights by grouping by 'time.season'.
    weights = month_length.groupby('time.season') / month_length.groupby('time.season').sum()
    # Test that the sum of the weights for each season is 1.0
    np.testing.assert_allclose(weights.groupby('time.season').sum().values, np.ones(4))
    # Calculate the weighted average
    ds_weighted = (ds * weights).groupby('time.season').sum(dim='time')
    ds_weighted.attrs['long_name']= 'Seasonal mean ' + ds.long_name
    ds_weighted.attrs['units']=ds.units
    if 'standard_name'  in ds.attrs:
        ds_weighted.attrs['standard_name']=ds.standard_name
    return ds_weighted


def mask_region_latlon(ds, lat_low=-90, lat_high=90, lon_low=0, lon_high=360):
    '''Subtract data from a confined region
    Note, for the atmosphere the longitude values go from 0 -> 360.
    Also after regridding
    This is not the case for ice and ocean variables for which some cmip6 models
    use -180 -> 180
    
    Parameters
    ----------
    ds : xarray.DataArray or xarray.DataSet
    lat_low : int or float, lower latitude boudary. The default is -90.
    lat_high : int or float, lower latitude boudary. The default is 90.
    lon_low :  int or float, East boudary. The default is 0.
    lon_high : int or float, West boudary. The default is 360.
    
    Returns
    -------
    ds_out : xarray.DataArray or xarray.DataSet with data only for the selected region
    
    Then it is still possible to use other functions e.g. global_mean(ds) to 
    get an averaged value for the confined region 
    '''
    ds_out = ds.where((ds.lat>=lat_low) & (ds.lat<=lat_high))
    if lon_high>lon_low:
        ds_out = ds_out.where((ds_out.lon>=lon_low) & (ds_out.lon<=lon_high))
    else:
        boole = (ds_out.lon.values <= lon_high) | (ds_out.lon.values >= lon_low)
        ds_out = ds_out.sel(lon=ds_out.lon.values[boole])
    if 'long_name' in ds.attrs:
        ds_out.attrs['long_name']= 'Regional subset (%i,%i,%i,%i) of '%(lat_low,lat_high,lon_low,lon_high) + ds.long_name 
    if 'units' in ds.attrs:
        ds_out.attrs['units']=ds.units
    if 'standard_name'  in ds.attrs:
        ds_out.attrs['standard_name']= 'Regional subset (%i,%i,%i,%i) of '%(lat_low,lat_high,lon_low,lon_high) + ds.standard_name
    return ds_out


def get_areacello(cmor=True):
    '''
    only if pweight / areacello is not provided. Only works for 1deg ocean (CMIP6) as it is now
    '''
    if not cmor:
        # This path only works on FRAM and BETZY
        grid = xr.open_dataset('/cluster/shared/noresm/inputdata/ocn/blom/grid/grid_tnx1v4_20170622.nc')
        pweight = grid.parea*grid.pmask.where(grid.pmask>0)
        # add latitude and longitude info good to have in case of e.g. regridding
        pweight = pweight.assign_coords(lat=grid.plat)
        pweight = pweight.assign_coords(lon=grid.plon)
    if cmor:
        # This path only works on NIRD. NS9034 is not mounted in /trd-projects* so impossible to add a general path
        area = xr.open_dataset('/projects/NS9034K/CMIP6/CMIP/NCC/NorESM2-MM/piControl/r1i1p1f1/Ofx/areacello/gn/latest/areacello_Ofx_NorESM2-MM_piControl_r1i1p1f1_gn.nc')
        mask = xr.open_dataset('/projects/NS9034K/CMIP6/CMIP/NCC/NorESM2-MM/piControl/r1i1p1f1/Ofx/sftof/gn/latest/sftof_Ofx_NorESM2-MM_piControl_r1i1p1f1_gn.nc')
        pweight = area.areacello*mask.sftof
    pweight = consistent_naming(pweight)
    return pweight


def sea_ice_ext(ds, pweight = None, cmor = True):
    ''' 
    Calculates the sea ice extent from the sea ice concentration fice in BLOM raw output and siconc in cmorized files
    Sea ice concentration (fice or siconc) is the percent areal coverage of ice within the ocean grid cell. 
    Sea ice extent is the integral sum of the areas of all grid cells with at least 15% ice concentration.
    
    Parameters
    ----------
    ds : xarray.DaraArray i.e.  ds[var] (var = fice in BLOM)
    pweight : xarray.DataArray with area information
    
    Returns
    -------
    ds_out : xarray.DaraSet with sea-extent for each hemisphere, in March and in September

    '''
    ds_out = None
    if not isinstance(pweight,xr.DataArray):
        pweight = get_areacello(cmor = cmor)
    for monthnr in [3, 9]:
        da = ds.sel(time = ds.time.dt.month == monthnr)
        parea = pweight.where(da>=15)
        SHout = parea.where(pweight.lat <=0).sum(dim=('i','j'))/(1E6*(1000*1000))
        SHout.attrs['standard_name'] = 'siext_SH_0%i'%monthnr
        SHout.attrs['units'] = '10^6 km^2'
        SHout.attrs['long_name'] = 'southern_hemisphere_sea_ice_extent_month_0%i'%monthnr
        NHout = parea.where(pweight.lat >=0).sum(dim=('i','j'))/(1E6*(1000*1000))
        NHout.attrs['standard_name'] = 'siext_NH_0%i'%monthnr
        NHout.attrs['units'] = '10^6 km^2'
        NHout.attrs['long_name'] = 'northern_hemisphere_sea_ice_extent_month_0%i'%monthnr
        if isinstance(ds_out,xr.Dataset):
            ds_out = xr.merge([ds_out, SHout.to_dataset(name = 'siext_SH_0%i'%monthnr), NHout.to_dataset(name = 'siext_NH_0%i'%monthnr)])
        else:
            ds_out = xr.merge([SHout.to_dataset(name = 'siext_SH_0%i'%monthnr), NHout.to_dataset(name = 'siext_NH_0%i'%monthnr)])
        
    return ds_out

def sea_ice_area(ds, pweight = None, cmor = True):
    ''' 
    Calculates the sea ice extent from the sea ice concentration fice in BLOM raw output and siconc in cmorized files
    Sea ice concentration (fice or siconc) is the percent areal coverage of ice within the ocean grid cell. 
    Sea ice area is the integral sum of the product of ice concentration and area of all grid cells with at least 15% ice concentration
    
    Parameters
    ----------
    ds : xarray.DaraArray i.e.  ds[var] (var = fice in BLOM)
    pweight : xarray.DataArray with area information
    
    Returns
    -------
    ds_out : xarray.DaraSet with sea-extent for each hemisphere, in March and in September

    '''
    ds_out = None
    if not isinstance(pweight,xr.DataArray):
        pweight = get_areacello(cmor = cmor)
    for monthnr in [3, 9]:
        da = ds.sel(time = ds.time.dt.month == monthnr)
        parea = (da*pweight).where(da>=15)
        SHout = parea.where(pweight.lat <=0).sum(dim=('i','j'))/100/(1E6*(1000*1000))
        SHout.attrs['standard_name'] = 'siarea_SH_0%i'%monthnr
        SHout.attrs['units'] = '10^6 km^2'
        SHout.attrs['long_name'] = 'southern_hemisphere_sea_ice_area_month_0%i'%monthnr
        NHout = parea.where(pweight.lat >=0).sum(dim=('i','j'))/100/(1E6*(1000*1000))
        NHout.attrs['standard_name'] = 'siarea_NH_0%i'%monthnr
        NHout.attrs['units'] = '10^6 km^2'
        NHout.attrs['long_name'] = 'northern_hemisphere_sea_ice_area_month_0%i'%monthnr
        if isinstance(ds_out,xr.Dataset):
            ds_out = xr.merge([ds_out, SHout.to_dataset(name = 'siarea_SH_0%i'%monthnr), NHout.to_dataset(name = 'siarea_NH_0%i'%monthnr)])
        else:
            ds_out = xr.merge([SHout.to_dataset(name = 'siarea_SH_0%i'%monthnr), NHout.to_dataset(name = 'siarea_NH_0%i'%monthnr)])

    return ds_out

def select_atlantic_latbnds(ds):
    '''
    Selects the Atlantic meridional overtuning streamfunction / heat transport 
    @2&N (rapid), @45N and the maximum between 20N and 60N

    Parameters
    ----------
    ds : xarray.DaraArray i.e.  ds[var] var = mmflxd (raw) and var = msftmz (cmorized) 
                             or ds[var] var = mhflx (raw) and var = hfbasin (cmorized)
    
    Returns
    -------
    a zip list of the 3 sections xarray.DataArray and the latitudes for the corresponding sections 
 
    '''
    # basin = 0 ->  sector = atlantic_arctic_ocean
    ds = ds.isel(basin = 0)
    amoc26 = ds.sel(lat=26)
    amoc45 = ds.sel(lat=45)
    amoc20_60 = ds.sel(lat=slice(20,60)).max(dim='lat')
    return zip([amoc26, amoc45, amoc20_60],['26N', '45N', 'max20N_60N'])
        
    
def amoc(ds):
    ''' 
    Calculates the Atlantic meridional overturning circulation 
    @26N (rapid), @45N and the maximum between 20N and 60N  
    
    Parameters
    ----------
    ds : xarray.DaraArray i.e.  ds[var] var = mmflxd (raw) and var = msftmz (cmorized)
    
    Returns
    -------
    ds_out : xarray.DaraSet with AMOC @26N, 45N and max(20N,60N)
    '''
    ds_out = None
    zipvals = select_atlantic_latbnds(ds)
    for da, lat_lim in zipvals:
        da = 1e-9*da.max(dim = 'lev')
        da.attrs['long_name']='Max Atlantic Ocean Overturning Mass Streamfunction @%s'%lat_lim
        da.attrs['units']='kg s-1'
        da.attrs['standard_name']='max_atlantic_ocean_overturning_mass_streamfunction_%s'%lat_lim
        da.attrs['description']='Max Atlantic Overturning mass streamfunction arising from all advective mass transport processes, resolved and parameterized @%s'%lat_lim
        if 'lat' in da.coords:
            da.attrs['lat']='%.1fN'%da.lat.values
            da = da.drop('lat')
        if 'basin' in da.coords:
            da.attrs['basin']='%s'%da.basin.values
            da = da.drop('basin')
        da = da.to_dataset(name = 'amoc_%s'%lat_lim)
        if isinstance(ds_out,xr.Dataset):
            ds_out = xr.merge([ds_out, da])
        else:
            ds_out = da
    return ds_out

def atl_hfbasin(ds):
    ''' 
    Calculates the Atlantic northward ocean heat transport 
    @26N (rapid), @45N and the maximum between 20N and 60N  
    
    Parameters
    ----------
    ds : xarray.DaraArray i.e.  ds[var] var = mhflx (raw) and var = hfbasin (cmorized)
    
    Returns
    -------
    ds_out : xarray.DaraSet with AOHT @26N, 45N and max(20N,60N)
    '''
    ds_out = None
    zipvals = select_atlantic_latbnds(ds)
    for da, lat_lim in zipvals:
        da = 1E-15*da
        da.attrs['long_name']='Atlantic Northward Ocean Heat Transport @%s'%lat_lim
        da.attrs['units']='PW'
        da.attrs['standard_name']='atlantic_northward_ocean_heat_transport_%s'%lat_lim
        da.attrs['description']='Contains contributions from all physical processes affecting the northward heat transport, including resolved advection, parameterized advection, lateral diffusion, etc.'
        if 'lat' in da.coords:
            da.attrs['lat']='%.1fN'%da.lat.values
            da = da.drop('lat')
        if 'basin' in da.coords:
            da.attrs['basin']='%s'%da.basin.values
            da = da.drop('basin')
        da = da.to_dataset(name = 'aoht_%s'%lat_lim)
        if isinstance(ds_out,xr.Dataset):
            ds_out = xr.merge([ds_out, da])
        else:
            ds_out = da
    return ds_out


def areaavg_ocn(ds, pweight=None, cmor = True):
    ''' 
    Calculates area averaged values   
    
    Parameters
    ----------
    ds : xarray.DaraArray i.e.  ds[var] 
    
    Returns
    -------
    ds_out : xarray.DaraArray
    '''
    if not isinstance(pweight,xr.DataArray):
        pweight = get_areacello(cmor = cmor)
    ds_out = ((ds*pweight).sum(dim=("j","i")))/pweight.sum()  
    if 'long_name'  in ds.attrs:
        ds_out.attrs['long_name']= 'Globally averaged ' + ds.long_name
    if 'units'  in ds.attrs:
        ds_out.attrs['units']=ds.units
    if 'standard_name'  in ds.attrs:
        ds_out.attrs['standard_name']=ds.standard_name
    return ds_out

def regionalavg_ocn(ds, lat_low=-90, lat_high=90, lon_low=0, lon_high=360, pweight=None, cmor = True):
    ''' 
    Calculates area averaged values   
    
    Parameters
    ----------
    ds : xarray.DaraArray i.e.  ds[var] 
    
    Returns
    -------
    ds_out : xarray.DaraArray
    '''
    if not isinstance(pweight,xr.DataArray):
        pweight = get_areacello(cmor = cmor)
    pweight = mask_region_latlon(pweight, lat_low=lat_low, lat_high=lat_high, lon_low=lon_low, lon_high=lon_high)
    ds_out = ((ds*pweight).sum(dim=("j","i")))/pweight.sum()
    if 'long_name'  in ds.attrs:
        ds_out.attrs['long_name']= 'Regional avg (%i,%i,%i,%i) '%(lat_low,lat_high,lon_low,lon_high) + ds.long_name
    if 'units'  in ds.attrs:
        ds_out.attrs['units']=ds.units
    if 'standard_name'  in ds.attrs:
        ds_out.attrs['standard_name']=ds.standard_name
    return ds_out

def volumeavg_ocn(ds, dp, pweight=None, cmor = True):
    ''' 
    Calculates volume averaged values   
    
    Parameters
    ----------
    ds : xarray.DaraArray i.e. ds[var] e.g. var = thatao, so, tempn, saltn 
    dp : xarray.DataArray with pressure thinkness
   
    Returns
    -------
    ds_out : xarray.DaraArray
    '''
    if not isinstance(pweight,xr.DataArray):
        pweight = get_areacello(cmor = cmor)
    if 'sigma' in ds.coords:
        ds = (ds*dp).sum(dim='sigma')
        dpweight = dp.sum(dim='sigma')
        ds_out = (pweight*ds).sum(dim=('j','i'))/(pweight*dpweight).sum(dim=('i','j'))
    if 'long_name'  in ds.attrs:
        ds_out.attrs['long_name']= 'Volume averaged ' + ds.long_name
    if 'units'  in ds.attrs:
        ds_out.attrs['units']=ds.units
    if 'standard_name'  in ds.attrs:
        ds_out.attrs['standard_name']=ds.standard_name
    return ds_out
   