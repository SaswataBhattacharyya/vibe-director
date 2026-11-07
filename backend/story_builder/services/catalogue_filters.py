"""Validated metadata filters applied before catalogue pagination."""
from datetime import date, datetime


def content_indexed(record):
    index = record.get('semantic_content_index') or {}
    return (isinstance(index, dict) and bool(record.get('sha256'))
            and index.get('source_sha256') == record.get('sha256')
            and bool(index.get('model')) and type(index.get('dimension')) is int
            and index['dimension'] > 0)


class CatalogueFilters:
    def __init__(self, *, audio_category='', content_index='', role='', created_after='', created_before=''):
        if audio_category not in {'', 'voice', 'dialogue', 'sfx', 'music'}:
            raise ValueError('Choose a supported audio category.')
        if content_index not in {'', 'indexed', 'unindexed'}:
            raise ValueError('Choose a supported content index filter.')
        if not isinstance(role, str) or len(role) > 80:
            raise ValueError('Invalid media role filter.')
        self.audio_category, self.content_index, self.role = audio_category, content_index, role
        try:
            self.after = date.fromisoformat(created_after) if created_after else None
            self.before = date.fromisoformat(created_before) if created_before else None
        except (ValueError, TypeError):
            raise ValueError('Use YYYY-MM-DD dates for the media filter.') from None
        if self.after and self.before and self.after > self.before:
            raise ValueError('The start date must precede the end date.')

    def matches(self, record):
        if self.audio_category and (record.get('kind') != 'audio' or record.get('audio_category') != self.audio_category):
            return False
        if self.role and self.role not in (record.get('roles') or []):
            return False
        if self.content_index and content_indexed(record) != (self.content_index == 'indexed'):
            return False
        if self.after or self.before:
            try:
                created = datetime.fromisoformat(record.get('created_at', '').replace('Z', '+00:00')).date()
            except (ValueError, TypeError, AttributeError):
                return False
            if (self.after and created < self.after) or (self.before and created > self.before):
                return False
        return True
