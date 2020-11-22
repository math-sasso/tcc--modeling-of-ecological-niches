
import os
import numpy as np
import geopandas as gpd
from typing import List,Tuple,Dict
from sklearn import svm, metrics
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
# from raster_standards import Raster_Standards
# from utils import Utils
import rasterio
import matplotlib.pyplot as plt


class OneClassSVMModel:
  
  """
  This class is reponsable for performing fits and predictions for the species ditribution problem using OneClassSVM 
   Attributes
  ----------
  nu : float
      An upper bound on the fraction of training errors and a lower bound of the fraction of support vectors. Should be in the interval (0, 1]. By default 0.5 will be taken.
  kenel : str
      Specifies the kernel type to be used in the algorithm. It must be one of ‘linear’, ‘poly’, ‘rbf’, ‘sigmoid’, ‘precomputed’ or a callable. If none is given, ‘rbf’ will be used. If a callable is given it is used to precompute the kernel matrix.
  gamma : object
      Kernel coefficient for ‘rbf’, ‘poly’ and ‘sigmoid’.
      if gamma='scale' (default) is passed then it uses 1 / (n_features * X.var()) as value of gamma,
      if ‘auto’, uses 1 / n_features.
  seed : object
    Aleatory seed
  raster_standards : object
    Raster standards object
  utils_methods : object
    Utils object
  land_reference : array
    Array used as the land reference
  
  """
  def __init__(self,hyperparams:Dict,raster_standards, utils_methods,land_reference_path:str):
    """    
    Parameters
    ----------
    hyperparams : Dict
        Set of hyperparameters for the model(nu,kernel,gamma,seed)
    raster_standards : Object
        Raster standards object
    utils_methods : Object
        Utils object
    land_reference_path : str
        Path to a raster used as land refence
       
    """
  
    #-------------- hyperparams
    self.nu = hyperparams["nu"]
    self.kernel = hyperparams["kernel"]
    self.gamma = hyperparams["gamma"]
    self.seed = hyperparams["seed"]
    
    #-------------- 
    self.raster_standards = raster_standards
    self.utils_methods = utils_methods
    self.land_reference = self.raster_standards.get_land_reference_array_mask(land_reference_path)
    np.random.seed(self.seed)


  def fit(self,species_bunch,global_mean,global_std):
    """ Fitting data with normalized data """
    train_cover_std = (species_bunch['raster_data_train'] - global_mean) / global_std
    train_cover_std[np.isnan(train_cover_std)] = 0 #Nan values comes from std=0 in some variable
    clf = svm.OneClassSVM(nu=self.nu, kernel=self.kernel, gamma=self.gamma)
    clf.fit(train_cover_std)
    return clf
  
  def predict_land(self,stacked_raster_coverages,clf,global_mean,global_std):
    """ Predict adaptability for every valid point on the map """

    stacked_raster_coverages_shape = stacked_raster_coverages.shape
    print('Shape stacked_raster_coverages: ',stacked_raster_coverages_shape)

    # Extracting coverages land
    idx = np.where(self.land_reference == self.raster_standards.positive_mask_val) # Coordenadas X e Y em duas tuplas de onde a condição se satifaz (array(),array())
    
    #Performing Predictions
    raster_coverages_land = stacked_raster_coverages[:, idx[0],idx[1]].T
    for k in range(raster_coverages_land.shape[1]):
      raster_coverages_land[:,k][raster_coverages_land[:,k]<=self.raster_standards.no_data_val] = global_mean[k]
      
    scaled_coverages_land = (raster_coverages_land - global_mean) / global_std
    del raster_coverages_land
    scaled_coverages_land[np.isnan(scaled_coverages_land)] = 0
    global_pred = clf.decision_function(scaled_coverages_land)
    del scaled_coverages_land

    #Setting Spatial Predictions
    Z = np.ones((stacked_raster_coverages_shape[1], stacked_raster_coverages_shape[2]), dtype=np.float64)#cria um array de uns do tamanho das dimensões do brasil
    Z *= global_pred.min() #Miltiplica ele pelo mínimo das predições [valor muito baixo ou zero]
    Z[idx[0], idx[1]] = global_pred #atribui o valor de pred para lugares onde não são zero
    del global_pred


    #Setting no data values to -9999
    Z[self.land_reference == 0] = self.raster_standards.no_data_val

    return Z

  def predict_test_occurences(self,species_bunch,clf,global_mean,global_std):
    """ Fitting adaptability only for test set data """

    scaled_species_raster_test = (species_bunch['raster_data_test'] - global_mean) / global_std
    scaled_species_raster_test[np.isnan(scaled_species_raster_test)] = 0
    pred_test = clf.decision_function(scaled_species_raster_test)
    return pred_test

  def perform_K_folder_preidction(self,species_occurence_path:str,specie_shp_path:str,rasters_root_folders_list:List,output_base_folder:str,K:int=4):
    """ Perform K times the prediction pipeline """
    
    #1 Getting species name
    species_name = species_occurence_path.split("/")[-1].split(".")[0]

    #2 Recovering occurrences data
    species_gdf = gpd.read_file(specie_shp_path)
    coordinates = np.array((np.array(species_gdf['LATITUDE']),np.array(species_gdf['LONGITUDE']))).T 
    species_raster_data = self.utils_methods.retrieve_data_from_np_array(species_occurence_path)

    #3 Retrieving raster stacked coverages data
    print("---------------------- Reading and stacking rasters ----------------------")
    raster_coverages_list = []
    for rasters_root_folder in rasters_root_folders_list:
        raster_coverages = self.raster_standards.get_rasters_from_dir(rasters_root_folder)
        raster_coverages_list.append(raster_coverages)
        raster_coverages = None
    stacked_raster_coverages = np.concatenate([x for x in raster_coverages_list], axis=0)
    del raster_coverages_list
    print("Stack finished")
    
    #4 Reshaping data
    stacked_raster_coverages_copy = np.copy(stacked_raster_coverages)#(38,4923, 4942)
    stacked_raster_coverages_copy = np.transpose(stacked_raster_coverages_copy,(1,2,0)) #(4923, 4942,38)
    stacked_raster_coverages_copy = np.reshape(stacked_raster_coverages_copy,(-1,stacked_raster_coverages_copy.shape[2]))#(24329466,38)

    #5 Taking Means and Stds
    global_mean = np.zeros(shape=(0))
    for i in range(stacked_raster_coverages_copy.shape[1]):
      mean = np.mean(stacked_raster_coverages_copy[:,i][stacked_raster_coverages_copy[:,i]>self.raster_standards.no_data_val])
      global_mean = np.append(global_mean, mean)
    global_mean = np.float32(global_mean)
    
    global_std = np.zeros(shape=(0))
    for i in range(stacked_raster_coverages_copy.shape[1]):
      std = np.std(stacked_raster_coverages_copy[:,i][stacked_raster_coverages_copy[:,i]> self.raster_standards.no_data_val])
      global_std = np.append(global_std, std)
    global_std = np.float32(global_std)
    
    del stacked_raster_coverages_copy
  
    #6 reating kfolds object
    kf = KFold(n_splits=K,random_state=self.seed, shuffle=True)
    
    #7 Executing Pipeline
    for i, (train_index, test_index) in enumerate(kf.split(species_raster_data)):
      print(f"------------------------------ KFold {i+1} ------------------------------")
      #creating Kfold Folder Structure
      kfold_path = os.path.join(output_base_folder,species_name,f"KFold{i+1}")
      self.utils_methods.create_folder_structure(kfold_path)


      species_raster_data_train, species_raster_data_test = species_raster_data[train_index], species_raster_data[test_index]
      coords_train, coords_test = coordinates[train_index], coordinates[test_index]
      species_bunch = {'species_name':species_name,
                       'raster_data_train':species_raster_data_train,
                       'raster_data_test':species_raster_data_test,
                       'coords_train':coords_train,
                       'coords_test':coords_test}
      
      clf = self.fit(species_bunch,global_mean,global_std)

      #predicting values only for test points
      pred_test = self.predict_test_occurences(species_bunch,clf,global_mean,global_std)

      #predicting land values
      Z = self.predict_land(stacked_raster_coverages,clf,global_mean,global_std)


      #save Z
      self.utils_methods.save_nparray_to_folder(Z,kfold_path,"Land_Prediction")
      del Z
      #save pred_test
      self.utils_methods.save_nparray_to_folder(pred_test,kfold_path,"Test_Prediction")
      del pred_test
      #save coords_train
      self.utils_methods.save_nparray_to_folder(species_bunch['coords_train'],kfold_path,"Coords_Train")
      #save_coords_test
      self.utils_methods.save_nparray_to_folder(species_bunch['coords_test'],kfold_path,"Coords_Test")
      #raster_data_train
      self.utils_methods.save_nparray_to_folder(species_bunch['raster_data_train'],kfold_path,"Species_Raster_Data_Train")
      #raster_data_test
      self.utils_methods.save_nparray_to_folder(species_bunch['raster_data_test'],kfold_path,"Species_Raster_Data_Test")
      del  species_bunch