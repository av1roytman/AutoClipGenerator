import subprocess
import sys
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from moviepy.video.io.VideoFileClip import VideoFileClip

load_dotenv()


def main():
    if len(sys.argv) < 2:
        print("Usage: python remove_silence.py <YouTube URL> [output_file]")
        sys.exit(1)

    youtube_url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Download the video from the url
    raw_video = download_video(youtube_url, 'Raw')

    # Get the Transcript
    transcript = get_transcript(youtube_url)
    transcript_text_list = [entry['text'] for entry in transcript]
    transcript_text = ' '.join(transcript_text_list)

    # Get the interesting parts of the video
    interesting_parts = get_interesting_parts(transcript_text)

    # Extract timestamps for the most interesting parts
    timestamps = extract_timestamps(interesting_parts, transcript)

    print(timestamps)

    # Crop the video to the interesting parts
    crop_video(raw_video, timestamps, 'Cropped')


def crop_video(input_file, timestamps, output_path):
    # Load the video
    video = VideoFileClip(input_file)

    # Extract filename from input_file
    filename = os.path.basename(input_file)

    # For each timestamp, create a new clip from 60 seconds before to 60 seconds after the timestamp
    for i, timestamp in enumerate(timestamps[:10]):  # Limit to the first 10 timestamps
        start = max(0, timestamp - 60)  # Ensure start is not negative
        end = timestamp + 60
        clip = video.subclip(start, end)

        # Write the clip to a file
        clip.write_videofile(f"{output_path}/{filename}_{i}.mp4")

        clip.close()

    video.close()


def extract_timestamps(interesting_parts, transcript):
    timestamps = []
    for entry in transcript:
        for sentence in interesting_parts:
            if entry['text'] in sentence:
                timestamps.append(entry['start'])
                interesting_parts.remove(sentence)

    return timestamps


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

    video_stream = yt.streams.filter(progressive=False, file_extension='mp4').order_by('resolution').desc().first()
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


def get_interesting_parts(transcript):
    # Concatenate transcript entries into a single text
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    # Use OpenAI API to summarize and extract key points
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You are a helpful assistant that finds the most interesting parts of a video transcript"},
            {"role": "user", "content": "The following is the transcript of the video as a list of transcript entires. Identify the 10 most interesting sentences in the transcript. \
                                        You should return a json object with the key 'interesting_parts' and a list of only the 10 most interesting sentences. Here is the transcript: " + str(transcript)}
        ]
    )

    # Print token summary of usgae
    print("Usage:")
    print(response.usage)

    summary = json.loads(response.choices[0].message.content)

    # Parse the JSON and get the list of entries
    interesting_parts = summary['interesting_parts']

    return interesting_parts


if __name__ == "__main__":
    main()
