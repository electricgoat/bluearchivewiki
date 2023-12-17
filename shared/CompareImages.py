import os
import numpy as np
from PIL import Image

def identical_images(image1, image2):
    try:
        # Check if the shape of the images is the same
        if image1.shape != image2.shape:
            #print(f"Images have different dimensions.")
            return False

        # Compare pixel values
        if np.array_equal(image1, image2):
            #print(f"Images have IDENTICAL pixels.")
            return True
        else:
            #print(f"Images have different pixels.")
            pass
    except Exception as e:
        print(f"Error: {e}")
    
    return False



def compare_images(files, dir):
    data = []
    duplicate_list = []

    for file in files:
        data.append(np.array(Image.open(os.path.join(dir,file))))

    for index,file in enumerate(files):
        for i in range(index+1,len(files)):
            if identical_images(data[index], data[i]): duplicate_list.append(files[i])

    return duplicate_list
