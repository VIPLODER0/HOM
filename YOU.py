import os
import instaloader
import ffmpeg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from pytube import YouTube
from fbdown import download_video
import uuid
import logging
import time
from functools import partial

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Instaloader
L = instaloader.Instaloader()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username or update.message.from_user.first_name
    logger.info(f"User {username} started the bot")
    await update.message.reply_text(
        "Welcome to the Video Downloader Bot! 🎥\n"
        "Send a YouTube, Instagram, or Facebook video link to download.\n"
        "For YouTube, choose quality (up to 4K) or audio-only."
    )

# Progress callback for YouTube downloads
async def progress_callback(stream, chunk, bytes_remaining, update, context, message_id):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    if percentage % 10 < 1:  # Update every ~10%
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"Downloading: {percentage:.1f}%"
            )
        except Exception as e:
            logger.warning(f"Failed to update progress: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    username = update.message.from_user.username or update.message.from_user.first_name
    logger.info(f"User {username} sent URL: {url}")
    
    if "youtube.com" in url or "youtu.be" in url:
        await handle_youtube(update, context, url, username)
    elif "instagram.com" in url:
        await handle_instagram(update, context, url, username)
    elif "facebook.com" in url or "fb.watch" in url:
        await handle_facebook(update, context, url, username)
    else:
        await update.message.reply_text(
            "Please send a valid YouTube, Instagram, or Facebook video link."
        )

async def handle_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, username: str):
    try:
        yt = YouTube(url)
        # Include both progressive and adaptive streams for video
        streams = yt.streams.filter(file_extension="mp4", type="video").order_by("resolution").desc()
        if not streams:
            await update.message.reply_text(
                "No suitable video streams found for this YouTube video."
            )
            return

        # Prepare quality options
        quality_buttons = [
            [
                InlineKeyboardButton(
                    f"{stream.resolution} ({stream.mime_type})",
                    callback_data=f"yt_{stream.itag}_{url}"
                )
            ]
            for stream in streams if stream.resolution
        ]
        quality_buttons.append(
            [InlineKeyboardButton("Audio Only (MP3)", callback_data=f"yt_audio_{url}")]
        )
        reply_markup = InlineKeyboardMarkup(quality_buttons)

        await update.message.reply_text(
            f"Select the quality for '{yt.title}':", reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error processing YouTube URL {url} for {username}: {str(e)}")
        await update.message.reply_text(
            f"Error processing YouTube video: {str(e)}. Ensure the link is valid and the video is accessible."
        )

async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, username: str):
    try:
        # Send initial downloading message
        status_message = await update.message.reply_text("Downloading: 0%")
        
        # Extract shortcode from Instagram URL
        shortcode = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Generate unique filename
        filename = f"ig_{uuid.uuid4().hex}.mp4"
        L.download_post(post, target=filename)
        
        # Find the downloaded video file
        video_file = None
        for file in os.listdir("."):
            if file.startswith(filename) and file.endswith(".mp4"):
                video_file = file
                break
        
        if video_file and os.path.exists(video_file):
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                text="Download complete! Uploading..."
            )
            with open(video_file, "rb") as f:
                await update.message.reply_video(video=f, caption="Downloaded from Instagram")
            os.remove(video_file)
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                text="Failed to download Instagram video."
            )
        
        # Clean up any additional files
        for file in os.listdir("."):
            if file.startswith(filename):
                os.remove(file)
                
    except Exception as e:
        logger.error(f"Error processing Instagram URL {url} for {username}: {str(e)}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_message.message_id,
            text=f"Error downloading Instagram reel: {str(e)}. Ensure the link is valid and the post is public."
        )

async def handle_facebook(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, username: str):
    try:
        # Send initial downloading message
        status_message = await update.message.reply_text("Downloading: 0%")
        
        # Generate unique filename
        filename = f"fb_{uuid.uuid4().hex}.mp4"
        download_video(url, filename)
        
        if os.path.exists(filename):
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                text="Download complete! Uploading..."
            )
            with open(filename, "rb") as f:
                await update.message.reply_video(video=f, caption="Downloaded from Facebook")
            os.remove(filename)
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                text="Failed to download Facebook video."
            )
            
    except Exception as e:
        logger.error(f"Error processing Facebook URL {url} for {username}: {str(e)}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_message.message_id,
            text=f"Error downloading Facebook video: {str(e)}. Ensure the link is valid and the video is public."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    username = query.from_user.username or query.from_user.first_name
    data = query.data.split("_")
    action = data[0]
    if action == "yt":
        itag = data[1]
        url = "_".join(data[2:])
        logger.info(f"User {username} selected YouTube quality {itag} for {url}")
        await download_youtube_video(query, context, url, itag, username)
    elif action == "yt_audio":
        url = "_".join(data[2:])
        logger.info(f"User {username} selected YouTube audio for {url}")
        await download_youtube_audio(query, context, url, username)

async def download_youtube_video(
    query: Update, context: ContextTypes.DEFAULT_TYPE, url: str, itag: str, username: str
):
    try:
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(itag)
        if not stream:
            await query.message.reply_text("Selected quality is no longer available.")
            return

        # Send initial downloading message
        status_message = await query.message.reply_text("Downloading: 0%")
        
        # Register progress callback
        progress_func = partial(progress_callback, update=query, context=context, message_id=status_message.message_id)
        yt.register_on_progress_callback(progress_func)
        
        filename = f"yt_{uuid.uuid4().hex}.mp4"
        if stream.is_adaptive:
            # Download video stream
            video_file = f"video_{uuid.uuid4().hex}.mp4"
            stream.download(filename=video_file)
            # Download audio stream
            audio_stream = yt.streams.filter(only_audio=True).first()
            audio_file = f"audio_{uuid.uuid4().hex}.mp4"
            audio_stream.download(filename=audio_file)
            # Merge video and audio using ffmpeg
            stream_video = ffmpeg.input(video_file)
            stream_audio = ffmpeg.input(audio_file)
            ffmpeg.output(
                stream_video, stream_audio, filename, vcodec="copy", acodec="aac", strict="experimental"
            ).run(overwrite_output=True)
            os.remove(video_file)
            os.remove(audio_file)
        else:
            # Download progressive stream (video + audio)
            stream.download(filename=filename)

        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_message.message_id,
            text="Download complete! Uploading..."
        )
        
        with open(filename, "rb") as f:
            await query.message.reply_video(
                video=f, caption=f"Downloaded from YouTube: {yt.title}"
            )
        os.remove(filename)
        
    except Exception as e:
        logger.error(f"Error downloading YouTube video {url} for {username}: {str(e)}")
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_message.message_id,
            text=f"Error downloading video: {str(e)}. Please try again."
        )

async def download_youtube_audio(
    query: Update, context: ContextTypes.DEFAULT_TYPE, url: str, username: str
):
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(only_audio=True).first()
        if not stream:
            await query.message.reply_text("No audio stream available for this video.")
            return
        
        # Send initial downloading message
        status_message = await query.message.reply_text("Downloading: 0%")
        
        # Register progress callback
        progress_func = partial(progress_callback, update=query, context=context, message_id=status_message.message_id)
        yt.register_on_progress_callback(progress_func)
        
        filename = f"yt_audio_{uuid.uuid4().hex}.mp3"
        stream.download(filename=filename)
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_message.message_id,
            text="Download complete! Uploading..."
        )
        
        with open(filename, "rb") as f:
            await query.message.reply_audio(
                audio=f, caption=f"Audio from YouTube: {yt.title}"
            )
        os.remove(filename)
        
    except Exception as e:
        logger.error(f"Error downloading YouTube audio {url} for {username}: {str(e)}")
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=status_message.message_id,
            text=f"Error downloading audio: {str(e)}. Please try again."
        )

def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    application = Application.builder().token("7917489800:AAFvqTFOIWwcVR0IPEwxJCbFRF9EwWE-Fxw").build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.run_polling()

if __name__ == "__main__":
    main()