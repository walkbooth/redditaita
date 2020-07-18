import sys
import re
from pprint import pprint
import praw
import pandas as pd

personal_pronouns = [
    "I",
    "i",
    "Me",
    "ME",
    "me",
    "My",
    "MY",
    "my",
    "Mine",
    "MINE",
    "mine",
    "Myself",
    "MYSELF",
    "myself",
]

GENDER_PRONOUNS = "MFmf"

gender_pronoun_transform = {
    "M": "Male",
    "F": "Female",
    "m": "Male",
    "f": "Female",
}

age_lowbound = 10
age_highbound = 80

results = {
    "Asshole": {
        "Male": 0,
        "Female": 0,
        "Ages": dict.fromkeys(range(age_lowbound, age_highbound + 1), 0),
    },
    "Not the A-hole": {
        "Male": 0,
        "Female": 0,
        "Ages": dict.fromkeys(range(age_lowbound, age_highbound + 1), 0),
    },
}


def parse_age_and_gender(text: str):

    # Handle text like M22 or F22
    if text[0] in GENDER_PRONOUNS and text[1:].isdecimal():
        return (gender_pronoun_transform[text[0]], int(text[1:]))

    # Handle text like 22F or 22M
    if text[-1] in GENDER_PRONOUNS and text[:-1].isdecimal():
        return (gender_pronoun_transform[text[-1]], int(text[:-1]))

    # If the text fits under neither of these cases, throw an error
    raise ValueError(f"Unable to parse age and gender from {text}")


def readkey(key):
    """
    Read a key from the 'apikeys' directory
    """
    with open(f"secrets/{key}") as stream:
        key_contents = stream.read()
    return key_contents


def get_submissions():
    reddit = praw.Reddit(
        client_id=readkey("client_id"),
        client_secret=readkey("app_secret"),
        user_agent="script:com.example.aita-data:v1.0.0 (by u/anapantaleao and u/wgbooth)",
    )

    return reddit.subreddit("AmITheAsshole").top(limit=1000)


df = pd.DataFrame(columns=["Flair", "Age", "Gender", "Confidence", "Comments", "Text"])

# Put all of below in loop once we get API results
for submission in get_submissions():

    row_data = {}

    # Get flair, and skip submission if it's not a decisive submission
    row_data["Flair"] = submission.link_flair_text
    if row_data["Flair"] not in ("Asshole", "Not the A-hole"):
        continue

    row_data["Text"] = submission.selftext

    # Diagnostics for a submission
    row_data["Confidence"] = 0
    row_data["Comments"] = []

    # Scrape submission content for submitter's age and gender
    result = re.findall(r" ?(\w+) [\[\(]([a-zA-Z0-9]+)[\]\)]", row_data["Text"])
    first_person_matches = [match for match in result if match[0] in personal_pronouns]
    if len(first_person_matches) > 1:
        row_data["Confidence"] -= 1
        row_data["Comments"].append(
            "More than one first person match, using first match"
        )
    elif len(first_person_matches) == 0:
        row_data["Confidence"] -= 2
        row_data["Comments"].append("No first person matches, do not use")
        df = df.append(row_data, ignore_index=True)
        continue

    submitter_info = first_person_matches[0][1]
    try:
        row_data["Gender"], row_data["Age"] = parse_age_and_gender(submitter_info)
    except ValueError as error:
        row_data["Confidence"] -= 2
        row_data["Comments"].append(str(error))
        df = df.append(row_data, ignore_index=True)
        continue

    # Add to results
    try:
        results[row_data["Flair"]]["Ages"][int(row_data["Age"])] += 1
    except KeyError:
        row_data["Confidence"] -= 2
        row_data["Comments"].append(
            f"Submitter is outside the age range {age_lowbound}-{age_highbound}, do not use"
        )
        df = df.append(row_data, ignore_index=True)
        continue

    df = df.append(row_data, ignore_index=True)
    results[row_data["Flair"]][row_data["Gender"]] += 1

with pd.ExcelWriter("output.xlsx") as writer:
    df.to_excel(writer)
