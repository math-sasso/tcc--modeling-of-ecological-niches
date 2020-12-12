from typing import List,Tuple
import numpy as np
import os
import rasterio
from rasterio.enums import Resampling
from rasterio.plot import show


class Raster_Standards:
  
  """
  This class is reponsable for define all the raster base parametes used on the project and for applying operations on raster arrays

   Attributes
  ----------
  security_limt : int
    Limit to extrapolate territory boarders in all directions
  x_min_limit : float
      Country most western point considering security_limit
  x_max_limit : float
      Country most eastern point considering security_limit
  y_min_limit : float
      Country most south point considering security_limit
  y_max_limit : float
      Country most north point considering security_limit
  resolution : int
      Raster resolution
  crs : int
      CRS code for map projection
  no_data_val : int
      No data value
  positive_mask_val : int
      Positive mask value
  negative_mask_val : int
      Negative mask value
  xgrid : array
      Grid of values for refernce map on X
  ygrid : array
      Grid of values for refernce map on Y
  x_center_point : int
      Center point X coordinate
  y_center_point : int
      Center point Y coordinate
  """

  def __init__(self, raster_base_configs):
      """
      Parameters
      ----------
      raster_base_configs : Dict
          Configurations for raster Standards (resolution,crs,no_data_val,positive_mask_val,negative_mask_val and country_limits)
      """

      self.security_limt = 1
      country_limits = raster_base_configs['country_limits']
      self.x_min_limit = country_limits[0] -self.security_limt # Coordenadas DMS: 07°32′39″S 073°59′04″W; Coordenada Decimal Geohack: -7.544167, -73.984444; Corrdenada Decimal epsg.io: -7.535403, -73.981934
      self.x_max_limit = country_limits[1] +self.security_limt # Coordenadas DMS: 07°09′28″S 034°47′38″W; Coordenada Decimal Geohack: -20.474444, -28.840556; Corrdenada Decimal epsg.io: -7.155017, -34.792929
      self.y_min_limit = country_limits[2] -self.security_limt # Coordenadas DMS: 33°45′09″S 053°22′07″W; Coordenada Decimal Geohack: -33.7525, -53.368611; Corrdenada Decimal epsg.io: -33.750035, -53.407288
      self.y_max_limit = country_limits[3] +self.security_limt # Coordenadas DMS: 05°15′05″N 060°12′33″W; Coordenada Decimal Geohack: 5.251389, -60.209167; Corrdenada Decimal epsg.io: 5.271478, -60.214691
      self.resolution =  raster_base_configs['resolution']
      self.crs = raster_base_configs['crs']   #WGS84 EPSG:4326
      self.no_data_val = raster_base_configs['no_data_val'] 
      self.positive_mask_val = raster_base_configs['positive_mask_val']
      self.negative_mask_val = raster_base_configs['positive_mask_val']
      self.reference_raster = rasterio.open("/content/drive/MyDrive/Mestrado/Deep Learning/Projeto/Data/Standarized_Rasters/Base_Rasters/brazilian_mask_standarized.tif ")
      grids = self._construct_grids()
      self.xgrid = grids[0]
      self.ygrid = grids[1]
      self.x_center_point = np.median(self.xgrid)
      self.y_center_point = np.median(self.ygrid)

  

  def _construct_grids(self):
      """Construct the map grid from the batch object"""
      ref_aff = self.reference_raster.meta['transform']
      ref_width = self.reference_raster.profile['width']
      ref_heigh = self.reference_raster.profile['height']
      # X limits
      x_min_limit = ref_aff[2]
      x_max_limit = x_min_limit + ref_aff[0]*ref_width
      # Y limits
      y_max_limit = ref_aff[5]
      y_min_limit = y_max_limit + ref_aff[4]*ref_heigh


      xgrid = np.arange(x_min_limit, x_max_limit,ref_aff[0])
      ygrid = np.arange(y_min_limit, y_max_limit, ref_aff[0])


      return (xgrid,ygrid)


    
  def _reescale(self,raster_array,raster_object):
      """ Reescale a raster array on the desired resolution """
      if not (round(self.resolution,5) == round(raster_object.meta['transform'][0],5)):
        aux = self.resolution/raster.meta['transform'][0]
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
        data = data[0]
      else:
        data = raster_array
        transform = raster_object.meta['transform']
      return data,transform

  def _get_window_from_extent(self,aff):
    """ Get a portion form a raster array based on the country limits"""
    col_start, row_start = ~aff * (self.x_min_limit, self.y_max_limit)
    col_stop, row_stop = ~aff * (self.x_max_limit, self.y_min_limit)
    return ((int(row_start), int(row_stop)), (int(col_start), int(col_stop)))

  def _read_array_standarized(self,raster,raster_name):
      """ Performs verifications and standarizations for raster arrays """

      #1 Check if orientaion from Affine position 4 is negative
      res_n_s = raster.meta['transform'][4]
      if res_n_s > 0:
        raise Exception("Behavior not expected. The North South resolution is excpected to be negative")

      #2 Checking the number of raster layers 
      if raster.meta['count']>1:
        raise Exception("For some reason there are more than one layer in this raster")
      if raster.meta['count']==0:
        raise Exception("For some reason this raster is empty")

      #3 Checking CRS
      raster_code = int(raster.crs.data['init'].split(':')[1])
      if raster_code != self.crs:
        raise Exception("Sorry,crs from this raster is no EPSG:4326")
        # raster = raster.to_crs(epsg=self.crs)

      #4 Extracting only the window from Raster Standars Object
      raster_array = raster.read(1)


      #5 Resampling
      if not (round(self.reference_raster.meta['transform'][0],5) == round(raster.meta['transform'][0],5)):
         raise Exception(f"Files are not on the same resolution. That should be {round(self.reference_raster.meta['transform'][0],5)}")
      
      #6 converting nodata value if necessary
      if raster.nodata != self.no_data_val:
        raise Exception(f"Raster dont have default no data val. That should be {self.no_data_val}")


      #6 converting nodata value if necessary
      if raster.nodata != self.no_data_val:
        raise Exception(f"Raster dont have default no data val. That should be {self.no_data_val}")
        

      #7 Asserting that numpy array will be float32
      if raster.meta['dtype'] != self.reference_raster.meta['dtype']:
        raise Exception(f"Raster dont have default dtype. That should be {self.reference_raster.meta['dtype']}")
      
      #8 Setting raster to none. The information that matters is the rater aray
      raster = None

      return raster_array
  
  def get_land_reference_array_mask(self,land_reference_path):
      """ Returns the reference array mask conseidering scales and limits"""
      raster = rasterio.open(land_reference_path)
      raster_array = raster.read(1,window = self._get_window_from_extent(raster.meta['transform']))
      raster_array,_ = self._reescale(raster_array,raster)
      return raster_array

  def get_raster_array(self,path,print_example = False):
      """ Returns a raster array with all the standarizations applied"""
      #openning raster
      raster = rasterio.open(path)
      #get standarized raster array
      raster_array = self._read_array_standarized(raster,path.split("/")[-1])   
      return raster_array
    
  def get_rasters_from_dir(self,dir_path):
      """ Read all the .tif files on the standarized format and stack them"""
      rasters = []
      for (dirpath, dirnames, filenames) in os.walk(dir_path):
        dir_files_paths_list = sorted([os.path.join(dir_path, fname) for fname in filenames])
        for filepath,filename in zip(dir_files_paths_list,filenames):
          if filename.endswith('.tif'):
            raster_array  = self.get_raster_array(filepath)
            rasters.append(raster_array) 
            del raster_array
        break
      
      result =  np.stack([value for value in rasters])
      del rasters

      return result

  def get_land_reference_array_infos(self,country_mask_reference):
      """ Returns infos (raster_array,xgrid,ygrid) from a contry mask reference array"""
      raster = rasterio.open(country_mask_reference)
      resolution = raster.meta['transform'][0]
      raster_array = raster.read(1,window = self._get_window_from_extent(raster.meta['transform']))
      raster_array,_ = self._reescale(raster_array,raster)
      xgrid = np.arange(self.x_min_limit, self.x_min_limit+raster_array.shape[1]*resolution, resolution)
      ygrid = np.arange(self.y_min_limit, self.y_min_limit+raster_array.shape[0]*resolution, resolution)
      return raster_array,xgrid,ygrid
  