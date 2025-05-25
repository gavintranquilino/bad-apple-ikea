import cv2
import os
import argparse
import subprocess
import tempfile

def create_video_from_frames(frames_dir, temp_video_path, fps):
    """
    Creates a silent MP4 video from a directory of PNG frames.

    Args:
        frames_dir (str): Path to the directory containing PNG frames.
        temp_video_path (str): Path to save the temporary silent MP4 video.
        fps (float): Frames per second for the output video.

    Returns:
        bool: True if successful, False otherwise.
        tuple: (width, height) of the video if successful, None otherwise.
    """
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.lower().endswith(".png")])
    if not frame_files:
        print(f"No PNG frames found in {frames_dir}")
        return False, None

    # Read the first frame to get dimensions
    try:
        first_frame_path = os.path.join(frames_dir, frame_files[0])
        frame = cv2.imread(first_frame_path)
        if frame is None:
            print(f"Error reading first frame: {first_frame_path}")
            return False, None
        height, width, layers = frame.shape
    except Exception as e:
        print(f"Error getting frame dimensions: {e}")
        return False, None

    print(f"Creating temporary video from {len(frame_files)} frames at {width}x{height}, {fps} FPS.")

    # Use MP4V codec for MP4 format
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    out = cv2.VideoWriter(temp_video_path, fourcc, float(fps), (width, height))

    if not out.isOpened():
        print(f"Error: Could not open temporary video file {temp_video_path} for writing.")
        return False, None

    for i, frame_file in enumerate(frame_files):
        frame_path = os.path.join(frames_dir, frame_file)
        img = cv2.imread(frame_path)
        if img is None:
            print(f"Warning: Could not read frame {frame_path}. Skipping.")
            continue
        out.write(img)
        if (i + 1) % 100 == 0:
            print(f"Processed {i+1}/{len(frame_files)} frames for temporary video.")
            
    out.release()
    print(f"Temporary silent video saved to {temp_video_path}")
    return True, (width, height)

def add_audio_to_video(silent_video_path, audio_source_path, output_video_path):
    """
    Adds audio from an audio source to a silent video using FFmpeg.
    The output duration will be determined by the shorter of the video or audio.

    Args:
        silent_video_path (str): Path to the silent video file.
        audio_source_path (str): Path to the video/audio file to extract audio from.
        output_video_path (str): Path to save the final video with audio.

    Returns:
        bool: True if successful, False otherwise.
    """
    if not os.path.isfile(audio_source_path):
        print(f"Error: Audio source file not found at '{audio_source_path}'. Cannot add audio.")
        print(f"The silent video is available at: {silent_video_path}")
        # Copy silent video to output path if audio source is missing
        try:
            import shutil
            shutil.copy(silent_video_path, output_video_path)
            print(f"Copied silent video to {output_video_path} as audio source was not found.")
            return True # Or False, depending on desired behavior for missing audio
        except Exception as e:
            print(f"Error copying silent video to output: {e}")
            return False

    print(f"Attempting to merge audio from '{audio_source_path}' into '{silent_video_path}' to create '{output_video_path}'.")
    
    ffmpeg_command = [
        'ffmpeg',
        '-y',  # Overwrite output file if it exists
        '-i', silent_video_path,    # Input silent video
        '-i', audio_source_path,    # Input original video (for audio)
        '-c:v', 'copy',             # Copy the video stream
        '-c:a', 'aac',              # Encode audio to AAC
        '-map', '0:v:0',            # Map video from first input
        '-map', '1:a:0?',           # Map audio from second input (if it exists)
        '-shortest',                # Finish encoding when the shortest input stream ends
        output_video_path
    ]
    try:
        result = subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        print(f"Successfully merged audio. Final video saved to: {output_video_path}")
        if result.stderr:
            print(f"FFmpeg stderr (warnings/info):\n{result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during FFmpeg audio merge:")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Return code: {e.returncode}")
        print(f"Stderr: {e.stderr}")
        print(f"Stdout: {e.stdout}")
        print(f"Please ensure FFmpeg is installed and in your system PATH.")
        print(f"The silent processed video is available at: {silent_video_path}")
        return False
    except FileNotFoundError:
        print("Error: FFmpeg command not found. Please ensure FFmpeg is installed and in your system PATH.")
        print(f"The silent processed video is available at: {silent_video_path}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Creates a preview video from frames and adds audio. Requires FFmpeg for audio.")
    parser.add_argument("output_path", help="Path to save the final output MP4 video file (e.g., ../preview.mp4).")
    parser.add_argument("--frames_dir", default="../frames/", help="Directory containing the PNG frames (default: ../frames/).")
    parser.add_argument("--audio_source", default="./bad-apple-raw.mp4", help="Path to the source MP4 video for audio (default: ./bad-apple-raw.mp4, relative to script location).")
    parser.add_argument("--fps", type=float, default=15.0, help="Target FPS for the video (default: 15.0).")

    args = parser.parse_args()

    # Ensure output path is .mp4
    if not args.output_path.lower().endswith(".mp4"):
        args.output_path += ".mp4"
        print(f"Output path adjusted to: {args.output_path}")

    # Resolve paths relative to the script's directory if they are relative
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(args.frames_dir):
        args.frames_dir = os.path.join(script_dir, args.frames_dir)
    if not os.path.isabs(args.audio_source):
        args.audio_source = os.path.join(script_dir, args.audio_source)
    if not os.path.isabs(args.output_path):
        args.output_path = os.path.join(script_dir, args.output_path)
        # If output path was relative, it might now be inside utils. Let's put it one level up.
        args.output_path = os.path.join(os.path.dirname(script_dir), os.path.basename(args.output_path))


    # Generate a temporary filename for the silent video
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
        temp_silent_video_path = tmp_file.name
    
    print(f"Temporary silent MP4 video will be generated at: {temp_silent_video_path}")

    video_created, dims = create_video_from_frames(args.frames_dir, temp_silent_video_path, args.fps)

    if video_created:
        audio_added = add_audio_to_video(temp_silent_video_path, args.audio_source, args.output_path)
        if audio_added:
            print("Preview video generation successful.")
        else:
            print("Preview video generation failed at audio merging stage.")
    else:
        print("Preview video generation failed at video creation stage.")

    # Clean up temporary silent video file
    if os.path.exists(temp_silent_video_path):
        try:
            os.remove(temp_silent_video_path)
            print(f"Temporary silent video file '{temp_silent_video_path}' deleted.")
        except OSError as e:
            print(f"Error deleting temporary file '{temp_silent_video_path}': {e}")

