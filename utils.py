import datetime
import locale
import re
from bs4 import BeautifulSoup
import markdown
from markdown.extensions.toc import TocExtension
import logging
from typing import List, Dict, Any
import json

def get_human_readable_datetime() -> str:
    """
    Returns the current date and time in a human-readable format.
    """
    locale.setlocale(locale.LC_TIME, '')
    now = datetime.datetime.now()
    return now.strftime("%d{} of %B %Y, %H:%M").format(
        'th' if 11 <= now.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(now.day % 10, 'th')
    )

def fix_footnotes(text: str) -> str:
    """
    Fixes footnote formatting in the given text.
    """
    return re.sub(r'\[\^(\d+)\^\]', r'[^\1]', text)

def render_markdown(text: str) -> str:
    """
    Renders the given markdown text to HTML.
    """
    md = markdown.Markdown(extensions=[
        'toc',
        'codehilite',
        'fenced_code',
        'footnotes',
        'tables',
        'nl2br',
        TocExtension(baselevel=2)
    ])
    html = md.convert(text)
    soup = BeautifulSoup(html, 'html.parser')
    for footnote_div in soup.find_all('div', class_='footnote'):
        for hr in footnote_div.find_all('hr'):
            hr.decompose()
    cleaned_html = str(soup)
    md.reset()
    return cleaned_html

def extract_content_between_tags(text: str, tag: str) -> str:
    """
    Extracts content between specified XML-like tags.
    """
    pattern = f'<{tag}>(.*?)</{tag}>'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ''

def setup_logging(log_file: str = 'app.log', log_level: int = logging.INFO) -> None:
    """
    Sets up logging for the application.
    """
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='a'
    )
    # Also log to console
    console = logging.StreamHandler()
    console.setLevel(log_level)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncates the given text to the specified maximum length.
    """
    return (text[:max_length] + '...') if len(text) > max_length else text

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """
    Flattens a nested dictionary.
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """
    Safely loads a JSON string, returning a default value if parsing fails.
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return default

def remove_html_tags(text: str) -> str:
    """
    Removes HTML tags from the given text.
    """
    return re.sub(r'<[^>]+>', '', text)

def normalize_url(url: str) -> str:
    """
    Normalizes the given URL by removing the protocol and 'www.' prefix.
    """
    return re.sub(r'^(https?://)?(www\.)?', '', url.lower())

def group_by(items: List[Dict[str, Any]], key: str) -> Dict[Any, List[Dict[str, Any]]]:
    """
    Groups a list of dictionaries by a specified key.
    """
    groups = {}
    for item in items:
        groups.setdefault(item.get(key), []).append(item)
    return groups

def retry(func, max_attempts: int = 3, delay: int = 1):
    """
    Decorator to retry a function with exponential backoff.
    """
    def wrapper(*args, **kwargs):
        attempts = 0
        while attempts < max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                if attempts == max_attempts:
                    raise
                time.sleep(delay * (2 ** (attempts - 1)))
    return wrapper