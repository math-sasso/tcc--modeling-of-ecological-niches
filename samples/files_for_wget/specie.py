import requests
import pandas as pd
import os
import geopandas as gpd
import numpy as np

class Specie:

  """
  This class reprepsents a specie that is retrieved from GBIF

   Attributes
  ----------
  _taxonKey : int
      GBIF code for requesting species data
  _species_name : string
      Species cientific name
  _limit : int
      Limit of rows by request
  _hasCoordinate : boolean
      Boolean for getting only data with Lat and Long
  _lowYear : int
      Low year limit for the query 
  _upYear : int
      UP year limit for the query
  _year_range : int
      Geopandas dataframe for brazilian territory as cities
  _dropDuplicates : boolean
      True for dropping duplicate occurrences
  _tryOverrideSpecieData : boolean
      True for always retrieve the shapefile, false to used an existing one
  _base_url : string
       GBIF base URL
  _out_shapefile_parent_folder : string
      Path with shapefiles saving location

  """
  def __init__(self,
               taxonKey:int,
               species_name:str,
               countryObj:object=None,
               limit:int =300,
               hasCoordinate: bool=True,
               lowYear:int=None,
               upYear:int=None,
               dropDuplicates:bool=True,
               tryOverrideSpecieData:bool=False,
               base_url:str = "http://api.gbif.org/v1/occurrence/search",
               out_shapefile_parent_folder:str = "/content/drive/My Drive/TFC_MatheusSasso/Data/GBIF_Ocurrences"):
    
    """    
    Parameters
    ----------
    taxonKey : int
        GBIF taxonkey identifier
    species_name : str
        Species Name
    countryObj : object
        Object with country shapefiles
    limit : int
        Limit of occurences in one request 
    hasCoordinate : bool
        True for only get occurences with coordinates
    lowYear : int
        Low Year occurrence limit
    upYear : int
        Up Year occurrence limit
    dropDuplicates : bool
        True for dropping duplicate occurrences
    tryOverrideSpecieData : bool
        True for always retrieve the shapefile, false to used an existing one
    base_url : str
        GBIF base URL
    out_shapefile_parent_folder : str
        Path with shapefiles saving location
        
    """
    
    #-------Country Object
    self._countryObj = countryObj

    #--------Parameters
    self._taxonKey = taxonKey
    self._species_name = species_name
    self._limit = limit
    self._hasCoordinate = hasCoordinate
    self._lowYear = lowYear
    self._upYear = upYear
    self._year_range = str(lowYear) + ',' +str(upYear)
    self._dropDuplicates = dropDuplicates
    self._tryOverrideSpecieData = tryOverrideSpecieData
    self._base_url = base_url
    self._out_shapefile_parent_folder = out_shapefile_parent_folder

    #--------Data Retrieval
    if (not self._tryOverrideSpecieData) and (self._data_reader()):
      print("In this case GBIF request was not necessary, we got gdf from Shapefile")
      self._df = None
      self._gdf = self._data_reader()
    else:
      print("In this case GBIF request was necessary to create gdf file")
      df_dirty = self._managing_complete_species_dataframe()
      self._df = self._get_inside_country_dataframe(df_dirty)
      self._gdf = self._create_specie_geo_dataframe()
      print('Effectively ' + str(len(self._gdf)) + ' examplars are inside country boarders')
      self._shp_exporter()
      

  #-------- Private Methods 
  def _managing_complete_species_dataframe(self):
    """ Organizes GBIF information in a dataframe considering offsets and some basic data cleaning"""

    df = pd.DataFrame(columns=['SCIENTIFIC_NAME','LONGITUDE','LATITUDE','COUNTRY','STATE_PROVINCE','IDENTIFICATION_DATE','DAY','MONTH','YEAR'])
    endOfRecords = False  
    offset = 0  
    status = 200
    params = {'taxonKey': str(self._taxonKey) ,'limit':self._limit,'hasCoordinate':self._hasCoordinate,'year':self._year_range,'country':'BR'} 
    while endOfRecords == False and status == 200:  
        r, endOfRecords, status = self._gbif_request_json_request(offset, params)
        df = self._create_specie_dataframe(df,r)
        offset = len(df) + 1
    
    # Double check to certify there is no empty lat/long data
    df = df[pd.notnull(df['LATITUDE'])]
    df = df[pd.notnull(df['LONGITUDE'])]

    # Removing duplicate data
    df = df.drop_duplicates(ignore_index=True) if self._dropDuplicates else df

    # Sorting Data by STATE_PROVINCE
    df.sort_values("STATE_PROVINCE", inplace = True,ignore_index=True)
    return df

  def _gbif_request_json_request(self,offset,params):
    """ Request GBIF information """

    query = self._base_url
    params['offset'] = offset
    r = requests.get(query,params=params)
    status_code =  r.status_code
    if r.status_code != 200:  
        print(f"API call failed at offset {offset} with a status code of {r.status_code}.") 
        endOfRecords = True
    else:  
        r = r.json() 
        endOfRecords = r['endOfRecords']

    return r,endOfRecords,status_code


  def _data_reader(self):
    """ Try to read an existing shapefile """

    species_folder = self.out_shapefile_folder
    specie_id_file = str(self.taxonKey) + '.shp'
    fp = os.path.join(species_folder, specie_id_file)
    try:
     gdf = gpd.read_file(fp) 
    except FileNotFoundError:
     gdf = None
    return gdf      
  
  def _shp_exporter(self):
    """ Save gepandas as shapefile """

    species_folder =os.path.join(self._out_shapefile_parent_folder,  self._species_name)
    if not os.path.exists(species_folder):
      os.mkdir(species_folder)
  
    #saving shapefile data inside the created folder
    self._gdf.to_file(species_folder)
  
  def _refact_dict(self, result):
    """ Refact dict placing None in empty cells """

    columns = result.keys()
    desired_columns = ['scientificName','decimalLongitude','decimalLatitude','country','stateProvince','eventDate','day','month','year','occurrenceRemarks']
    for d_col in desired_columns:
      if d_col not in columns:
        result[d_col] = None
    return result

  def _create_specie_dataframe(self,df_final,request):
    """ Create species dataframe with the request data """

    for result in request['results']:
      result = self._refact_dict(result)
      df_final = df_final.append({
          "SCIENTIFIC_NAME": result['scientificName'],
          "LONGITUDE": result['decimalLongitude'],
          "LATITUDE":  result['decimalLatitude'],
          "COUNTRY":  result['country'],
          "STATE_PROVINCE":  result['stateProvince'],
          "IDENTIFICATION_DATE":  result['eventDate'],
          "DAY":  result['day'],
          "MONTH":  result['month'],
          "YEAR":  result['year']}, ignore_index=True)
    return df_final

  def _get_inside_country_dataframe(self,df):
    """Use country(brazil) object to double check if points truly are in Brazil"""

    if self._countryObj:
      insde_country_df = self._countryObj.get_df_only_with_inside_country_points(df,
                                                                                 name_index='NAME_ISO',
                                                                                 country_index='COUNTRY',
                                                                                 lat_index='LATITUDE',
                                                                                 lon_index='LONGITUDE')
    else:
      insde_country_df = df
    return insde_country_df

  def _create_specie_geo_dataframe(self):
    """ Create species geodataframe from dataframe + Longitude and Latitude"""
    gdf = gpd.GeoDataFrame(self._df, geometry=gpd.points_from_xy(self._df.LONGITUDE,self._df.LATITUDE))
    return gdf
    
  #-------- Public Methods
  def get_specie_df(self):
    """ Get species as DataFrame """
    return self._df
  
  def get_specie_gdf(self):
    """ Get species as vGeoDataFrame """
    return self._gdf