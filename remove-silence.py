import subprocess
import sys

def remove_silence(input_file, output_file=None):
    """
    Removes silent parts from a video using auto-editor.

    :param input_file: Path to the input video file (mp4).
    :param output_file: Path to the output video file (mp4). If None, appends '_ALTERED' to the input file name.
    """
    if output_file is None:
        output_file = input_file.rsplit('.', 1)[0] + '_ALTERED.mp4'

    command = [
        'auto-editor', input_file,
        '--edit', 'audio:threshold=0.04,stream=all',  # Cuts out sections where the audio volume is below 4% in all streams
        '--margin', '0.2sec',  # Adds 0.2 seconds of padding around "loud" sections
        '--output', output_file
    ]

    subprocess.run(command, check=True)
    print(f"Processed video saved as {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_silence.py <input_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    remove_silence(input_file, output_file)
