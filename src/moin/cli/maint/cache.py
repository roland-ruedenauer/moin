# Copyright: 2023-2024 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

import click

from flask.cli import FlaskGroup
from pathlib import Path

from moin import current_app, log
from moin.app import create_app
from moin.storage.middleware.cache import MetaDataCache

logger = log.getLogger(__name__)


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


def get_wiki_root() -> Path:
    return Path(current_app.cfg.wikiconfig_dir)


def get_cache_path() -> Path:
    wiki_root = get_wiki_root()
    return wiki_root / "wiki" / "cache" / "metadata.db"


@cli.command("cache-create", help="Create the metadata cache")
def create_metadata_cache():
    logger.info(f"creating the metadata cache for wiki instance at {get_wiki_root()}")
    md_cache = MetaDataCache(get_cache_path())
    md_cache.create()


@cli.command("cache-destroy", help="Destroy the metadata cache")
def destroy_metadata_cache():
    logger.info(f"removing the metadata cache of wiki instance at {get_wiki_root()}")
    md_cache = MetaDataCache(get_cache_path())
    md_cache.destroy()


@cli.command("cache-populate", help="Populate the metadata cache")
def populate_metadata_cache():
    logger.info(f"populating the metadata cache of wiki instance at {get_wiki_root()}")
    md_cache = MetaDataCache(get_cache_path())
    for _, backend in current_app.storage.backend.backends.items():
        md_cache.populate(backend)
