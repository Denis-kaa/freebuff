"""app/__init__.py — real_estate_parser application package.

Daily real-estate listing parser + Telegram control bot.
Pipeline: sources → fetch → parse → normalize → validate → dedup → DB upsert.
"""
