# main.py
import pandas as pd
import asyncio
from linkedin_scrap import scrape_profiles, generate_welcome_message
from welcome_audio import create_audio_from_text

EXCEL_FILE_PATH = "D:/Projects/Liminal/Linkedin_webscrap/Profile_links.xlsx"
AUDIO_OUTPUT_FOLDER = "D:/Projects/Liminal/Linkedin_webscrap/Welcome_Audio"


async def main():
    # Load profile links from Excel file
    profile_links_df = pd.read_excel(EXCEL_FILE_PATH)
    profile_links = profile_links_df['Profile_Links'].tolist()

    # Scrape LinkedIn profiles
    profiles_data = await scrape_profiles(profile_links)

    # Generate and save audio welcome message for each new profile
    for index, profile_data in enumerate(profiles_data):
        welcome_message = generate_welcome_message(profile_data['profile'])
        filename = f"welcome_message_{index + 1}.mp3"
        create_audio_from_text(welcome_message, AUDIO_OUTPUT_FOLDER, filename)


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
