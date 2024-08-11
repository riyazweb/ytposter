import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, VideoUnavailable, NoTranscriptFound
import discord
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
from bing_image_downloader import downloader
import google.generativeai as genai

# Configure the Gemini API
genai.configure(api_key='AIzaSyDYqg7nDC9wZsYQi5QAXR52b-XWIKvNCnQ')

# Create an instance of a Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

summary_points = []


def extract_video_id(url):
    """
    Extracts the video ID from a YouTube URL.
    """
    video_id_pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.match(video_id_pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid YouTube URL")


def get_transcript(url, languages=['en', 'hi']):
    try:
        video_id = extract_video_id(url)
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=languages)
        transcript_text = ' '.join(entry['text'] for entry in transcript)
        return transcript_text
    except VideoUnavailable:
        return "The video is unavailable."
    except TranscriptsDisabled:
        return "Transcripts are disabled for this video."
    except NoTranscriptFound:
        return "No transcript found for the specified languages."
    except ValueError as ve:
        return str(ve)
    except Exception as e:
        return f"An error occurred: {e}"


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')


@client.event
async def on_message(message):
    global summary_points

    if message.author == client.user:
        return

    if message.content.startswith('!yt'):
        args = message.content.split()
        if len(args) < 2:
            await message.channel.send("Usage: !yt <YouTube URL>")
            return

        url = args[1]
        transcript = get_transcript(url)

        # Send the transcript to the Gemini API to get five summary points
        prompt = f"translate to english then make upto 10 key points each lpoint should be only in one line each line,all in only in 100 words only dont include numbers or mention numbers in points dont include *:\n\n{transcript}"
        import re

        response = genai.GenerativeModel(
            'gemini-1.5-flash').generate_content(prompt)
        summary_points = [re.sub(r'[^\w\s]', '', point).strip()
                          for point in response.text.strip().split('\n')]

        await message.channel.send("Generated 5 key points from the transcript:")
        for i, point in enumerate(summary_points):
            await message.channel.send(f"{i + 1}. {point}")

    elif message.content.startswith('!c'):
        args = message.content.split()
        if len(args) < 3:
            await message.channel.send("Usage: !c <point number> <image search term>")
            return

        point_number = int(args[1]) - 1
        search_term = ' '.join(args[2:])

        if point_number < 0 or point_number >= len(summary_points):
            await message.channel.send("Invalid point number.")
            return

        point = summary_points[point_number]
        downloader.download(f"{search_term}", limit=4, output_dir="images",
                            adult_filter_off=True, force_replace=False)

        image_files = []
        for j in range(1, 5):
            image_dir_jpg = f"/content/drive/MyDrive/ha/images/{search_term}/Image_{j}.jpg"
            
            image_dir_png = f"/content/drive/MyDrive/ha/images/{search_term}/Image_{j}.png"

            if os.path.exists(image_dir_jpg):
                image_dir = image_dir_jpg
            elif os.path.exists(image_dir_png):
                image_dir = image_dir_png
            else:
                await message.channel.send(f"Image {j} not found for point {point_number + 1}.")
                continue

            img = Image.open(image_dir)
            new_img = Image.new('RGB', (600, 600), (255, 255, 255))
            x = (600 - img.width) // 2
            y = (600 - img.height) // 2
            new_img.paste(img, (x, y))

            overlay = Image.open('/content/drive/MyDrive/ha/tranfx.png')
            print("..........used overlay................")
            overlay = overlay.resize((600, 600))
            overlay = overlay.convert("RGBA")
            new_img.paste(overlay, (0, 0), overlay)

            draw = ImageDraw.Draw(new_img)
            font = ImageFont.truetype(
                '/content/drive/MyDrive/ha/Muroslant.otf', size=35)
            max_width = 750
            wrapped_text = textwrap.wrap(
                point, width=int(max_width / font.getbbox('x')[2]))
            total_text_height = len(wrapped_text) * \
                font.getbbox(wrapped_text[0])[3]
            y = new_img.height - total_text_height - 50

            for line in wrapped_text:
                line_width = draw.textlength(line, font=font)
                line_height = font.getbbox(line)[3]
                x = (new_img.width - line_width) // 2
                draw.text((x, y), line, fill='white', font=font)
                y += line_height

            title_dir = f"{search_term}"
            if not os.path.exists(title_dir):
                os.makedirs(title_dir)

            img_filename = f"/content/drive/MyDrive/ha/{title_dir}/image_{point_number + 1}_{j}.png"
            new_img.save(img_filename)
            image_files.append(img_filename)
            print(f"Saved image as {img_filename}")

        if image_files:
            await message.channel.send(files=[discord.File(img_file) for img_file in image_files])

# Run the bot with your token
client.run(
    'MTEyOTAxMjc0MzQwODcxMzc2OA.GjhZ7c.zJOZ9THDUFS8NhMts30x2uO899N9kIzGPc-FFk')
