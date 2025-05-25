import time
import json
import os
from pynput import mouse, keyboard # Added keyboard
from PIL import Image # For image processing
import mss # For screenshots

# Global variable to store the last clicked position or signal to start
click_event_occurred = False

def on_initial_click(x, y, button, pressed):
    """Callback function for the initial mouse click to start the script."""
    global click_event_occurred
    if pressed and button == mouse.Button.left:
        print(f"Initial click detected at ({x}, {y}). Starting script...")
        click_event_occurred = True
        # Stop listener
        return False

def wait_for_initial_click():
    """Waits for a single left mouse click before proceeding."""
    global click_event_occurred
    click_event_occurred = False
    print("Waiting for a left mouse click to start the process...")
    
    with mouse.Listener(on_click=on_initial_click) as listener:
        listener.join()
    
    if not click_event_occurred:
        print("No click detected. Exiting.")
        exit()
    time.sleep(0.5) # Brief pause

def set_cell_color(mouse_controller, cell_target_coords, color_button_coords, color_name):
    """
    Moves to a cell, clicks it, waits, then clicks the specified color button.
    """
    mouse_controller.position = cell_target_coords
    mouse_controller.click(mouse.Button.left, 1)
    time.sleep(3) # As per original requirement
    mouse_controller.position = color_button_coords
    mouse_controller.click(mouse.Button.left, 1)
    time.sleep(2) # As per original requirement

def get_pixel_grid_from_image(image_path, num_rows, num_cols):
    """
    Loads a binarized image and converts it into a 2D grid of 0s (black) and 1s (white).
    Assumes input images are already 11x15 and binarized.
    """
    try:
        img = Image.open(image_path).convert('L') # Convert to grayscale
        
        if img.width != num_cols or img.height != num_rows:
            print(f"Warning: Image {os.path.basename(image_path)} dimensions ({img.width}x{img.height}) "
                  f"do not match target ({num_cols}x{num_rows}). Attempting to use as is.")

        pixel_grid = [[1 for _ in range(num_cols)] for _ in range(num_rows)]
        for r in range(num_rows):
            for c in range(num_cols):
                pixel_value = img.getpixel((c, r))
                if pixel_value >= 128:
                    pixel_grid[r][c] = 1 # White
                else:
                    pixel_grid[r][c] = 0 # Black
        return pixel_grid
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

def main():
    coords_file = "./coordinates.json"
    reference_frames_dir = "./reference-frames"
    output_frames_dir = "./frames"
    # state_file = "current_grid_state.json" # Not currently used for saving state between runs

    os.makedirs(output_frames_dir, exist_ok=True)

    try:
        with open(coords_file, 'r') as f:
            coords_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {coords_file} not found. Please run the coordinate capture script first.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode {coords_file}. Ensure it's a valid JSON.")
        return

    grid_cells = coords_data.get("grid_cells", {})
    set_white_button_pos = coords_data.get("set_white_button")
    set_black_button_pos = coords_data.get("set_black_button")
    grid_dims = coords_data.get("grid_dimensions", {"rows": 0, "cols": 0})
    num_rows = grid_dims["rows"]
    num_cols = grid_dims["cols"]

    if not all([grid_cells, set_white_button_pos, set_black_button_pos, num_rows > 0, num_cols > 0]):
        print(f"Error: Coordinate data is incomplete in {coords_file}. "
              "Ensure grid_cells, set_white_button, set_black_button, and dimensions are present.")
        return

    mouse_ctrl = mouse.Controller()
    keyboard_ctrl = keyboard.Controller() # Added keyboard controller

    current_screen_grid_state = [[0 for _ in range(num_cols)] for _ in range(num_rows)]
    print(f"Initialized internal grid state to all black ({num_rows}x{num_cols}).")

    try:
        all_reference_files = sorted([
            f for f in os.listdir(reference_frames_dir) 
            if f.lower().endswith(".png") and os.path.isfile(os.path.join(reference_frames_dir, f))
        ])
        if not all_reference_files:
            print(f"No .png files found in {reference_frames_dir}. Exiting.")
            return
    except FileNotFoundError:
        print(f"Error: Reference frames directory '{reference_frames_dir}' not found.")
        return
        
    processed_frames_in_output = []
    if os.path.exists(output_frames_dir):
        processed_frames_in_output = sorted([
            f for f in os.listdir(output_frames_dir)
            if f.lower().endswith(".png") and os.path.isfile(os.path.join(output_frames_dir, f))
        ])

    last_processed_frame_filename = None
    if processed_frames_in_output:
        last_processed_frame_filename = processed_frames_in_output[-1]
        print(f"Last processed frame found in '{output_frames_dir}': {last_processed_frame_filename}")

    start_processing_index = 0
    if last_processed_frame_filename:
        try:
            start_processing_index = all_reference_files.index(last_processed_frame_filename) + 1
            if start_processing_index < len(all_reference_files):
                 print(f"Resuming. Will start processing from frame: {all_reference_files[start_processing_index]}")
            else:
                print("All frames appear to be processed based on output folder. Exiting.")
                return # Exit if all frames are processed
        except ValueError:
            print(f"Warning: Last processed frame '{last_processed_frame_filename}' not found in reference frames. Starting from the beginning.")
            start_processing_index = 0
    
    frames_to_process = all_reference_files[start_processing_index:]

    if not frames_to_process:
        print("No new frames to process. All reference frames seem to have corresponding output.")
        return
        
    print(f"Found {len(frames_to_process)} reference frames to process (out of {len(all_reference_files)} total).")

    wait_for_initial_click()

    search_bar_coords = (951, 60) # Define search bar coordinates

    with mss.mss() as sct:
        for frame_index_overall, frame_filename in enumerate(frames_to_process):
            true_frame_number_idx = start_processing_index + frame_index_overall 
            print(f"\n--- Processing frame {true_frame_number_idx + 1}/{len(all_reference_files)} (File: {frame_filename}) ---")
            image_path = os.path.join(reference_frames_dir, frame_filename)
            
            target_grid_state = get_pixel_grid_from_image(image_path, num_rows, num_cols)
            if target_grid_state is None:
                print(f"Skipping frame {frame_filename} due to image processing error.")
                continue

            changes_made_for_this_frame = 0
            for r in range(num_rows):
                for c in range(num_cols):
                    target_color_val = target_grid_state[r][c]
                    current_color_val = current_screen_grid_state[r][c]
                    
                    if target_color_val != current_color_val:
                        changes_made_for_this_frame +=1
                        cell_key = f"({r},{c})"
                        if cell_key not in grid_cells:
                            print(f"Warning: Coordinates for cell {cell_key} not found. Skipping cell.")
                            continue
                        
                        cell_coords = tuple(grid_cells[cell_key])
                        
                        color_to_set_str = "white" if target_color_val == 1 else "black"
                        button_coords = tuple(set_white_button_pos) if target_color_val == 1 else tuple(set_black_button_pos)
                        
                        set_cell_color(mouse_ctrl, cell_coords, button_coords, color_to_set_str)
                        current_screen_grid_state[r][c] = target_color_val

            if changes_made_for_this_frame == 0:
                print(f"No changes needed for frame {frame_filename} based on current state.")

            print("Waiting 5 seconds...")
            time.sleep(5) 
            
            # Click search bar and type frame number
            print(f"Clicking search bar at {search_bar_coords} and typing frame number.")
            mouse_ctrl.position = search_bar_coords
            mouse_ctrl.click(mouse.Button.left, 1)
            time.sleep(0.5) # Short pause for focus

            # Extract frame number from filename (e.g., "frame_00123.png" -> "00123")
            try:
                frame_num_str = frame_filename.split('_')[1].split('.')[0]
                keyboard_ctrl.type(frame_num_str)
                print(f"Typed: {frame_num_str}")
            except IndexError:
                print(f"Could not extract frame number from filename: {frame_filename}")
            
            time.sleep(0.5) # Short pause after typing

            # Click additional coordinates
            additional_click_coords = (62, 518)
            print(f"Clicking at {additional_click_coords}")
            mouse_ctrl.position = additional_click_coords
            mouse_ctrl.click(mouse.Button.left, 1)
            time.sleep(0.5) # Short pause after click

            screenshot_filename = os.path.join(output_frames_dir, frame_filename)
            try:
                sct.shot(output=screenshot_filename)
                print(f"Screenshot saved to {screenshot_filename}")
            except Exception as e:
                print(f"Error taking or saving screenshot for {frame_filename}: {e}")

    print("\nAll frames processed.")

if __name__ == "__main__":
    main()