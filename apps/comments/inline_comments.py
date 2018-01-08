
import re
import bson

from flask import current_app as app

from .user_mentions import notify_mentioned_users


# client is using @[display name](type:id)
USER_MENTIONS_REGEX = re.compile('@\[([^]]+)\]\(user:([a-f0-9]{24})\)')


def handle_inline_mentions(sender, updates, original):
    """Listen to item_update signal and send notifications to new inline user mentions."""
    updated = original.copy()
    updated.update(updates)
    comments = _get_inline_comments(updates)
    for comment in comments:
        if not comment.get('notified'):
            users = _get_mentioned_users(comment)
            if users:
                notify_mentioned_users([{
                    '_id': '',
                    'item': original.get('_id'),
                    'text': _format_comment_text(comment),
                    'mentioned_users': {user: bson.ObjectId(user) for user in users},
                }], app.config.get('CLIENT_URL', ''), item=updated)
            comment['notified'] = True


def _get_mentioned_users(comment):
    return [group[1] for group in USER_MENTIONS_REGEX.findall(comment.get('msg', ''))]


def _format_comment_text(comment):
    def repl(match):
        return match.group(1)
    return USER_MENTIONS_REGEX.sub(repl, comment.get('msg', ''))


def _get_inline_comments(updates):
    try:
        comments = []
        data = updates['editor_state'][0]['blocks'][0]['data']
        for val in data.values():
            if val.get('type') == 'COMMENT':
                comments.append(val)
                for reply in val.get('replies', []):
                    comments.append(reply)
        return comments
    except (KeyError, IndexError):
        return []
