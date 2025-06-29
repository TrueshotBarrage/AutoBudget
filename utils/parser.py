import re
from bs4 import BeautifulSoup
from dateutil.parser import parse as date_parse, ParserError as DateParserError


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
    if matches.group(1):
        return matches.group(1)
    return matches.group(2)


def assert_date(datestring):
    try:
        date = date_parse(datestring, fuzzy=True)
        return "date", date.strftime("%m/%d/%Y"), date.date()
    except DateParserError:
        return None


def find_matches_from_pattern(pat, s, pat_type=None, use_regex=False):
    if use_regex:
        print(s)
        print(f"Pat: {pat}")
        result = apply_regex(s, pat).strip()
    else:
        start_i = s.find(pat[0])
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
            raise Exception("Not a date type item")

    # Currency exchange between USD & KRW
    if pat_type == "amount":
        # Remove commas from thousands separators
        result = float(result.replace(",", ""))

        # Handle Korean currency differently
        if "KRW" in s:
            usd_to_krw_ratio = 1388.88
            result /= usd_to_krw_ratio
            print(f"New amount: {result}")

    return result
