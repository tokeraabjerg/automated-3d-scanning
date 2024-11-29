from CompleteComparison import complete_comparison
from Translatory_crutch import align_centroids

stl_file = r"C:\Users\ovikd\Documents\Punktskyer\DesignUdenTap.STL"
scanned_pc_path1 = r"C:\Users\ovikd\Documents\Punktskyer\ScannedMerged.ply"  # Replace with your scanned point cloud path


complete_comparison(stl_file,scanned_pc_path1)