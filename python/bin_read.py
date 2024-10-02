#===========================================================================
#  ?                                ABOUT
#  @author         :  Toke Raabjerg
#  @email          :  tokermc@hotmail.com
#  @repo           :  automation-3d-scanning
#  @createdOn      :  01/10-24
#  @description    :  Reading 3D scan data stored in binary files. 
#                     The data order is column-major, therefore the
#                     data is transposed
#===========================================================================
import numpy as np

def read(bin_path, transpose=True):
    # Read the entire binary file at once
    point_data = np.fromfile(bin_path, dtype='<f8')  # Little-endian 64-bit float

    # Determine the number of data points (assuming 4 columns: X, Y, Z, I)
    n_points = int(point_data.shape[0]/4)

    if(transpose==True):
        # Reshape the data into 4 columns (X, Y, Z, I)
        return point_data.reshape(4, n_points).T  # Transpose to get (num_points, 4)
    elif(transpose==False):
        # Reshape the data into 4 columns (X, Y, Z, I)
        return point_data.reshape(4, n_points)  # Do not transpose