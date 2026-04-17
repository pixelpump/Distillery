import re
import trafilatura
from trafilatura.settings import use_config
from dataclasses import dataclass
from typing import Optional


@dataclass
class Article:
    title: str
    author: Optional[str]
    date: Optional[str]
    text: str
    word_count: int


def fetch_article(url: str) -> Article:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not download content from URL: {url}")

    config = use_config()
    config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")

    result = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        output_format="txt",
        config=config,
    )

    if not result:
        raise ValueError("Could not extract article content from the page. The page may require JavaScript or block scrapers.")

    result = re.sub(r'\n{3,}', '\n\n', result).strip()

    metadata = trafilatura.extract_metadata(downloaded)

    title = (metadata.title if metadata and metadata.title else "Untitled Article")
    author = (metadata.author if metadata and metadata.author else None)
    date = (metadata.date if metadata and metadata.date else None)

    words = result.split()
    word_count = len(words)

    return Article(
        title=title,
        author=author,
        date=date,
        text=result,
        word_count=word_count,
    )
