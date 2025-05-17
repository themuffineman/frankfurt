from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from markdownify import markdownify as md
from urllib.parse import urlparse
from collections import deque
import re
import requests



import os
load_dotenv(dotenv_path=".env.local")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ai_model = "gpt-4o-mini"

class FilterSchema(BaseModel):
    """
    Represents the schema for the LLM response containing filtered personal blog URLs.
    """
    data: list[str]

def filter_personal_blogs(input_list: list[str]) -> list[str]:
    """
    Filters the input list to keep only URLs that are likely creator blogs
    maintained by individual creators, removing corporate blogs, company websites,
    software documentation sites.
    
    Args:
        input_list: List of URLs to filter
        
    Returns:
        List of URLs that are likely personal blogs
    """
    print("original: ", len(input_list))
    response = client.responses.parse(
        model=ai_model,
        input=[
            {"role": "system", "content": """Filter this list of URLs to include only URLs that are likely personal blogs maintained by actaul independent individuals. Remove any URLs for corporate blogs, company websites, software documentation sites, or non-personal content platforms. I'm specifically looking for authentic, personal blogs written by real individuals, not organizational, software tools, agencies  or commercial content."""},
            {
                "role": "user",
                "content": f"{input_list}",
            },
        ],
        text_format=FilterSchema,
    )
    print("after filtering links: ", len(response.output_parsed.data))

    return response.output_parsed.data


def filter_irrelavant_urls(input_list: list[str]) -> list[str]:
    """
    Filters the input list to keep only URLs that are likely to contain the following information for outreach purposes:
        - The email address of the owner
        - The owners's name
        - The owners's social media links
        - The owners's personal website
        - Any course or products they are selling

    Any URLs that are not likely contain this information are removed from the list.

    .
    
    Args:
        input_list: List of URLs to filter
        
    Returns:
        List of URLs that are likely to contain the above information
        1. The email address of the owner   
        2. The owners's name
        4. The owners's personal information
        5. Any course or products they are selling
    """
    print("Before removing irelavant urls: ", len(input_list))
    response = client.responses.parse(
        model=ai_model,
        input=[
            {"role": "system", "content": """ 
             Filter this list of URLs for a personal to include only URLs that are likely to contain the following information for outreach purposes:
                - The email address of the owner
                - The owners's name
                - The owners's personal information or bio inorder to persoanlize outreach
                - Any course or products they are selling
             Any URLs that are not likely contain this information are removed from the list.
             """
            },
            {
                "role": "user",
                "content": f"{input_list}",
            },
        ],
        text_format=FilterSchema,
    )
    print("After removing irrelavant urls: ", len(response.output_parsed.data))
    return response.output_parsed.data

def extract_blog_data_recursively(driver,links):
    """
    Recursively extract blog data from a given domain.
    
    Args:
        driver: WebDriver instance
        links: List of links to follow for further extraction
    """
    init_links = deque(links)
    visited = set()
    extracted_content = {
        "email": None,
        "name": None,
        "bio": None,
        "course_product": None,
    }
    while len(init_links) > 0:
        try:
            best_url = best_url_to_follow(init_links, extracted_content)
            print("Best URL to follow: ", best_url)
            if best_url in visited:
                init_links.remove(best_url)
                continue
            visited.add(best_url)
            print("Links available to scrape: ", len(init_links))
            driver.set_page_load_timeout(60)
            driver.get(best_url)
            page_content = extract_markdown_from_html(driver.page_source)
            extracted_content = scrape_blog_data(extracted_content, page_content)
            print("Extracted Content: ", extracted_content)
            if all(value is not None for value in extracted_content.values()):
                print("All required data extracted.")
                break
        except Exception as e:
            print(f"An error occurred: {e}")
    return extracted_content
        



def update_none_values(target_dict, source_dict):
    for key, value in source_dict.items():
        if key in target_dict and target_dict[key] is None:
            target_dict[key] = value
    return target_dict


def scrape_blog_data(extracted_content, page_content):
    
    class PageDataSchema(BaseModel):
        """
        Represents the schema for the LLM response containing required data extracted from the page.
        """
        name:str|None
        email:str|None
        bio:str|None
        course_product:str|None
   
    is_data_on_page_prompt = f"""
        You are a data extraction bot. Your job is to extract data from the given page.
        You will be given the page content and you need to extract the that am looking for.
        The data I am looking for is:
        1. The email address of the owner
        2. The owners's name
        3. The personal bio or information of the owner for personalization of the outreach
        4. The course or products they are selling
        If you find any of this data on the page, please extract it and return it in the following format:
        {extracted_content}
        If you do not find a certain key data on the page, please return None for that specific field that you dont find.
        
    """
    # Extract data from the page using LLM
    response = client.responses.parse(
        model=ai_model,
        input=[
            {"role": "system", "content": is_data_on_page_prompt},
            {
                "role": "user",
                "content": f"{page_content}",
            },
        ],
        text_format=PageDataSchema,
    )
    response_content = response.output_parsed
    extracted_content = update_none_values(extracted_content, response_content.dict())
    return extracted_content

    

def best_url_to_follow( links, extracted_content):
    """
    Given a list of links, determine which link is most likely to contain the required data.
    
    Args:
        links: List of links to evaluate
    """
    class URLToFollowSchema(BaseModel):
        """
        Represents the schema for the LLM response containing URL to follow for further extraction.
        """
        url:str
    extracted_content_with_none_values = {key: value for key, value in extracted_content.items() if value is None}
    which_url_to_follow_prompt = f"""
        You are a scraping bot and you are required to extract specific information from a page.
        Given the list of links, tell me which link should I navigate to that is most likely to contain the following information:
        extracted info: {extracted_content_with_none_values}
        links: {links}
    """
    response = client.responses.parse(
        model="gpt-4.1-nano",
        input=[
            {"role": "system", "content": which_url_to_follow_prompt},
            {
                "role": "user",
                "content": f"{extracted_content_with_none_values}",
            },
        ],
        text_format=URLToFollowSchema,
    )
    # Extract the URL to follow from the response
    url_to_follow = response.output_parsed.url
    return url_to_follow

def extract_blog_content_and_links(driver, href):
    """
    Navigate to a blog post and return the links on the page and its content
    
    Args:
        driver: WebDriver instance
        href: URL of the blog post
    """
        # Extract the root domain from the href
    parsed_url = urlparse(href)
    root_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    try:
        driver.set_page_load_timeout(60)
        driver.get(root_domain)
    except Exception as e:
        raise Exception(f"Page took too long to load: {e}")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    # Remove all script and head tags from the page source
    page_source = driver.page_source
    markdown_content = extract_markdown_from_html(page_source)
    # Extract all links from the markdown content
    links = re.findall(r'\[.*?\]\((http[s]?://.*?)\)', markdown_content)
    links = [link for link in links if not re.search(r'\.(?:jpg|jpeg|png|gif|bmp|svg)(?:\?.*)?$', link, re.IGNORECASE)]

    # Filter links that contain the root domain
    filtered_links = [link for link in links if root_domain in link]
    return markdown_content,filtered_links

def extract_markdown_from_html(html_content):
    """
    Extracts markdown content from HTML content.
    
    Args:
        html_content: HTML content to extract markdown from
        
    Returns:
        Extracted markdown content
    """
    # Remove all <head>, <script>, and <img> tags from the page source
    markdown_content = re.sub(r'<(head|script|img)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL)
    # Remove all base64 URLs from the page source
    markdown_content = re.sub(r'data:image/[^;]+;base64,[^\"]+', '', markdown_content)
    # Remove all <a> tags that have hrefs pointing to image URLs
    markdown_content = re.sub(r'<a[^>]*href=["\'].*?\.(?:jpg|jpeg|png|gif|bmp|svg)["\'][^>]*>.*?</a>', '', markdown_content, flags=re.DOTALL | re.IGNORECASE)
    return md(markdown_content)

def send_results_to_crm(body):
    """
    Send results to CRM system
    Args:
        body: The data to be sent
    """
    url = os.getenv("CRM_URL")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv("CRM_TOKEN")}"  # Replace with your API token if required
    }

    try:
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        print(f"Results successfully sent to CRM: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send results to CRM: {e}")
    pass

