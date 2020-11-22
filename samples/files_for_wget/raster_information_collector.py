from typing import List,Tuple
import gc
from sklearn.utils import Bunch
import geopandas as gpd
import rasterio
import numpy as np
from rasterio.plot import show
from rasterio.windows import Window
from osgeo import gdal
from matplotlib import pyplot



class Raster_Information_Collector:
  """
  This class is reponsable for extracting data from rasters on GBIF occurrence locations

  Attributes
  ----------
  raster_base_configs : str
      Directory to save coverages
  coorection_limit : int
      Limit of iterations to correct no information points
  raster_standards : object
      Raster standards object
  """

  def __init__(self, output_dir:str,raster_standards,coorection_limit:int=10):
      """
      Parameters
      ----------
      raster_base_configs : str
          Directory to save coverages
      coorection_limit : int
          Limit of iterations to correct no information points
      raster_standards : object
          Raster standards object
      """

      self.output_dir = output_dir
      self.raster_standards = raster_standards
      self.coorection_limit = coorection_limit

  def _treat_boarder_points(self,Long,Lat,ix,iy,raster_array,raster_occurrences_array):
      "Repair problems on points very near to the the country boarders by getting nearest values on the center point direction"

      for i,elem in enumerate(raster_occurrences_array):
        if elem == -9999.0:
          point_x,point_y = Long[i],Lat[i]
          base_point_x,base_point_y = point_x.copy(),point_y.copy()
          incx,incy = 0,0
          k = 0
          #walking coodinates in center map
          while (elem==-9999.0 and k<self.coorection_limit):
            if point_x >= self.raster_standards.x_center_point and  point_y >= self.raster_standards.y_center_point:
              point_x -= self.raster_standards.resolution
              point_y -= self.raster_standards.resolution
              incx -= 1
              incy -= 1
            if point_x >= self.raster_standards.x_center_point and  point_y <= self.raster_standards.y_center_point:
              point_x -= self.raster_standards.resolution
              point_y += self.raster_standards.resolution
              incx -= 1
              incy += 1
            if point_x <= self.raster_standards.x_center_point and  point_y <= self.raster_standards.y_center_point:
              point_x += self.raster_standards.resolution
              point_y += self.raster_standards.resolution
              incx += 1
              incy += 1
            if point_x <= self.raster_standards.x_center_point and  point_y >= self.raster_standards.y_center_point:
              point_x += self.raster_standards.resolution
              point_y -= self.raster_standards.resolution
              incx += 1
              incy -= 1           

            new_ix = ix[i]+incx
            new_iy = iy[i]+incy

            value = raster_array[-new_iy,new_ix].T
            if value != -9999.0:
              raster_occurrences_array[i] = value
              elem = value
              print(f"The raster coordniate info was changed from the point {(base_point_x,base_point_y)} to the point {(point_x,point_y)}")
            k+=1
      return raster_occurrences_array  

  def _fill_peristent_no_data_values_with_mean(self,raster_occurrences_array):
      """ For grids that still with empty value after the board points treatment, this function fill it with the mean value"""

      mean_value = np.mean(raster_occurrences_array[[raster_occurrences_array!=-9999.0]])
      for i,elem in enumerate(raster_occurrences_array):
        if elem == -9999.0:
          raster_occurrences_array[i] = mean_value
      
      return raster_occurrences_array

  def _update_coverages(self,species_name,coverage):
      """ Treats if a new numpy array is created or if an existing one is updated"""
      try:
          with open(self.output_dir+'/'+species_name + '.npy', 'rb') as f:
            numpy_raster_info = np.load(f)
            coverage = np.concatenate((numpy_raster_info,coverage),axis=1)
            with open(self.output_dir+'/'+species_name  + '.npy', 'wb') as f:
              np.save(f, coverage)
      except Exception as e:
          print(e)
          with open(self.output_dir+'/'+species_name + '.npy', 'wb') as f:
            np.save(f, coverage)
      print(species_name + ' successfully saved on the folder ' + self.output_dir + "with shape: " ,coverage.shape)

  def save_coverges_to_numpy(self,specie_dir:str,species_name:str,root_raster_files_list:List[str]):
    """ Save all extracted to a numpy array"""

    data = gpd.read_file(specie_dir)
    coordinates = np.array((np.array(data['LATITUDE']),np.array(data['LONGITUDE']))).T
        
    # determine coverage values for each of the training & testing points
    Long = coordinates[:,1]
    Lat = coordinates[:,0]
    ix = np.searchsorted(self.raster_standards.xgrid,Long)
    iy = np.searchsorted(self.raster_standards.ygrid,Lat)

    all_env_values_list = []
    for i,fp in enumerate(root_raster_files_list):
        
        # Exctraction occurences from rasters
        raster_array = self.raster_standards.get_raster_array(fp)
        raster_occurrences_array = raster_array[-iy, ix].T
        
        #treating cases where points that should be inside country are outside
        raster_occurrences_array = self._treat_boarder_points(Long,Lat,ix,iy,raster_array,raster_occurrences_array)
        del raster_array

        #tretaing cases that still with no data values
        raster_occurrences_array= self._fill_peristent_no_data_values_with_mean(raster_occurrences_array)
        
        #selecting the env value on the occurrence position
        all_env_values_list.append(raster_occurrences_array)

        del raster_occurrences_array
        gc.collect()

    coverage= np.stack([value for value in all_env_values_list]).T
    del ix
    del iy
    del all_env_values_list
    gc.collect() 

    self._update_coverages(species_name,coverage)
    
    del coverage
    gc.collect()
   