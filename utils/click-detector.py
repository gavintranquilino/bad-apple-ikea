from pynput import mouse

def on_click(x, y, button, pressed):
    """Callback function for mouse clicks."""
    if pressed and button == mouse.Button.left:
        print(f"Left click detected at: ({int(x)}, {int(y)})")
        # Stop listener after the first left click
        return False

print("Waiting for a left mouse click...")

# Collect events until the listener returns False
with mouse.Listener(on_click=on_click) as listener:
    listener.join()

print("Listener stopped.")