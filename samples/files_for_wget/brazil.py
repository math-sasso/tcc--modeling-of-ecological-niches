import os
from osgeo import ogr
from shapely import wkt
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from typing import Tuple


class Brazil:
  """
  This class models a country on the shapefile format on different detail levels
  
  
  Attributes
  ----------
  x_min_limit : float
      Country most western point
  x_max_limit : float
      Country most eastern point
  y_min_limit : float
      Country most south point
  y_max_limit : float
      Country most north point
  _brazil_country_level_gpd : GeoDataframe
      Geopandas dataframe for brazilian territory as country
  _brazil_state_level_gpd : GeoDataframe
      Geopandas dataframe for brazilian territory as states
  _brazil_city_level_gpd : GeoDataframe
      Geopandas dataframe for brazilian territory as cities
  _brazil_district_level_gpd : GeoDataframe
      Geopandas dataframe for brazilian territory as districts
  _brazil_country_level_path : str
      Path to brazilian territory as country
  _brazil_state_level_path : str
      Path to brazilian territory as states
  _brazil_city_level_path : str
      Path to brazilian territory as cities
  _brazil_district_level_path : str
      Path to brazilian territory as districts

  
  """


  def __init__(self, shapefiles_folder:str,country_limits:Tuple):
    """
    Parameters
    ----------
    shapefiles_folder : str
        Folder cointaing shapefiles from some country
    country_limitsr : Tuple
        Tuple with the country 4 limits (N,S,L,W)
    """

    #Country_Limits
    self.x_min_limit = country_limits[0]  # Coordenadas DMS: 07°32′39″S 073°59′04″W; Coordenada Decimal Geohack: -7.544167, -73.984444; Corrdenada Decimal epsg.io: -7.535403, -73.981934
    self.x_max_limit = country_limits[1]  # Coordenadas DMS: 07°09′28″S 034°47′38″W; Coordenada Decimal Geohack: -20.474444, -28.840556; Corrdenada Decimal epsg.io: -7.155017, -34.792929
    self.y_min_limit = country_limits[2]  # Coordenadas DMS: 33°45′09″S 053°22′07″W; Coordenada Decimal Geohack: -33.7525, -53.368611; Corrdenada Decimal epsg.io: -33.750035, -53.407288
    self.y_max_limit = country_limits[3]  # Coordenadas DMS: 05°15′05″N 060°12′33″W; Coordenada Decimal Geohack: 5.251389, -60.209167; Corrdenada Decimal epsg.io: 5.271478, -60.214691
      
    #Folder
    brazil_country_level_folder = shapefiles_folder + '/Pais'
    brazil_state_level_folder = shapefiles_folder + '/Estados'
    brazil_city_level_folder = shapefiles_folder + '/Municipios'
    brazil_district_level_folder = shapefiles_folder + '/Distritos'
    
    #Complete file path
    self._brazil_country_level_path = os.path.join(brazil_country_level_folder, 'BRA_adm0.shp')
    self._brazil_state_level_path = os.path.join(brazil_state_level_folder, 'BRA_adm1.shp')
    self._brazil_city_level_path = os.path.join(brazil_city_level_folder, 'BRA_adm2.shp')
    self._brazil_district_level_path = os.path.join(brazil_district_level_folder, 'BRA_adm3.shp')

    # GeoDataFrame
    self._brazil_country_level_gpd = gpd.read_file(self._brazil_country_level_path)
    self._brazil_state_level_gpd = gpd.read_file(self._brazil_state_level_path)
    self._brazil_city_level_gpd = gpd.read_file(self._brazil_city_level_path)
    self._brazil_district_level_gpd = gpd.read_file(self._brazil_district_level_path)


  def get_country_level_gdf(self):
    """Construct geopandas dataframe for brazilian territory as country"""
    return self._brazil_country_level_gpd

  def get_state_level_gdf(self):
    """Construct geopandas dataframe for brazilian territory as states"""
    return self._brazil_state_level_gpd

  def get_city_level_gdf(self):
    """Construct geopandas dataframe for brazilian territory as cities"""
    return self._brazil_city_level_gpd

  def get_district_level_gdf(self):
    """Construct geopandas dataframe for brazilian territory as disrticts"""
    return self._brazil_district_level_gpd

  def get_df_only_with_inside_country_points(self,df,name_index:str='NAME_ISO',country_index:str='COUNTRY',lat_index:str='LATITUDE',lon_index:str='LONGITUDE'):
    """
    Returns a filtered df without the missmarked occurrences, checking if they realy are inside the country

    Parameters
    ----------
    df : Dataframe
        Dataframe with gbif occurenced not checked
    name_index : str
        Column with name information 
    country_index : str
        Column with country information  
    lat_index : str
        Column with latitude information
    lon_index : str
        Column with longitude information
    """

    # 1 --> Open shapefile containing country polygons
    filename = self._brazil_country_level_path
    drv = ogr.GetDriverByName('ESRI Shapefile')                # set up driver object to read/write shapefiles        
    shapefile = drv.Open(filename)                             # open shapefile 
    layer = shapefile.GetLayer(0)                              # create layer object for shapefile                               
    
    #2 --> Determine indices of relevant columns
    nameIndex = layer.GetLayerDefn().GetFieldIndex(name_index) # index of column with country names in shapefile 
    countryIndex = df.columns.get_loc(country_index)           # index of country name column in observation table                                                            
    latIndex = df.columns.get_loc(lat_index)                   # index of lat column in observation table
    lonIndex = df.columns.get_loc(lon_index)                   # index of lon column in observation table

    #3 --> Countries Check.
    geocodingResults = []  #Set up list in which we will store the results of looking up the containing country for each row

    # itertuples is used to efficiently loop through the rows of the data frame
    for row in df.itertuples(index=False):  

        # create a new OGR point object with lon and lat coordinates from current row 
        pt = ogr.Geometry(ogr.wkbPoint)                    
        pt.SetPoint_2D(0, row[lonIndex], row[latIndex] )  

        # apply spatial filter that will give us polygons that intersect our point
        layer.SetSpatialFilter(pt)                         

        country = "UNKNOWN"# variable for storing the country's name

        # check whether there's exactly one feature selected, if get country name of that feature
        if layer.GetFeatureCount() == 1:                   
            country = layer.GetNextFeature().GetFieldAsString(nameIndex).title()
        
        # add country name to result list
        geocodingResults.append(country)                   
    
    df['country_geocoding'] = geocodingResults  # add geocoding results as new column
    df = df [(df.country_geocoding == df.COUNTRY)|(df.country_geocoding == 'Brazil')]


    #4 --> Limits Check.
    df = df[df['LONGITUDE']>=self.x_min_limit]
    df = df[df['LONGITUDE']<=self.x_max_limit]
    df = df[df['LATITUDE']>=self.y_min_limit]
    df = df[df['LATITUDE']<=self.y_max_limit]
    return df


  def plot_points_on_country(self,
                              species_name:str,
                              map_result_path:str,
                              species_presences_path:str,
                              species_absences_path:str=None):
                              
    fig, ax = plt.subplots(figsize=(10, 10))

    self._brazil_country_level_gpd.plot(ax=ax, facecolor='gray')



    if ".csv" in species_presences_path:
      df_species_presences = pd.read_csv(species_presences_path)
      gdf_species_presences = gpd.GeoDataFrame(df_species_presences, geometry=gpd.points_from_xy(df_species_presences.LONGITUDE, df_species_presences.LATITUDE),crs='epsg:4326')
      # df_species_presences['geometry'] = df_species_presences['geometry'].apply(wkt.loads)
      # gdf_species_presences = gpd.GeoDataFrame(df_species_presences, crs='epsg:4326')
    elif ".shp" in species_presences_path:
      gdf_species_presences = gpd.read_file(species_presences_path)
    gdf_species_presences.plot(ax=ax, color='blue', markersize=5,label="presences")
    
    if species_absences_path:
      if ".csv" in species_absences_path:
        df_species_absences = pd.read_csv(species_absences_path)
        gdf_species_absences = gpd.GeoDataFrame(df_species_absences, geometry=gpd.points_from_xy(df_species_absences.LONGITUDE, df_species_absences.LATITUDE),crs='epsg:4326')
      elif ".shp" in species_absences_path:
        gdf_species_absences = gpd.read_file(species_absences_path)
      gdf_species_absences.plot(ax=ax, color='red', markersize=5,label="absences")
      plt.title(f'Ocorrências e Abeências da espécie \n {species_name} no Brasil',fontsize=20)
    else:
      plt.title(f'Ocorrências da espécie  \n {species_name} no Brasil',fontsize=20)
    
    plt.ylabel('Latitude [graus]',fontsize=16)
    plt.xlabel('Longitude [graus]',fontsize=16)
    plt.tight_layout()
    plt.savefig(map_result_path)
