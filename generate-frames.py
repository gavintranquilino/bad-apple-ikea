import cv2
import os
import argparse

def video_to_resized_frames(video_path, output_folder, target_width=15, target_height=11, target_fps=None):
    """
    Reads a video, resizes its frames, and saves them to the output folder at a specific FPS.

    Args:
        video_path (str): Path to the input video file.
        output_folder (str): Folder to save the resized frames.
        target_width (int): The target width for the resized frames (x-dimension).
        target_height (int): The target height for the resized frames (y-dimension).
        target_fps (int, optional): The target frames per second. If None, all frames are processed.
    """
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")

    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Original video FPS: {original_fps}")

    if target_fps and target_fps > original_fps:
        print(f"Warning: Target FPS ({target_fps}) is higher than original video FPS ({original_fps}). Output will be at original FPS.")
        target_fps = original_fps
    
    if target_fps and target_fps <= 0:
        print(f"Warning: Target FPS ({target_fps}) must be a positive number. Processing all frames instead.")
        target_fps = None

    frame_number = 0
    saved_frame_count = 0
    frame_interval = 1  # Default to saving every frame

    if target_fps is not None and original_fps > 0:
        frame_interval = original_fps / target_fps
        print(f"Saving one frame every {frame_interval:.2f} original frames to achieve approx. {target_fps} FPS.")

    next_frame_to_save = 0.0

    while True:
        # Read a frame
        ret, frame = cap.read()

        # If frame is not read correctly (e.g., end of video), break the loop
        if not ret:
            break

        if target_fps is None or frame_number >= next_frame_to_save:
            # Resize the frame
            resized_frame = cv2.resize(frame, (target_width, target_height))

            # Convert to grayscale
            gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)

            # Apply binary thresholding
            # Pixels below 127 will become black (0), and above will become white (255)
            _, binary_frame = cv2.threshold(gray_frame, 127, 255, cv2.THRESH_BINARY)

            # Save the binarized frame
            frame_filename = os.path.join(output_folder, f"frame_{saved_frame_count:05d}.png")
            cv2.imwrite(frame_filename, binary_frame)
            saved_frame_count += 1
            if target_fps is not None:
                next_frame_to_save += frame_interval

        frame_number += 1

    # Release the video capture object
    cap.release()
    print(f"Finished processing. {saved_frame_count} frames were extracted, resized and saved.")
    print(f"Resized frames are saved in the '{output_folder}' directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resizes video frames and saves them.")
    parser.add_argument("path", help="Path to the input video file.")
    parser.add_argument("output_dir", help="Folder to save the resized frames.")
    parser.add_argument("--width", type=int, default=15, help="Target width for resized frames (default: 15).")
    parser.add_argument("--height", type=int, default=11, help="Target height for resized frames (default: 11).")
    parser.add_argument("--fps", type=int, default=None, help="Target FPS for the output frames (default: process all frames).")

    args = parser.parse_args()

    input_video_file = args.path
    output_frames_dir = args.output_dir
    desired_width = args.width
    desired_height = args.height
    desired_fps = args.fps

    if not os.path.isfile(input_video_file):
        print(f"Error: Input video file not found at '{input_video_file}'.")
        print("Please make sure the video file path is correct.")
    else:
        video_to_resized_frames(input_video_file, output_frames_dir, 
                                target_width=desired_width, target_height=desired_height, target_fps=desired_fps)