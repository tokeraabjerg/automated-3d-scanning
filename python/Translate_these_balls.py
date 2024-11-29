import json
import os

def steps_to_degrees(steps):
    """
    Convert steps to degrees.
    1 degree of rotation equals 19.5 steps.
    """
    return steps / 19.5

def translate_positions():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    positions_path = os.path.join(script_dir, 'positions.json')
    
    with open(positions_path, 'r') as file:
        positions = json.load(file)
    
    if not positions:
        print("No positions found in positions.json")
        return
    
    initial_pos_a = positions[0]['pos_a']
    initial_pos_b = positions[0]['pos_b']
    
    for entry in positions:
        pos_a = entry['pos_a']
        pos_b = entry['pos_b']
        
        steps_a = pos_a - initial_pos_a
        steps_b = pos_b - initial_pos_b
        
        deg_a = steps_to_degrees(steps_a)
        deg_b = steps_to_degrees(steps_b)
        
        print(f"Relative Position A: {steps_a} steps, {deg_a:.2f} degrees")
        print(f"Relative Position B: {steps_b} steps, {deg_b:.2f} degrees")

if __name__ == "__main__":
    translate_positions()
