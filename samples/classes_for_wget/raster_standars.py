from typing import List,Tuple
import numpy as np
import os
import rasterio
from rasterio.enums import Resampling


class Raster_Standards:
  def __init__(self, resolution:float=0.00833333333333,crs:int=4326,no_data_val:float=-9999.0,country_limits:Tuple=(-73.981934,-34.792929, -33.750035, 5.271478)):
      #https://epsg.io/map
      #https://en.wikipedia.org/wiki/List_of_extreme_points_of_Brazil
      
      self.security_limt = 1
      self.x_min_limit = country_limits[0] -self.security_limt # Coordenadas DMS: 07°32′39″S 073°59′04″W; Coordenada Decimal Geohack: -7.544167, -73.984444; Corrdenada Decimal epsg.io: -7.535403, -73.981934
      self.x_max_limit = country_limits[1] +self.security_limt # Coordenadas DMS: 07°09′28″S 034°47′38″W; Coordenada Decimal Geohack: -20.474444, -28.840556; Corrdenada Decimal epsg.io: -7.155017, -34.792929
      self.y_min_limit = country_limits[2] -self.security_limt # Coordenadas DMS: 33°45′09″S 053°22′07″W; Coordenada Decimal Geohack: -33.7525, -53.368611; Corrdenada Decimal epsg.io: -33.750035, -53.407288
      self.y_max_limit = country_limits[3] +self.security_limt # Coordenadas DMS: 05°15′05″N 060°12′33″W; Coordenada Decimal Geohack: 5.251389, -60.209167; Corrdenada Decimal epsg.io: 5.271478, -60.214691
      self.resolution =  resolution
      self.crs = crs  #WGS84 EPSG:4326
      self.no_data_val = no_data_val
      grid_infos = self._construct_grids()
      self.xgrid = grid_infos[0]
      self.ygrid = grid_infos[1]
      self.Nx = grid_infos[2] 
      self.Ny = grid_infos[3]
      self.x_center_point = np.median(self.xgrid)
      self.y_center_point = np.median(self.ygrid)

  

  def _construct_grids(self):
      """Construct the map grid from the batch object

      Parameters
      ----------
      batch : Batch object
          The object returned by :func:`fetch_species_distributions`

      Returns
      -------
      (xgrid, ygrid) : 1-D arrays
          The grid corresponding to the values in batch.coverages
      """

      # x coordinates of the grid cells
      xgrid = np.arange(self.x_min_limit, self.x_max_limit, self.resolution)
      # y coordinates of the grid cells
      ygrid = np.arange(self.y_min_limit, self.y_max_limit, self.resolution)
      # x array size
      Nx = len(xgrid)
      # y array size
      Ny = len(ygrid)

      return (xgrid, ygrid,Nx,Ny)

    
  def _reescale(self,raster_array,raster_object):
      if not (round(self.raster_standars.resolution,5) == round(raster.meta['transform'][0],5)):
        aux = self.resolution/actual_grid
        reescale_factor = 1/aux

        # resample data to target shape
        data = raster_array.read(
            out_shape=(
                raster_array.count,
                int(raster_array.height * reescale_factor),
                int(raster_array.width * reescale_factor)
            ),
            resampling=Resampling.bilinear
        )

        # scale image transform
        transform = raster_array.transform * raster_array.transform.scale(
            (raster_array.width / data.shape[-1]),
            (raster_array.height / data.shape[-2])
        )
      else:
        data = raster_array
        transform = raster_object.meta['transform']
      return data[0],transform

  def _get_window_from_extent(self,aff):
    col_start, row_start = ~aff * (self.x_min_limit, self.y_max_limit)
    col_stop, row_stop = ~aff * (self.x_max_limit, self.y_min_limit)
    return ((int(row_start), int(row_stop)), (int(col_start), int(col_stop)))

  def get_land_reference_array_mask(self,land_reference_path):
      raster = rasterio.open(land_reference_path)
      raster_array = raster.read(1,window = self._get_window_from_extent(raster.meta['transform']))
      raster_array,_ = self._reescale(raster_array,raster)
      return raster_array

  def read_array_standarized(self,raster):

      #Extraction only the window from Raster Standars Object
      raster_array = raster.read(1,window = self._get_window_from_extent(raster.meta['transform']))

      #Resampling
      if not (round(self.resolution,5) == round(raster.meta['transform'][0],5)):
        raster_array = self._reescale(raster_array,raster)
        print(f"The Raster resolution was converted from {raster.meta['transform'][0]} to {self.resolution}")

      #converting nodata valye if necessary
      if raster.nodata != self.no_data_val:
        raster_array[raster_array==raster.nodata] = self.no_data_val
        print(f"The Raster no data value converted from EPSG {raster.nodata} to EPSG:{self.no_data_val}")

      return raster_array
    