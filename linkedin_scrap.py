import json
import os
import re
from typing import List, Dict
from dotenv import load_dotenv
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from parsel import Selector
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

# Load environment variables
load_dotenv()
scrapfly_api_key = os.getenv("SCRAPFLY_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

# Initialize clients
SCRAPFLY = ScrapflyClient(key=scrapfly_api_key)
llm = ChatGroq(model_name='llama-3.2-1b-preview', api_key=groq_api_key)

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "headers": {"Accept-Language": "en-US,en;q=0.5"}
}

# File paths
SCRAPED_LINKS_FILE = "D:/Projects/Liminal/Linkedin_webscrap/scraped_links.txt"
PROFILE_OUTPUT_FOLDER = "D:/Projects/Liminal/Linkedin_webscrap/profile_jsons"

# Ensure the output folder exists
os.makedirs(PROFILE_OUTPUT_FOLDER, exist_ok=True)

def load_scraped_links() -> set:
    """Load previously scraped links from file."""
    if os.path.exists(SCRAPED_LINKS_FILE):
        with open(SCRAPED_LINKS_FILE, "r") as file:
            return set(link.strip() for link in file.readlines())
    return set()

def save_scraped_link(link: str):
    """Save a newly scraped link to file."""
    with open(SCRAPED_LINKS_FILE, "a") as file:
        file.write(f"{link}\n")

def sanitize_filename(url: str) -> str:
    """Generate a safe filename from URL by removing invalid characters."""
    profile_name = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', profile_name)
    return safe_name if safe_name else "profile_unknown"

def refine_profile(data: Dict) -> Dict:
    """Refine and clean the parsed profile data."""
    parsed_data = {}
    profile_data = [key for key in data["@graph"] if key["@type"] == "Person"][0]
    profile_data["worksFor"] = [profile_data["worksFor"][0]]
    articles = [key for key in data["@graph"] if key["@type"] == "Article"]
    for article in articles:
        selector = Selector(article["articleBody"])
        article["articleBody"] = "".join(selector.xpath("//p/text()").getall())
    parsed_data["profile"] = profile_data
    parsed_data["posts"] = articles
    return parsed_data

def parse_profile(response: ScrapeApiResponse) -> Dict:
    """Parse profile data from hidden script tags."""
    selector = response.selector
    data = json.loads(selector.xpath("//script[@type='application/ld+json']/text()").get())
    return refine_profile(data)

async def scrape_profiles(urls: List[str]) -> List[Dict]:
    """Scrape LinkedIn profiles, skipping those already scraped."""
    # Load previously scraped links
    scraped_links = load_scraped_links()
    new_profiles = []
    to_scrape = []

    # Filter URLs to only new ones
    for url in urls:
        if url not in scraped_links:
            to_scrape.append(ScrapeConfig(url, **BASE_CONFIG))
        else:
            print(f"Skipping already scraped link: {url}")

    # Scrape the new URLs
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        # The original LinkedIn URL
        linkedin_url = response.request.url.split("url=")[-1]
        linkedin_url = json.loads(f'"{linkedin_url}"')  # Decode URL-encoded string

        # Parse the profile data
        profile_data = parse_profile(response)
        new_profiles.append(profile_data)

        # Save the profile data as JSON
        profile_filename = os.path.join(PROFILE_OUTPUT_FOLDER, f"{sanitize_filename(linkedin_url)}.json")
        with open(profile_filename, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        print(f"Saved profile data to {profile_filename}")

        # Mark the LinkedIn URL as scraped
        save_scraped_link(linkedin_url)

    print(f"Scraped and saved {len(new_profiles)} new profiles.")
    return new_profiles

def generate_welcome_message(profile_data: Dict) -> str:
    """Generate a welcome message using the LLM based on profile data."""
    chat_prompt = ChatPromptTemplate(messages=[
        HumanMessagePromptTemplate.from_template(
            "Based on the LinkedIn profile information, create a personalized welcome message.\n\nProfile Data:\n{profile_data}\n\nWelcome Message:"
        )
    ])
    profile_json = json.dumps(profile_data, indent=2)
    prompt_inputs = {"profile_data": profile_json}
    response = llm(chat_prompt.format_prompt(**prompt_inputs).to_messages())
    return response.content
