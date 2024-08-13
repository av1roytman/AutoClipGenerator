import tkinter as tk
from tkinter import messagebox
import re
from yt_dlp import YoutubeDL
from moviepy.editor import VideoFileClip
import os


def sanitize_title(title):
    # Remove any character that is not a word character, space, underscore, or dash
    sanitized_title = re.sub(r"[^\w\s\-_]", "", title)
    # Strip leading and trailing whitespace
    sanitized_title = sanitized_title.strip()
    return sanitized_title


def download_youtube_short(url):
    try:
        # Create the output directory if it doesn't exist
        output_dir = "StolenClips"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Download the video using yt-dlp
        with YoutubeDL({}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get("title", None)
            sanitized_title = sanitize_title(video_title)
            print("Sanitized title:", sanitized_title)

        ydl_opts = {
            "outtmpl": os.path.join(output_dir, f"{sanitized_title}.%(ext)s"),
            "format": "bestvideo+bestaudio/best",  # Get the best video and audio quality available
            "merge_output_format": "mp4",  # Ensure the output is mp4
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        temp_path = os.path.join(output_dir, f"{sanitized_title}.mp4")
        print(f"Downloaded video to: {temp_path}")

        # Convert to MOV format using MoviePy
        output_path = os.path.join(output_dir, f"{sanitized_title}.mov")
        clip = VideoFileClip(temp_path)
        clip.write_videofile(output_path, codec="libx264")
        print(f"Video successfully saved as {output_path}")

        # Remove the temporary MP4 file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"Removed temporary file: {temp_path}")

        messagebox.showinfo(
            "Success", f"Video successfully downloaded and saved as {output_path}"
        )

    except Exception as e:
        print(f"An error occurred: {e}")


def on_download_click(event=None):
    url = url_entry.get()
    if url:
        download_youtube_short(url)
        url_entry.delete(0, tk.END)  # Clear the URL entry after processing
    else:
        messagebox.showwarning("Input Error", "Please enter a YouTube link")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("YouTube Short Downloader")

    # Set window size
    root.geometry("400x150")

    # Add URL input field
    url_label = tk.Label(root, text="Enter YouTube URL:")
    url_label.pack(pady=10)
    url_entry = tk.Entry(root, width=50)
    url_entry.pack(pady=5)
    url_entry.bind(
        "<Return>", on_download_click
    )  # Bind the Enter key to trigger download

    # Add Download button
    download_button = tk.Button(root, text="Download Video", command=on_download_click)
    download_button.pack(pady=20)

    # Start the GUI event loop
    root.mainloop()
