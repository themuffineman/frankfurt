from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
import os
load_dotenv(dotenv_path=".env.local")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class FilterSchema(BaseModel):
    """
    Represents the schema for the LLM response containing filtered personal blog URLs.
    """
    data: list[str]

def filter_personal_blogs(input_list: list[str]) -> list[str]:
    """
    Filters the input list to keep only URLs that are likely personal blogs
    maintained by individuals, removing corporate blogs, company websites,
    software documentation sites, and non-personal content platforms.
    
    Args:
        input_list: List of URLs to filter
        
    Returns:
        List of URLs that are likely personal blogs
    """
    response = client.responses.parse(
        model="gpt-4.1-nano",
        input=[
            {"role": "system", "content": """Filter this list to include only URLs that are likely personal blogs maintained by individuals. Remove any URLs for corporate blogs, company websites, software documentation sites, or non-personal content platforms. I'm specifically looking for authentic, personal blogs written by real individuals, not organizational or commercial content."""},
            {
                "role": "user",
                "content": f"{input_list}",
            },
        ],
        text_format=FilterSchema,
    )
    return response.output_parsed.data
