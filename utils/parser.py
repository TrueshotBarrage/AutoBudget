import logging
import re

from bs4 import BeautifulSoup
from dateutil.parser import parse as date_parse, ParserError as DateParserError

logger = logging.getLogger(__name__)


def clean_html(html):
    soup = BeautifulSoup(
        html, "html.parser"
    )  # create a new bs4 object from the html data loaded
    for script in soup(
        ["script", "style"]
    ):  # remove all javascript and stylesheet code
        script.extract()
    # get text
    text = soup.get_text()
    # replace non-breaking spaces
    text = text.replace("\xa0", " ")
    # remove zero width space
    text = text.replace("\u200c", "")
    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = "\n".join(chunk for chunk in chunks if chunk)

    return text


def apply_regex(s, reg):
    regex = re.compile(reg)
    matches = regex.search(s)
    if matches and matches.group(1):
        return matches.group(1)
    if matches and matches.group(2):
        return matches.group(2)
    return s  # Fallback if no groups match, or handle appropriately. Original code didn't handle None matches well for group 2 if group 1 failed or matches was None.


def assert_date(datestring):
    try:
        date = date_parse(datestring, fuzzy=True)
        return "date", date.strftime("%m/%d/%Y"), date.date()
    except DateParserError:
        return None


def find_matches_from_pattern(pat, s, pat_type=None, use_regex=False):
    if use_regex:
        logger.debug(f"String to match: {s}")
        logger.debug(f"Pattern: {pat}")
        result = apply_regex(s, pat).strip()
    else:
        # Add safety check for find
        start_i = s.find(pat[0])
        if start_i == -1:
            logger.debug(f"Start pattern '{pat[0]}' not found in string.")
            return ""

        end_i = s[start_i + len(pat[0]) :].find(pat[1]) + start_i + len(pat[0])
        start_i += len(pat[0])

        result = s[start_i:end_i].strip()

    # Truncate the length of the vendor name to no more than 40 chars
    if pat_type == "vendor":
        if len(result) > 40:
            result = result[:40]

    # If the result string is a date, return in standardized date format
    if pat_type == "date":
        date_result = assert_date(result)
        if date_result:
            return date_result[2]
        else:
            # Instead of raising Exception, maybe log error and return None or raise stricter error
            # The original code raised Exception("Not a date type item")
            raise ValueError(f"Failed to parse date from string: {result}")

    # Currency exchange between USD & KRW
    if pat_type == "amount":
        try:
            # Remove commas from thousands separators
            result = float(result.replace(",", ""))

            # Handle Korean currency differently
            if "KRW" in s:
                usd_to_krw_ratio = 1388.88
                result /= usd_to_krw_ratio
                logger.debug(f"Converted KRW to USD. New amount: {result:.2f}")
        except ValueError as e:
            logger.error(f"Failed to parse amount '{result}': {e}")
            return 0.0

    return result
