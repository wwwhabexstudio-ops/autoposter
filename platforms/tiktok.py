"""TikTok Content Posting API adapter boundary.

Posting remains disabled until the app has the required TikTok product/scopes
and approval. This module intentionally does not implement browser automation.
"""


def configured() -> bool:
    return False
