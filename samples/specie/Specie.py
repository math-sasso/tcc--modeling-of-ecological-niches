import requests
import pandas as pd
import os
import geopandas as gpd

#Alguns outros parâmtreos interessantes que podem ser considerados 
#elevation: Elevation (altitude) in meters above sea level. Supports range queries.
#establishmentMeans: EstablishmentMeans, as defined in our EstablishmentMeans enum
#repatriated: Searches for records whose publishing country is different to the country where the record was recorded in.

class Specie:
  def __init__(self,
               taxonKey:int,
               countryObj:object=None,
               limit:int =300,
               hasCoordinate: bool=True,
               lowYear=None,
               upYear=None,
               dropDuplicates:bool=True,
               tryOverrideSpecieData:bool=False):
    

    #-------Country Object
    self._countryObj = countryObj

    #--------Parameters
    self._taxonKey = taxonKey
    self._limit = limit
    self._hasCoordinate = hasCoordinate
    self._lowYear = lowYear
    self._upYear = upYear
    assert (lowYear and upYear),"You must provide lowYear and upYear" 
    self._year_range = str(lowYear) + ',' +str(upYear)
    self._dropDuplicates = dropDuplicates
    self._tryOverrideSpecieData = tryOverrideSpecieData

    #--------Data Retrieval
    if (not self._tryOverrideSpecieData) and (self._data_reader()):
      print("In this case GBIF request was not necessary, we got gdf from Shapefile")
      self._r = None
      self._df = None
      self._gdf = self._data_reader()
    else:
      print("In this case GBIF request was necessary to create gdf file")
      self._r = self._gbif_request_json_request()
      df_dirty = self._create_specie_dataframe()
      self._df = self._get_inside_country_dataframe(df_dirty)
      self._gdf = self._create_specie_geo_dataframe()
      print('Effectively ' + str(len(self._gdf)) + ' examplars are inside country boarders')
      self._shp_exporter()
      

  #-------- Private Methods 
  
  def _gbif_request_json_request(self):
    payload = {'taxonKey': str(self._taxonKey) ,'limit':self._limit,'hasCoordinate':self._hasCoordinate,'year':self._year_range,'country':'BR'} 
    r = requests.get("http://api.gbif.org/v1/occurrence/search", params=payload)
    r = r.json()
    print(str(r['count']) + ' occurrences were found. The limit of occurrences per request is ' + str(self._limit))
    return r


  def _data_reader(self):
    ROOT_DIR = os.path.normpath(os.getcwd() + os.sep + os.pardir+ os.sep + os.pardir)
    SPECIES_SHAPEFILES_FOLDER = '\docs\Species_Collected_Databases'
    species_folder = ROOT_DIR + SPECIES_SHAPEFILES_FOLDER
    specie_id_file = str(self.taxonKey) + '.shp'
    fp = os.path.join(species_folder, specie_id_file)
    try:
     gdf = gpd.read_file(fp) 
    except FileNotFoundError:
     gdf = None
    return gdf      
  
  def _shp_exporter(self):
    ROOT_DIR = os.path.normpath(os.getcwd() + os.sep + os.pardir+ os.sep + os.pardir)
    SPECIES_SHAPEFILES_FOLDER = '\docs\Species_Collected_Databases'
    species_folder = ROOT_DIR + SPECIES_SHAPEFILES_FOLDER
    specie_id_file = str(self._taxonKey) + '.shp'
    output_fp = os.path.join(species_folder, specie_id_file)
    self._gdf.to_file(output_fp)
  
  def _refact_dict(self, result):
    columns = result.keys()
    desired_columns = ['scientificName','decimalLongitude','decimalLatitude','country','stateProvince','eventDate','day','month','year','occurrenceRemarks']
    for d_col in desired_columns:
      if d_col not in columns:
        result[d_col] = None
    return result

  def _create_specie_dataframe(self):
    df = pd.DataFrame(columns=['SCIENTIFIC_NAME','LONGITUDE','LATITUDE','COUNTRY','STATE_PROVINCE','IDENTIFICATION_DATE','DAY','MONTH','YEAR','OCCURENCE_REMARKS'])
    for result in self._r['results']:
      result = self._refact_dict(result)
      df = df.append({
          "SCIENTIFIC_NAME": result['scientificName'],
          "LONGITUDE": result['decimalLongitude'],
          "LATITUDE":  result['decimalLatitude'],
          "COUNTRY":  result['country'],
          "STATE_PROVINCE":  result['stateProvince'],
          "IDENTIFICATION_DATE":  result['eventDate'],
          "DAY":  result['day'],
          "MONTH":  result['month'],
          "YEAR":  result['year'],
          "OCCURENCE_REMARKS":  result['occurrenceRemarks']
          }, ignore_index=True)
      df = df.drop_duplicates(ignore_index=True) if self._dropDuplicates else df
      df.sort_values("STATE_PROVINCE", inplace = True,ignore_index=True)
    return df

  def _get_inside_country_dataframe(self,df):
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
    gdf = gpd.GeoDataFrame(self._df, geometry=gpd.points_from_xy(self._df.LONGITUDE, self._df.LATITUDE))
    
    return gdf
    
  #-------- Public Methods
  def get_specie_df(self):
    return self._df
  
  def get_specie_gdf(self):
    return self._gdf