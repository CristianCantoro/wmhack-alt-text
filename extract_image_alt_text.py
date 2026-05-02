#!/usr/bin/env python3

import argparse
import csv
import json
import logging
import re
from pathlib import Path
from html import unescape
from urllib.parse import urljoin, unquote

from bs4 import BeautifulSoup

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


IMAGE_NAMESPACE_ALIASES = {
    "image",
    "media",
    "immagine",
    "file",  # Italian Wikipedia also commonly uses File:
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".tif",
    ".tiff",
    ".ogg",
}


FILE_LINK_RE = re.compile(
    r"\[\[\s*([^:\]|]+)\s*:\s*([^\]|]+)",
    flags=re.IGNORECASE,
)


def get_commons_filename_from_image_url(image_url):
    """
    Extracts the Commons filename from Wikimedia image URLs, preserving capitalization.

    Handles URLs such as:
    - https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Foo.jpg/250px-Foo.jpg
      -> Foo.jpg
    - https://upload.wikimedia.org/wikipedia/commons/8/86/Foo.jpg
      -> Foo.jpg

    In Wikimedia thumbnail URLs, the original Commons filename is the last
    directory in the path, i.e. the second-to-last path component.
    """
    if not image_url:
        return ""

    image_url = unescape(image_url)
    image_url = unquote(image_url)

    path = image_url.split("?", 1)[0].split("#", 1)[0]
    parts = [part for part in path.split("/") if part]

    if not parts:
        return ""

    if "thumb" in parts and len(parts) >= 2:
        return parts[-2]

    return parts[-1]


def normalize_filename(filename):
    """
    Normalizes filenames so that wikitext filenames and HTML image URLs can be compared.

    Examples:
    - "Example image.jpg" -> "example_image.jpg"
    - "Example_image.jpg" -> "example_image.jpg"
    - URL-encoded names are decoded before comparison.
    """
    if not filename:
        return ""

    filename = unescape(filename)
    filename = unquote(filename)
    filename = filename.strip()

    # Remove namespace if present.
    if ":" in filename:
        maybe_namespace, rest = filename.split(":", 1)
        if maybe_namespace.strip().lower() in IMAGE_NAMESPACE_ALIASES:
            filename = rest

    filename = filename.replace(" ", "_")
    filename = re.sub(r"_+", "_", filename)

    return filename.lower()


def get_filename_from_image_url(image_url):
    """
    Extracts the original Wikimedia filename from common image URLs.

    Handles URLs such as:
    - https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Foo.jpg/220px-Foo.jpg
    - https://upload.wikimedia.org/wikipedia/commons/a/ab/Foo.jpg

    For thumbnail URLs, the original filename is usually the path component before
    the final thumbnail rendition filename.
    """
    if not image_url:
        return ""

    image_url = unescape(image_url)
    image_url = unquote(image_url)
    path = image_url.split("?", 1)[0].split("#", 1)[0]
    parts = [part for part in path.split("/") if part]

    if not parts:
        return ""

    if "thumb" in parts and len(parts) >= 2:
        # In Wikimedia thumb URLs, the original file is the second-to-last path segment.
        return normalize_filename(parts[-2])

    return normalize_filename(parts[-1])


def get_page_id(record):
    identifier = record.get("identifier")

    if isinstance(identifier, dict):
        return (
            identifier.get("page_id")
            or identifier.get("id")
            or identifier.get("value")
            or ""
        )

    if identifier is not None:
        return identifier

    return record.get("page_id", "")


def get_page_title(record):
    return (
        record.get("name")
        or record.get("page_title")
        or record.get("title")
        or ""
    )


def get_html(record):
    article_body = record.get("article_body")

    if isinstance(article_body, dict):
        return article_body.get("html") or ""

    return ""


def get_wikitext(record):
    article_body = record.get("article_body")

    if isinstance(article_body, dict):
        return article_body.get("wikitext") or ""

    return ""


def extract_image_filenames_from_wikitext(wikitext):
    """
    Extracts image filenames from wikitext file links, for example:

    [[File:Example.jpg|thumb|alt=Example alt text|Caption]]
    [[Immagine:Esempio.png|miniatura|Didascalia]]

    Returns a set of normalized filenames.
    """
    filenames = set()

    for match in FILE_LINK_RE.finditer(wikitext):
        namespace = match.group(1).strip().lower()
        filename = match.group(2).strip()

        if namespace not in IMAGE_NAMESPACE_ALIASES:
            continue

        normalized = normalize_filename(filename)

        if normalized:
            filenames.add(normalized)

    return filenames


def extract_images_from_html(html, allowed_filenames=None, base_url="https://it.wikipedia.org"):
    soup = BeautifulSoup(html, "html.parser")

    for img in soup.find_all("img"):
        image_url = img.get("src") or img.get("data-src") or ""

        if not image_url:
            continue

        image_url = unescape(image_url)

        # Convert protocol-relative URLs such as //upload.wikimedia.org/... to https://...
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        else:
            image_url = urljoin(base_url, image_url)

        html_filename = get_filename_from_image_url(image_url)

        if allowed_filenames is not None and html_filename not in allowed_filenames:
            continue

        alt_text = img.get("alt") or ""
        alt_text = unescape(alt_text).strip()

        yield {
            "image_url": image_url,
            "image_filename": html_filename,
            "has_alt_text": bool(alt_text),
            "alt_text": alt_text,
        }


def count_pages(path):
    """
    Counts non-empty lines in an NDJSON file.
    Assumes one page/article per non-empty line.
    """
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def process_file(path, base_url, quiet=False, progress_bar=None, filter_body_images=True):
    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                logging.warning(
                    "Skipping invalid JSON in %s:%s: %s",
                    path,
                    line_number,
                    e,
                )
                if progress_bar is not None:
                    progress_bar.update(1)
                continue

            page_id = get_page_id(record)
            page_title = get_page_title(record)
            html = get_html(record)
            wikitext = get_wikitext(record)

            allowed_filenames = None
            if filter_body_images:
                allowed_filenames = extract_image_filenames_from_wikitext(wikitext)

            if not quiet:
                print(f"Processing page '{page_title}'", end="", flush=True)

            images = []

            for image in extract_images_from_html(
                html,
                allowed_filenames=allowed_filenames,
                base_url=base_url,
            ):
                images.append(image)
                if not quiet:
                    print(".", end="", flush=True)

            if not quiet:
                print()

            if progress_bar is not None:
                progress_bar.update(1)

            for image in images:
                yield {
                    "page_id": page_id,
                    "page_title": page_title,
                    "image_url": image["image_url"],
                    "image_filename": get_commons_filename_from_image_url(image['image_url']),
                    "has_alt_text": image["has_alt_text"],
                    "alt_text": image["alt_text"],
                }


def main():
    parser = argparse.ArgumentParser(
        description="Extract body image URLs and alt text from article_body.html in NDJSON files."
    )

    parser.add_argument(
        "input_files",
        nargs="+",
        help="One or more input .ndjson files",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output CSV/TSV file",
    )

    parser.add_argument(
        "--base-url",
        default="https://it.wikipedia.org",
        help="Base URL used to resolve relative image URLs. Default: https://it.wikipedia.org",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable per-page progress logging.",
    )

    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show a progress bar with processed pages over the total. Implies --quiet",
    )

    parser.add_argument(
        "--delimiter",
        default="\t",
        help="Output delimiter. Default: tab. Use ',' for CSV.",
    )

    parser.add_argument(
        "--include-all-html-images",
        action="store_true",
        help=(
            "Do not filter images through article_body.wikitext. "
            "By default, only HTML images whose filenames also appear in wikitext are selected."
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    if args.progress and tqdm is None:
        parser.error(
            "The --progress option requires tqdm. Install it with: pip install tqdm"
        )

    fieldnames = [
        "page_id",
        "page_title",
        "image_url",
        "image_filename",
        "has_alt_text",
        "alt_text",
    ]

    input_paths = []
    for input_file in args.input_files:
        path = Path(input_file)

        if not path.exists():
            logging.warning("File not found: %s", input_file)
            continue

        input_paths.append(path)

    total_pages = None
    if args.progress:
        total_pages = sum(count_pages(path) for path in input_paths)

    progress_bar = None
    if args.progress:
        args.quiet = True
        progress_bar = tqdm(
            total=total_pages,
            unit="page",
            desc="Processing pages",
        )

    try:
        with open(args.output, "w", encoding="utf-8", newline="") as out_f:
            writer = csv.DictWriter(
                out_f,
                fieldnames=fieldnames,
                delimiter=args.delimiter,
            )
            writer.writeheader()

            for path in input_paths:
                for row in process_file(
                    path,
                    base_url=args.base_url,
                    quiet=args.quiet,
                    progress_bar=progress_bar,
                    filter_body_images=not args.include_all_html_images,
                ):
                    writer.writerow(row)
    finally:
        if progress_bar is not None:
            progress_bar.close()


if __name__ == "__main__":
    main()
