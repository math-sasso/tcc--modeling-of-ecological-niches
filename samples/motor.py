from samples.ambient import country
from 
import os

#'/content/drive/My Drive/TFC_MatheusSasso/Coolabs/Data/Shapefiles_Brasil'

#gbif = GbifRequester()






if __name__ == "__main__":

    ROOT_DIR = os.path.normpath(os.getcwd() + os.sep + os.pardir)
    COUNTRY_SHAPEFILES_FOLDER = '\docs\Shapefiles\Brasil'
    brasil_folder = ROOT_DIR + COUNTRY_SHAPEFILES_FOLDER
    brasil = country(brasil_folder)


