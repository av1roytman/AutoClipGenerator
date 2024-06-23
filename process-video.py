import subprocess
import sys
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import os

def remove_silence(input_file, output_file=None):
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

def download_video(youtube_url, output_path):
    yt = YouTube(youtube_url)

    video_stream = yt.streams.filter(progressive=False, file_extension='mp4').filter(lambda s: s.resolution <= '1080p').order_by('resolution').desc().first()
    audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()

    video_filename = video_stream.default_filename
    audio_filename = "audio_" + video_filename

    video_path = os.path.join(output_path, video_filename)
    audio_path = os.path.join(output_path, audio_filename)

    video_stream.download(filename=video_filename, output_path=output_path)
    audio_stream.download(filename=audio_filename, output_path=output_path)

    # Combine video and audio
    output_file = os.path.join(output_path, "final_" + video_filename)
    command = [
        'ffmpeg', '-i', video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', output_file
    ]
    subprocess.run(command, check=True)

    # Clean up and delete the uncombined files
    os.remove(video_path)
    os.remove(audio_path)

    return output_file

def get_transcript(video_url):
    video_id = YouTube(video_url).video_id
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return transcript

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_silence.py <YouTube URL> [output_file]")
        sys.exit(1)

    youtube_url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Download the video from the url
    raw_video = download_video(youtube_url, 'Raw')

    # Get the Transcript
    transcript_file = get_transcript(youtube_url)


    # remove_silence(input_file, output_file)