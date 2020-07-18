import praw


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

    lim = 1000
    sub = "AmITheAsshole"
    return reddit.subreddit(sub).top(limit=lim)
