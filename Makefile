# Makefile to download YouTube videos and convert them to iPhone-compatible MOV format using yt-dlp

# Variables
YOUTUBE_DL := yt-dlp
FORMAT_VIDEO := "bestvideo+bestaudio/best"
OUTPUT_DIR := stolen
RECODE_FORMAT := mp4
FINAL_FORMAT := mov

# Ensure the output directory exists
$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)

# Default target
.PHONY: download
download: $(OUTPUT_DIR)
	$(YOUTUBE_DL) -f $(FORMAT_VIDEO) -o "$(OUTPUT_DIR)/%(title)s.%(ext)s" --merge-output-format $(RECODE_FORMAT) $(URL)
	# Find the most recently downloaded file and convert to MOV format using FFmpeg
	NEWFILE=$$(ls -t $(OUTPUT_DIR)/*.mp4 | head -n 1) && \
	ffmpeg -i "$$NEWFILE" -vcodec libx264 -acodec aac "$${NEWFILE%.mp4}.$(FINAL_FORMAT)"

# Help target to display usage
.PHONY: help
help:
	@echo "Usage: make download URL=<youtube_url>"
	@echo "Example: make download URL=https://www.youtube.com/watch?v=example"

# Clean target to remove downloaded files (optional)
.PHONY: clean
clean:
	rm -f $(OUTPUT_DIR)/*.mp4
	rm -f $(OUTPUT_DIR)/*.mov