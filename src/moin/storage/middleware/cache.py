# Copyright: 2025 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations

import sqlite3

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import TYPE_CHECKING

from moin.constants.contenttypes import CONTENTTYPE_USER
from moin.constants.itemtypes import ITEMTYPE_USERPROFILE
from moin.constants.keys import (
    ACL,
    CONTENTTYPE,
    DATAID,
    ITEMID,
    ITEMTYPE,
    MTIME,
    NAME,
    NAMESPACE,
    PARENTID,
    REV_NUMBER,
    REVID,
    TRASH,
)
from moin.constants.namespaces import NAMESPACE_USERPROFILES
from moin.log import getLogger
from moin.utils import Singleton

if TYPE_CHECKING:
    from moin.storage.backends.stores import Backend


logger = getLogger(__name__)


class MetaDataCache(metaclass=Singleton):

    create_db_script = """
        CREATE TABLE IF NOT EXISTS mdcache(
            revid TEXT NOT NULL PRIMARY KEY,
            dataid TEXT UNIQUE,
            itemid TEXT NOT NULL,
            parentid TEXT,
            rev_number INT NOT NULL,
            mtime INT NOT NULL,
            namespace TEXT NOT NULL,
            name TEXT NOT NULL,
            itemtype TEXT NOT NULL,
            acl TEXT NULL
        ) STRICT;
        CREATE INDEX IF NOT EXISTS ix_mdcache_ns_name ON mdcache (namespace, name);
        CREATE INDEX IF NOT EXISTS ix_mdcache_itemid ON mdcache (itemid);
    """

    drop_db_script = """
        DROP INDEX IF EXISTS ix_mdcache_ns_name;
        DROP INDEX IF EXISTS ix_mdcache_itemid;
        DROP TABLE IF EXISTS mdcache;
    """

    insert_stmt = """
        INSERT INTO mdcache(
            revid,
            dataid,
            itemid,
            parentid,
            rev_number,
            mtime,
            namespace,
            name,
            itemtype,
            acl
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """

    update_stmt = """
        UPDATE mdcache SET
            mtime = ?
        WHERE
            revid = ?
    """

    @dataclass
    class Entry:
        revid: str
        dataid: str | None
        itemid: str
        parentid: str | None
        rev_number: int
        mtime: int
        namespace: str
        name: str
        itemtype: str
        acl: str | None

        @classmethod
        def from_row(cls, row) -> MetaDataCache.Entry:
            return MetaDataCache.Entry(
                revid=row[0],
                dataid=row[1],
                itemid=row[2],
                parentid=row[3],
                rev_number=row[4],
                mtime=row[5],
                namespace=row[6],
                name=row[7],
                itemtype=row[8],
                acl=row[9],
            )

        def to_dict(self):
            return asdict(self)

    def __init__(self, path: Path) -> None:
        self.path = path

    def create(self):
        logger.info(f"creating metadata cache for {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.Connection(self.path) as conn:
            conn.executescript(self.create_db_script)
            conn.commit()

    def destroy(self):
        logger.info(f"deleting metadata cache for {self.path}")
        if not self.path.exists():
            return
        with sqlite3.Connection(self.path) as conn:
            conn.executescript(self.drop_db_script)
            conn.commit()

    @staticmethod
    def get_itemtype(meta):
        if ITEMTYPE in meta:
            return meta[ITEMTYPE]
        if meta[NAMESPACE] == NAMESPACE_USERPROFILES and meta[CONTENTTYPE] == CONTENTTYPE_USER:
            return ITEMTYPE_USERPROFILE
        raise ValueError(f"Cant detect itemtype of metadata: {meta}")

    @staticmethod
    def get_revnumber(meta):
        if REV_NUMBER in meta:
            return meta[REV_NUMBER]
        return 1

    def populate(self, backend: "Backend"):
        if not self.path.exists():
            return

        store = backend.meta_store
        with sqlite3.Connection(self.path) as conn:
            # iterate over the existing metadata entries
            for key in store:
                meta = backend._get_meta(key)
                # skip deleted items
                if TRASH in meta and meta[TRASH]:
                    continue
                # insert item
                logger.info(f"inserting meta: {meta}")
                conn.execute(
                    self.insert_stmt,
                    (
                        meta[REVID],
                        meta[DATAID] if DATAID in meta else None,
                        meta[ITEMID],
                        meta[PARENTID] if PARENTID in meta else None,
                        self.get_revnumber(meta),
                        meta[MTIME],
                        meta[NAMESPACE],
                        meta[NAME][0],
                        self.get_itemtype(meta),
                        meta[ACL] if ACL in meta else None,
                    ),
                )
                conn.commit()

    def insert(self, entry: Entry):
        with sqlite3.Connection(self.path) as conn:
            conn.execute(
                self.insert_stmt,
                (
                    entry.revid,
                    entry.dataid,
                    entry.itemid,
                    entry.parentid,
                    entry.rev_number,
                    entry.mtime,
                    entry.namespace,
                    entry.name,
                    entry.itemtype,
                    entry.acl,
                ),
            )
            conn.commit()

    def update(self, entry: Entry):
        with sqlite3.Connection(self.path) as conn:
            conn.execute(self.update_stmt, (entry.mtime, entry.revid))
            conn.commit()

    def remove(self, revid: str):
        with sqlite3.Connection(self.path) as conn:
            # determine parentid
            cursor = conn.execute("SELECT parentid FROM mdcache WHERE revid = ?", (revid,))
            row = cursor.fetchone()
            parentid = row[0]
            # unlink
            conn.execute("UPDATE mdcache SET parentid = ? WHERE parentid = ?", (parentid, revid))
            # remove revision
            conn.execute("DELETE FROM mdcache WHERE revid = ?", (revid,))
            conn.commit()

    def get(self, revid: str) -> Entry | None:
        entry: MetaDataCache.Entry | None = None
        with sqlite3.Connection(self.path) as conn:
            cursor = conn.execute("SELECT * FROM mdcache WHERE revid = ?", (revid,))
            row = cursor.fetchone()
            if row:
                entry = MetaDataCache.Entry.from_row(row)
        return entry

    def get_by_itemid(self, itemid: str) -> Entry | None:
        entry: MetaDataCache.Entry | None = None
        with sqlite3.Connection(self.path) as conn:
            cursor = conn.execute("SELECT * FROM mdcache WHERE itemid = ? order by mtime desc limit 1", (itemid,))
            row = cursor.fetchone()
            if row:
                entry = MetaDataCache.Entry.from_row(row)
        return entry

    def get_by_name(self, namespace: str, name: str) -> Entry | None:
        entry: MetaDataCache.Entry | None = None
        with sqlite3.Connection(self.path) as conn:
            cursor = conn.execute(
                "SELECT * FROM mdcache WHERE namespace = ? and name = ? order by mtime desc limit 1", (namespace, name)
            )
            row = cursor.fetchone()
            if row:
                entry = MetaDataCache.Entry.from_row(row)
        return entry
