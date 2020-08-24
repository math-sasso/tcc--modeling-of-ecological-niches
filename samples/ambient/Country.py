import os
from osgeo import ogr
import geopandas as gpd

# Fazer Composição com continente no futuro
class Country:
  def __init__(self, shapefiles_folder:str):
    
    #Folder
    shapefile_brasi_pais_folder = shapefiles_folder + '/Pais'
    shapefile_brasi_estado_folder = shapefiles_folder + '/Estados'
    shapefile_brasi_municipio_folder = shapefiles_folder + '/Municipios'
    shapefile_brasi_distrito_folder = shapefiles_folder + '/Distritos'
    
    #Complete file path
    self._brasil_pais_path = os.path.join(shapefile_brasi_pais_folder, 'BRA_adm0.shp')
    self._brasil_estados_path = os.path.join(shapefile_brasi_estado_folder, 'BRA_adm1.shp')
    self._brasil_municipos_path = os.path.join(shapefile_brasi_municipio_folder, 'BRA_adm2.shp')
    self._brasil_distritos_path = os.path.join(shapefile_brasi_distrito_folder, 'BRA_adm3.shp')

    # GeoDataFrame
    self._brasil_pais = gpd.read_file(self._brasil_pais_path)
    self._brasil_estados = gpd.read_file(self._brasil_estados_path)
    self._brasil_municipos = gpd.read_file(self._brasil_municipos_path)
    self._brasil_distritos = gpd.read_file(self._brasil_distritos_path)
  
  def get_brasil_pais_gdf(self):
    return self._brasil_pais

  def get_brasil_estados_gdf(self):
    return self._brasil_estados

  def get_brasil_municipos_gdf(self):
    return self._brasil_municipos

  def get_brasil_distritos_gdf(self):
    return self._brasil_distritos

  def get_df_only_with_inside_country_points(self,df,name_index:str='NAME_ISO',country_index:str='COUNTRY',lat_index:str='LATITUDE',lon_index:str='LONGITUDE'):
    # open shapefile containing country polygons
    #filename = '/content/drive/My Drive/TFC_MatheusSasso/Coolabs/Data/Shapefiles_World/TM_WORLD_BORDERS-0.3.shp'
    filename = self._brasil_pais_path
    drv = ogr.GetDriverByName('ESRI Shapefile')                     # set up driver object to read/write shapefiles
    shapefile = drv.Open(filename) # open shapefile
    layer = shapefile.GetLayer(0)                                   # create layer object for shapefile
    # determine indices of relevant columns
    nameIndex = layer.GetLayerDefn().GetFieldIndex(name_index)       # index of column with country names in shapefile 
    countryIndex = df.columns.get_loc(country_index)       # index of country name column in observation table                                                            
    latIndex = df.columns.get_loc(lat_index)               # index of lat column in observation table
    lonIndex = df.columns.get_loc(lon_index)               # index of lon column in observation table

    # set up list in which we will store the results of looking up the containing country for each row
    geocodingResults = []  

    # itertuples is used to efficiently loop through the rows of the data frame
    for row in df.itertuples(index=False):  

        # create a new OGR point object with lon and lat coordinates from current row 
        pt = ogr.Geometry(ogr.wkbPoint)                    
        pt.SetPoint_2D(0, row[lonIndex], row[latIndex] )  

        # apply spatial filter that will give us polygons that intersect our point
        layer.SetSpatialFilter(pt)                         

        country = "UNKNOWN"           # variable for storing the country's name

        # check whether there's exactly one feature selected, if get country name of that feature
        if layer.GetFeatureCount() == 1:                   
            country = layer.GetNextFeature().GetFieldAsString(nameIndex).title()
        
        # add country name to result list
        geocodingResults.append(country)                   
    
    df['country_geocoding'] = geocodingResults  # add geocoding results as new column

    df = df [(df.country_geocoding == df.COUNTRY)|(df.country_geocoding == 'Brazil')]
    return df