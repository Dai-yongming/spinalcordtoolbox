import nibabel as nib
import sys
import torch
import numpy as np

from PIL import Image

from spinalcordtoolbox.image import Image

import model as M


class Acquisition():
    
    def __init__(self, axial_slices):
        self.slices = axial_slices

    def loadFromPath(self, path):
        """
        This method loads the slices in the slices attribute from the path.
        At this point it is only a list of arrays and will only be converted
        to tensor after transformations.
        """
        nii_original = nib.load(path).get_data()
        if nii_original.size == 0 :
            raise RuntimeError(f"Empty slice in subject {path}.")
        axial_slices = []
        for i in range(nii_original.shape[2]):
            axial_slices.append(nii_original[:,:,i])
        self.slices = axial_slices

    def loadFromImage(self, image):
        self.slices = image.data

    def StandardizeTransform(self):
        """
        This method standardizes each slices individually
        """
        for i in range(len(self.slices)):
            mean, std = self.slices[i].mean(), self.slices[i].std() 
            self.slices[i] = (self.slices[i] - mean) / std
    
    def CenterCropTransform(self, size=128):
        """
        This method centers the image around the center
        """
        for i in range(len(self.slices)):
            y, x = self.slices[i].shape
            
            startx = x // 2 - (size // 2)
            starty = y // 2 - (size // 2)
            
            if startx < 0 or starty < 0:
                raise RuntimeError("Negative crop.")
            
            self.slices[i] = self.slices[i][starty:starty + size,
                                           startx:startx + size]
    
    def ToTensor(self):
        """
        This method returns the tensor in the correct shape to feed the network
        ie. torch.Size([16, 1, 128, 128]) with dtype = float
        """        
        slices = np.asarray(self.slices, dtype=np.float32)
        slices = np.expand_dims(slices, axis=1)
        tensor = torch.FloatTensor(slices)
        return(tensor)


def classify_acquisition(input_path, model=None):
       
    slices = Acquisition(input_path)
    slices.CenterCropTransform()
    slices.StandardizeTransform()
    input_slices = slices.ToTensor()

    """
    # We load the acquisitions from the image module in order to benefit from all existing methods
    slices = Image()
    slices.loadFromPath(input_path)
    slices.change_orientation('RPI')
    
    # Then we preprocess the slices
    acq = Acquisition()
    acq.loadFromImage(slices)
    acq.CenterCropTransform()
    acq.StandardizeTranform()
    
    input_slices = acq.ToTensor()
    """


    with torch.no_grad():
        
        input_slices = input_slices

        outputs = model(input_slices)   
        _, preds = torch.max(outputs, 1)
        preds = preds.tolist()
        
    numeral=[[preds.count(nb), nb] for nb in preds]
    numeral.sort(key=lambda x:x[0], reverse=True)
    modality = numeral[0][1]

    class_names = ["t1", "t2s", "t2"]
    return(class_names[modality])


def run_main():
    if len(sys.argv) <= 1:
        print("\nclassify_acquisition [path]\n")
        return
    
    input_path = sys.argv[1]
    
    model = M.Classifier()
    model.load_state_dict(torch.load("model.pt", map_location='cpu'))
    model.eval()
    
    modality = classify_acquisition(input_path, model)
    
    class_names = ["T1w", "T2star", "T2w"]   
    
    return(class_names[modality])