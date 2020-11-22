import os
import numpy as np

class Utils:
    def __init__(self):
        pass
        
    def retrieve_data_from_np_array(path):
        """ Read a numpy array"""
        with open(path, 'rb') as f:
            np_array = np.load(f)
        return np_array

    def create_folder_structure(folder):
        """ Create the comple folder structure if it does not exists """
        if not os.path.exists(folder):
            os.makedirs(folder)

    def save_nparray_to_folder(np_array,folder_path,filename):
        """ Save numpy array to the specified folder path """
        complete_path = os.path.join(folder_path,filename+'.npy')
        with open(complete_path, 'wb') as f:
            print(f"{filename} Shape: ",np_array.shape)
            np.save(f, np_array)
            
