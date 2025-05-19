import cv2
import os
import argparse
import subprocess  # Added for FFmpeg
import tempfile  # Added for temporary file name

def resize_and_reencode_video(input_path, temp_silent_video_path, target_width, target_height, target_fps):
    """
    Reads an input video, resizes its frames, changes its FPS, converts to black and white,
    and saves it as a new silent MKV video file using FFV1 codec.

    Args:
        input_path (str): Path to the input video file.
        temp_silent_video_path (str): Path to save the temporary silent processed MKV video file.
        target_width (int): The target width for the output video frames.
        target_height (int): The target height for the output video frames.
        target_fps (float): The target frames per second for the output video.
    Returns:
        bool: True if successful, False otherwise.
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Error: Could not open input video file {input_path}")
        return False

    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    original_fps = cap.get(cv2.CAP_PROP_FPS)

    if original_fps == 0:
        print("Error: Original FPS is 0. Cannot determine frame interval. Please check the input video.")
        cap.release()
        return False
        
    print(f"Input video: {input_path}")
    print(f"  Original dimensions: {original_width}x{original_height} @ {original_fps:.2f} FPS")
    print(f"Processing video to temporary MKV: {temp_silent_video_path}")
    print(f"  Target dimensions: {target_width}x{target_height} @ {target_fps:.2f} FPS (MKV/FFV1, silent, B&W)")

    # Use FFV1 codec for lossless intermediate MKV file
    fourcc = cv2.VideoWriter_fourcc(*'F','F','V','1')
    out = cv2.VideoWriter(temp_silent_video_path, fourcc, float(target_fps), (target_width, target_height))

    if not out.isOpened():
        print(f"Error: Could not open temporary video file {temp_silent_video_path} for writing.")
        cap.release()
        return False

    frames_processed_input = 0
    frames_written_output = 0
    frame_skip_interval = original_fps / target_fps
    next_frame_to_process = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames_processed_input += 1
        if frames_processed_input >= next_frame_to_process:
            resized_frame = cv2.resize(frame, (target_width, target_height))
            gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
            _ , binary_frame_gray = cv2.threshold(gray_frame, 127, 255, cv2.THRESH_BINARY)
            binary_frame_bgr = cv2.cvtColor(binary_frame_gray, cv2.COLOR_GRAY2BGR)
            out.write(binary_frame_bgr)
            frames_written_output += 1
            next_frame_to_process += frame_skip_interval

    cap.release()
    out.release()

    if frames_written_output > 0:
        print(f"Successfully processed {frames_processed_input} input frames and wrote {frames_written_output} output frames to {temp_silent_video_path}.")
        return True
    else:
        print(f"No frames were processed for {temp_silent_video_path}. Please check the input video.")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resizes video, converts to B&W (intermediate MKV/FFV1), changes FPS, adds original audio, and saves, typically as MKV. Requires FFmpeg.")
    parser.add_argument("input_path", help="Path to the input MP4 video file (with audio).")
    parser.add_argument("output_path", help="Path to save the final output video file (e.g., output.mkv, to preserve lossless FFV1 video).")
    parser.add_argument("--width", type=int, default=15, help="Target width for the video (default: 15).")
    parser.add_argument("--height", type=int, default=11, help="Target height for the video (default: 11).")
    parser.add_argument("--fps", type=float, default=15.0, help="Target FPS for the video (default: 15.0).")

    args = parser.parse_args()

    if not os.path.isfile(args.input_path):
        print(f"Error: Input video file not found at '{args.input_path}'.")
    else:
        # Generate a temporary filename for the silent video, ensure .mkv suffix
        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp_file:
            temp_silent_video_path = tmp_file.name
        
        print(f"Temporary silent MKV video will be generated at: {temp_silent_video_path}")

        video_processed_successfully = resize_and_reencode_video(
            args.input_path, temp_silent_video_path, 
            args.width, args.height, args.fps
        )

        if video_processed_successfully:
            print(f"Attempting to merge audio from '{args.input_path}' into '{temp_silent_video_path}' to create '{args.output_path}'.")
            
            # Video codec will always be 'copy' to preserve the FFV1 stream from the temp file.
            video_codec = 'copy'
            print(f"FFmpeg will use '{video_codec}' for the video stream, preserving the intermediate FFV1 codec.")

            ffmpeg_command = [
                'ffmpeg',
                '-y',  # Overwrite output file if it exists
                '-i', temp_silent_video_path,    # Input silent video (MKV/FFV1)
                '-i', args.input_path,           # Input original video (for audio)
                '-c:v', video_codec,             # Always copy the video stream
                '-c:a', 'aac',                  # Encode audio to AAC
                '-map', '0:v:0',                 # Map video from first input
                '-map', '1:a:0',                 # Map audio from second input
                args.output_path
            ]
            try:
                subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
                print(f"Successfully merged audio. Final video saved to: {args.output_path}")
            except subprocess.CalledProcessError as e:
                print(f"Error during FFmpeg audio merge:")
                print(f"Command: {' '.join(e.cmd)}")
                print(f"Return code: {e.returncode}")
                print(f"Stderr: {e.stderr}")
                print(f"Stdout: {e.stdout}")
                print(f"Please ensure FFmpeg is installed and in your system PATH.")
                print(f"The silent processed video is available at: {temp_silent_video_path}")
            except FileNotFoundError:
                print("Error: FFmpeg command not found. Please ensure FFmpeg is installed and in your system PATH.")
                print(f"The silent processed video is available at: {temp_silent_video_path}")
            else:
                 # Clean up temporary silent video file only if FFmpeg was successful
                try:
                    os.remove(temp_silent_video_path)
                    print(f"Temporary silent video file '{temp_silent_video_path}' deleted.")
                except OSError as e:
                    print(f"Error deleting temporary file '{temp_silent_video_path}': {e}")
        else:
            print("Video processing failed. Audio merging step skipped.")
            # Ensure temp file is cleaned up if it exists and video processing failed early
            if os.path.exists(temp_silent_video_path):
                try:
                    os.remove(temp_silent_video_path)
                except OSError as e:
                    print(f"Error deleting temporary file '{temp_silent_video_path}': {e}")
