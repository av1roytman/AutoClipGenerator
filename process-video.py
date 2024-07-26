from math import ceil
import subprocess
import sys
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
import numpy as np
import pickle
import mimetypes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main():
    if len(sys.argv) < 2:
        print("Usage: python remove_silence.py <YouTube URL> [output_file]")
        sys.exit(1)

    youtube_url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Download the video from the url
    print("Downloading video...")
    raw_video = download_video(youtube_url, "Raw")

    # Get the Transcript
    print("Getting transcript...")
    transcript = get_transcript(youtube_url)
    # print("Transcript:", transcript)

    # Convert the transcript to a list of words with timestamps
    print("Converting transcript...")
    converted_transcript = convert_transcript(transcript)
    # print("Converted transcript:", converted_transcript)

    transcript_text = " ".join([entry["text"] for entry in transcript])

    # Check video duration
    video = VideoFileClip(raw_video)

    # Get the interesting parts of the video
    print("Getting interesting parts...")
    split_coefficient = 2400
    if video.duration > split_coefficient:
        split = ceil(video.duration / split_coefficient)
    else:
        split = 1

    interesting_parts = get_interesting_parts(transcript_text, split)
    print(interesting_parts)

    # Extract timestamps for the most interesting parts
    print("Extracting timestamps...")
    timestamps = extract_timestamps(interesting_parts, converted_transcript)

    print(timestamps)

    # Crop the video to the interesting parts
    print("Cropping video...")
    crop_video(raw_video, timestamps, "Cropped")

    print("Uploading videos to Google Drive...")
    upload_videos_to_drive()

    print("Cleaning up...")
    clear_folder("Cropped")

    print("Processing completed.")


def convert_transcript(transcript):
    new_transcript = []

    for entry in transcript:
        text = entry["text"]
        start = entry["start"]
        duration = entry["duration"]

        words = text.split()
        num_words = len(words)
        if num_words == 0:
            continue

        word_duration = duration / num_words

        for i, word in enumerate(words):
            word_entry = {
                "text": word,
                "timestamp": round(start + i * word_duration, 3),
            }
            new_transcript.append(word_entry)

    return new_transcript


def clear_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        os.remove(file_path)


def upload_videos_to_drive():
    drive_service = authenticate_drive_api()
    folder_path = "Cropped"
    folder_id = os.getenv("DRIVE_FOLDER_ID")

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.endswith(
            ("mp4", "avi", "mov", "mkv")
        ):
            file_metadata = {"name": filename, "parents": [folder_id]}
            mime_type, _ = mimetypes.guess_type(file_path)
            media = MediaFileUpload(file_path, mimetype=mime_type)

            file = (
                drive_service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            print(f'File ID: {file.get("id")} uploaded successfully!')


def authenticate_drive_api():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("drive", "v3", credentials=creds)


def crop_video(input_file, timestamps, output_path):
    # Load the video
    video = VideoFileClip(input_file)

    # Extract filename from input_file
    filename = os.path.basename(input_file)
    filename = filename.rsplit(".", 1)[0]

    # For each timestamp, create a new clip from 60 seconds before to 60 seconds after the timestamp
    for i, timestamp in enumerate(timestamps):  # Limit to the first 10 timestamps
        start = max(0, timestamp - 5)  # Ensure start is not negative
        end = min(
            video.duration, timestamp + 60
        )  # Set end to the minimum of video duration or timestamp + 60
        if end - start >= 1:
            clip = video.subclip(start, end)

            # Write the clip to a file
            try:
                clip.write_videofile(
                    f"{output_path}/{filename}_{i}.mp4", codec="h264_nvenc"
                )
            except AttributeError as e:
                print(f"An error occurred: {e}")
                if "stdout" in str(e):
                    print(
                        "It seems there is an issue with the audio processing in FFmpeg."
                    )

            clip.close()

    video.close()


def extract_timestamps(interesting_parts, transcript):
    timestamps = []
    for i in range(len(transcript) - 5):
        # Concat the next 5 words
        text = " ".join([transcript[i + j]["text"] for j in range(5)])
        # print("text: ", text)

        for sentence in interesting_parts:
            if text in sentence:
                print("sentence: ", sentence)
                print("text: ", text)
                if transcript[i]["timestamp"] not in timestamps:
                    timestamps.append(transcript[i]["timestamp"])
                interesting_parts.remove(sentence)

    return timestamps


def remove_silence(input_file, output_file=None):
    if output_file is None:
        output_file = input_file.rsplit(".", 1)[0] + "_ALTERED.mp4"

    command = [
        "auto-editor",
        input_file,
        "--edit",
        "audio:threshold=0.04,stream=all",  # Cuts out sections where the audio volume is below 4% in all streams
        "--margin",
        "0.2sec",  # Adds 0.2 seconds of padding around "loud" sections
        "--output",
        output_file,
    ]

    subprocess.run(command, check=True)
    print(f"Processed video saved as {output_file}")


def download_video(youtube_url, output_path):
    yt = YouTube(youtube_url)

    print("Title:", yt.title)

    video_stream = (
        yt.streams.filter(progressive=False, file_extension="mp4")
        .order_by("resolution")
        .desc()
        .first()
    )
    audio_stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()

    video_filename = video_stream.default_filename
    audio_filename = "audio_" + video_filename

    video_path = os.path.join(output_path, video_filename)
    audio_path = os.path.join(output_path, audio_filename)

    output_file = os.path.join(output_path, "final_" + video_filename)

    if not os.path.exists(output_file):
        video_stream.download(filename=video_filename, output_path=output_path)
        audio_stream.download(filename=audio_filename, output_path=output_path)

        command = [
            "ffmpeg",
            "-i",
            video_path,
            "-i",
            audio_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            output_file,
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


def get_interesting_parts(transcript, split):
    # Concatenate transcript entries into a single text
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Calculate the size of each part
    part_size = ceil(len(transcript) / split)
    print("split: ", split)
    print("part_size: ", part_size)

    interesting_parts = []

    # Use OpenAI API to summarize and extract key points for each part
    for i in range(0, len(transcript), part_size):
        part = transcript[i : min(i + part_size, len(transcript))]
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that finds the most interesting and viral-worthy parts of a video transcript. Ensure the selected parts are coherent with a main idea established and are returned word-for-word from the transcript without any modifications.",
                },
                {
                    "role": "user",
                    "content": "The following is the transcript of the video. Identify the 10 most interesting and potentially viral parts of the transcript that are coherent with a main idea established. \
                        Each part should be a coherent segment rather than just a single sentence. Return a json object with the key 'interesting_parts' and a list of only the 10 most interesting parts. \
                        The selected parts must be word-for-word from the transcript. Here is the transcript: "
                    + part,
                },
            ],
        )

        # Print token summary of usage
        print("Usage:")
        print(response.usage)

        summary = json.loads(response.choices[0].message.content)

        # Parse the JSON and get the list of entries
        interesting_parts.extend(summary["interesting_parts"])

    return interesting_parts


if __name__ == "__main__":
    main()
