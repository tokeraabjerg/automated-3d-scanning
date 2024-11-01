#===========================================================================
#  ?                                ABOUT
#  @author         :  Toke Raabjerg
#  @email          :  tokermc@hotmail.com
#  @repo           :  automation-3d-scanning
#  @createdOn      :  01/10-24
#  @description    :  Point cloud data .bin input/output
#                     Reading and writing 3D scan data stored in binary files.
#                     The data order is column-major, therefore the
#                     data is transposed when reading and writing.
#===========================================================================
import numpy as np

def read(bin_path, transpose=True):
    """
    Read point cloud data from a binary file.

    Parameters:
    - bin_path: Path to the binary file to read.
    - transpose: Whether to transpose the data after reading.
                 Should be True if the data is stored in column-major order.

    Returns:
    - NumPy array containing the point cloud data.
    """
    # Read the entire binary file at once
    point_data = np.fromfile(bin_path, dtype='<f8')  # Little-endian 64-bit float

    # Determine the number of data points (assuming 4 columns: X, Y, Z, I)
    n_points = int(point_data.shape[0] / 4)

    if transpose:
        # Reshape the data into 4 columns and transpose to get (num_points, 4)
        return point_data.reshape(4, n_points).T  # Shape: (n_points, 4)
    else:
        # Reshape the data into 4 columns without transposing
        return point_data.reshape(n_points, 4)    # Shape: (n_points, 4)


def save(bin_path, data, transpose=True):
    """
    Save point cloud data to a binary file in the same format and structure as the input.

    Parameters:
    - bin_path: Path to the binary file to save.
    - data: NumPy array containing the point cloud data.
    - transpose: Whether to transpose the data before writing.
                 Should match the transpose parameter used in read().
    """
    if transpose:
        # Data is (n_points, 4). Transpose back to (4, n_points).
        data_to_save = data.T  # Shape: (4, n_points)
    else:
        # Data is already in shape (n_points, 4)
        data_to_save = data  # Shape: (n_points, 4)

    # Flatten the data and write to file
    data_to_save.astype('<f8').tofile(bin_path)  # Little-endian 64-bit float

