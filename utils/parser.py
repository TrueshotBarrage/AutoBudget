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


def assert_date(datestring):
    try:
        date = date_parse(datestring, fuzzy=True)
        return "date", date.strftime("%m/%d/%Y"), date.date()
    except DateParserError:
        return None


def find_matches_from_pattern(pat, s, pat_type=None):
    start_i = s.find(pat[0])
    end_i = s[start_i:].find(pat[1]) + start_i
    start_i += len(pat[0])

    result = s[start_i:end_i].strip()

    # If the result string is a date, return in standardized date format
    if pat_type == "date":
        date_result = assert_date(result)
        if date_result:
            return date_result[2]
        else:
            raise Exception("Not a date type item")

    return result
