import numpy as np

def decompose_transformation(transformation):
    """
    Udtrækker translation og rotation fra en 4x4 transformationsmatrix.

    Args:
        transformation (np.ndarray): 4x4 transformationsmatrix.

    Returns:
        dict: En dictionary med 'translation' (x, y, z) og 'rotation' (roll, pitch, yaw i grader).
    """
<<<<<<< HEAD

=======
>>>>>>> bd86d10 (Ændret navn på Point Cloud Processing til)
    # Kontroller input
    if transformation.shape != (4, 4):
        raise ValueError("Transformationsmatrixen skal være 4x4.")

    # Udtræk translation (de sidste tre elementer i den fjerde kolonne)
    translation = transformation[:3, 3]

    # Udtræk rotationsdelen (de første tre rækker og kolonner)
    rotation_matrix = transformation[:3, :3]

    # Beregn Euler-vinkler fra rotationsmatrixen (roll, pitch, yaw)
    sy = np.sqrt(rotation_matrix[0, 0]**2 + rotation_matrix[1, 0]**2)

    singular = sy < 1e-6  # Tjek for singularitet

    if not singular:
        roll = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
        pitch = np.arctan2(-rotation_matrix[2, 0], sy)
        yaw = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
    else:
        roll = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
        pitch = np.arctan2(-rotation_matrix[2, 0], sy)
        yaw = 0

    # Konverter rotation fra radianer til grader
    roll = np.degrees(roll)
    pitch = np.degrees(pitch)
    yaw = np.degrees(yaw)

    return {
        "translation": tuple(translation),
        "rotation": (roll, pitch, yaw),
    }
