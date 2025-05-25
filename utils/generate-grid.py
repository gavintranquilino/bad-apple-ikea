import time
import json
from pynput import mouse

# Global variable to store the last clicked position
clicked_pos = None

def on_click(x, y, button, pressed):
    """Callback function for mouse clicks."""
    global clicked_pos
    if pressed:
        clicked_pos = (int(x), int(y))
        # Stop listener
        return False

def get_click_position(prompt_message):
    """Displays a prompt and waits for a mouse click, then returns the position."""
    global clicked_pos
    clicked_pos = None
    print(f"\n{prompt_message}")
    print("Please click the designated spot on your screen.")
    
    # Using a new listener for each click
    # The listener will run in this thread and block until it's stopped (by returning False from on_click)
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()
    
    if clicked_pos:
        print(f"Captured: {clicked_pos}")
    else:
        print("No position captured. Please try again if needed.")
    time.sleep(0.5) # Brief pause for user
    return clicked_pos

def main():
    """Main function to guide through coordinate capture and save to JSON."""
    num_rows = 11
    num_cols = 15

    column_x_values = [None] * num_cols
    row_y_values = [None] * num_rows
    grid_cells_coords = {}

    print("Starting screen coordinate capture for an 11x15 grid.")
    print("You will be asked to click specific points. Ensure the target window is active and visible.")
    print("The grid is indexed (row, col), with (0,0) at the top-left.")
    time.sleep(2)

    # 1. Capture Bottom Row (for X-coordinates of all columns and Y of the bottom row)
    print("\n--- Step 1: Capturing Bottom Row ---")
    print(f"You will click {num_cols} cells from left to right in the BOTTOM row (row {num_rows - 1}).")
    bottom_row_index = num_rows - 1
    for c in range(num_cols):
        prompt = f"Click on cell ({bottom_row_index}, {c}) (Column {c+1} of {num_cols} in the bottom row)."
        pos = get_click_position(prompt)
        if pos is None:
            print("Failed to capture position. Aborting.")
            return
        column_x_values[c] = pos[0]
        if c == 0: # First click in bottom row (bottom-left cell of the grid)
            row_y_values[bottom_row_index] = pos[1]
    
    # Check if Y for bottom row was set (it should be by the first click)
    if row_y_values[bottom_row_index] is None and column_x_values[0] is not None:
        # This case should ideally not happen if the first click (bottom_row_index, 0) was successful.
        # As a fallback, if we have its position, use its Y.
        # However, the logic above should set it. This is more of a sanity check.
        print(f"Re-evaluating Y for bottom row based on click for ({bottom_row_index}, 0)")
        # Re-prompt if necessary, or use a stored full coordinate for (bottom_row_index, 0)
        # For now, we assume the first click correctly set row_y_values[bottom_row_index]

    print("\nBottom row X-coordinates captured.")
    print(f"X-values: {column_x_values}")
    print(f"Y-value for row {bottom_row_index} (bottom row): {row_y_values[bottom_row_index]}")


    # 2. Capture Leftmost Column (for Y-coordinates of all rows and X of the leftmost column)
    print("\n--- Step 2: Capturing Leftmost Column ---")
    print(f"You will click {num_rows} cells from top to bottom in the LEFTMOST column (column 0).")
    leftmost_col_index = 0
    for r in range(num_rows):
        prompt = f"Click on cell ({r}, {leftmost_col_index}) (Row {r+1} of {num_rows} in the leftmost column)."
        pos = get_click_position(prompt)
        if pos is None:
            print("Failed to capture position. Aborting.")
            return
        row_y_values[r] = pos[1]
        if r == bottom_row_index: # This is the (bottom_row_index, 0) cell, clicked again
            # Check consistency of X-coordinate for (bottom_row_index, 0)
            if column_x_values[leftmost_col_index] is not None and \
               abs(column_x_values[leftmost_col_index] - pos[0]) > 5: # 5 pixels tolerance
                print(f"Warning: X-coordinate for ({r},{leftmost_col_index}) from leftmost column click ({pos[0]}) "
                      f"differs from bottom row click ({column_x_values[leftmost_col_index]}). "
                      f"Using X-value from bottom row click: {column_x_values[leftmost_col_index]}.")
            elif column_x_values[leftmost_col_index] is None:
                 column_x_values[leftmost_col_index] = pos[0] # Set if not set by bottom row (should have been)


    print("\nLeftmost column Y-coordinates captured.")
    print(f"Y-values: {row_y_values}")
    if column_x_values[leftmost_col_index] is not None:
        print(f"X-value for column {leftmost_col_index} (leftmost column): {column_x_values[leftmost_col_index]}")

    # 3. Calculate all grid cell coordinates
    print("\n--- Step 3: Calculating all grid cell coordinates ---")
    for r in range(num_rows):
        for c in range(num_cols):
            if row_y_values[r] is None or column_x_values[c] is None:
                print(f"Error: Missing coordinate data for cell ({r},{c}). Cannot calculate all grid cells.")
                print(f"Row Ys: {row_y_values}")
                print(f"Col Xs: {column_x_values}")
                return
            grid_cells_coords[f"({r},{c})"] = (column_x_values[c], row_y_values[r])
    print("All grid cell coordinates calculated.")

    # 4. Select Set Black and Set White buttons
    print("\n--- Step 4: Capturing Button Coordinates ---")
    set_black_button_pos = get_click_position("Click the 'Set Black' button.")
    if set_black_button_pos is None:
        print("Failed to capture 'Set Black' button position. Aborting.")
        return

    set_white_button_pos = get_click_position("Click the 'Set White' button.")
    if set_white_button_pos is None:
        print("Failed to capture 'Set White' button position. Aborting.")
        return
    
    print("\nButton coordinates captured.")

    # 5. Save to JSON
    output_data = {
        "grid_dimensions": {"rows": num_rows, "cols": num_cols},
        "grid_cells": grid_cells_coords,
        "set_black_button": set_black_button_pos,
        "set_white_button": set_white_button_pos
    }

    json_file_path = "coordinates.json"
    try:
        with open(json_file_path, 'w') as f:
            json.dump(output_data, f, indent=4)
        print(f"\nAll coordinates successfully saved to {json_file_path}")
    except IOError as e:
        print(f"Error saving coordinates to {json_file_path}: {e}")

if __name__ == "__main__":
    main()