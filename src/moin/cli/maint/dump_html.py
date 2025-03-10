# Copyright: 2015-2017 MoinMoin:RogerHaase
# Copyright: 2023-2024 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - Creates a static dump of HTML files for each current item in this wiki.

Usage:
    moin dump-html <options>

Options:
    --theme=<theme name>
    --directory=<output directory name>  # name with / means full path, else under moin root directory
    --exclude-ns=<comma separated list of namespaces to exclude>
    --query=<item name or regex to select items>

Defaults:
    --theme=topside_cms
    --directory=<install root dir>HTML
    --exclude-ns=userprofiles

Works best with a CMS-like theme that excludes the wiki navigation links for login, edit,
etc. that are not useful within a static HTML dump.

Most html-formatted files created in the root (HTML) directory will not have names
ending with .html, just as the paths used by the wiki server do not end with .html
(e.g. http://127.0.0.1/Home). All browsers tested follow links to pages not
having .html suffixes without complaint.

Duplicate copies of the home page and index page are created with names ending with .html.

Items with media content types and names ending in common media suffixes (.png, .svg, .mp4...)
will have their raw data, not HTML formatted pages, stored in the root HTML directory. All browsers
tested view HTML formatted pages with names ending in common media suffixes as corrupt files.

The raw data of all items are stored in the +get subdirectory.
"""

import shutil
import re

import click
from flask import g as flaskg
from flask import current_app as app
from flask.cli import FlaskGroup

from pathlib import Path
from urllib.parse import urlparse

from whoosh.query import Every, Term, And, Regex

from werkzeug.exceptions import Forbidden

from xstatic.main import XStatic

from moin.app import create_app, before_wiki, setup_user_anon
from moin.apps.frontend.views import show_item
from moin.constants.keys import CURRENT, NAME_EXACT, WIKINAME, THEME_NAME, LATEST_REVS
from moin.constants.contenttypes import (
    CONTENTTYPE_MEDIA,
    CONTENTTYPE_MEDIA_SUFFIX,
    CONTENTTYPE_OTHER,
    CONTENTTYPE_OTHER_SUFFIX,
)
from moin.items import Item
from moin.storage.middleware.indexing import Revision

from moin import log

logging = log.getLogger(__name__)

PARENT_DIR = "../"


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("dump-html", help="Create a static HTML image of this wiki")
@click.option(
    "--directory",
    "-d",
    type=str,
    required=False,
    default="HTML",
    help="Directory name containing the output files, default HTML",
)
@click.option(
    "--theme",
    "-t",
    required=False,
    default="topside_cms",
    help="Name of theme used in creating output pages, default topside_cms",
)
@click.option(
    "--exclude-ns",
    "-e",
    required=False,
    default="userprofiles",
    help="Comma separated list of excluded namespaces, default userprofiles",
)
@click.option("--query", "-q", required=False, default=None, help="name or regex of items to be included")
@click.option(
    "--convenience-duplicates", required=False, default=False, help="create convenience duplicates of toplevel pages"
)
def Dump(
    directory="HTML",
    theme="topside_cms",
    exclude_ns="userprofiles",
    user=None,
    query=None,
    convenience_duplicates=False,
):
    with app.test_request_context():
        logging.info("Dump html started")
        if theme:
            app.cfg.user_defaults[THEME_NAME] = theme
        exclude_ns = exclude_ns.split(",") if exclude_ns else []

        before_wiki()
        setup_user_anon()

        wiki_root = Path(app.cfg.wikiconfig_dir)
        moinmoin = Path(log.__file__).parent  # log is imported from moin -> this is src/moin
        logging.debug("wiki_root dir: %s, moin src dir: %s", wiki_root, moinmoin)
        if "/" in directory:
            # user has specified complete path to root
            html_root = Path(directory)
        else:
            html_root = Path(wiki_root) / directory

        # override ACLs with permission to read all items
        for _, acls in app.cfg.acl_mapping:
            acls["before"] = "All:read"

        # create an empty output directory after deleting any existing directory
        print(f"Creating output directory {html_root}, starting to copy supporting files")
        if html_root.exists():
            shutil.rmtree(html_root, ignore_errors=False)

        html_root.mkdir(parents=True)

        # create subdirectories and copy static css, icons, images into "static" subdirectory
        shutil.copytree(moinmoin / "static", html_root / "static")
        shutil.copytree(get_wiki_local_dir(), html_root / "+serve" / "wiki_local")

        # copy files from xstatic packaging into "+serve" subdirectory
        pkg = app.cfg.pkg
        xstatic_dirs = ["font_awesome", "jquery", "jquery_tablesorter", "autosize"]
        if theme in ["basic"]:
            xstatic_dirs.append("bootstrap")
        for dir in xstatic_dirs:
            xs = XStatic(getattr(pkg, dir), root_url="/static", provider="local", protocol="http")
            shutil.copytree(xs.base_dir, html_root / "+serve" / dir)

        # copy directories for theme's static files
        if theme == "topside_cms":
            # topside_cms uses topside CSS files
            from_dir = moinmoin / "themes" / "topside" / "static"
        else:
            from_dir = moinmoin / "themes" / theme / "static"
        to_dir = html_root / "_themes" / theme
        shutil.copytree(from_dir, to_dir)

        # convert: <img alt="svg" src="/+get/+7cb364b8ca5d4b7e960a4927c99a2912/svg" />
        # to:      <img alt="svg" src="+get/svg" />
        invalid_src = re.compile(r' [href|src]="/\+get/\+[0-9a-f]{32}/')

        invalid_href = re.compile(r' href="/\+get/\+[0-9a-f]{32}/')

        link_regex = re.compile(r"(href\s*=\s*[\"\']?)([^\"\'\s>]+)([\"\'])")

        # get ready to render and copy individual items
        names: tuple[str, str] = []
        home_page: str | None = None
        get_dir = Path(html_root) / "+get"  # images and other raw data from wiki content
        get_dir.mkdir()

        if query:
            q = And([Term(WIKINAME, app.cfg.interwikiname), Regex(NAME_EXACT, query)])
        else:
            q = Every()

        print("Starting to dump items")
        used_dirs = get_used_dirs(query=q)
        # In the filesystem the item cannot have the same name as the directory.
        # so we append .html to the filename for items in used_dirs.
        for current_rev in app.storage.search(q, limit=None, sortedby=("namespace", "name")):

            if current_rev.namespace in exclude_ns:
                # we usually do not copy userprofiles, no one can login to a static wiki
                continue

            if not current_rev.name:
                # TODO: we skip nameless tickets, but named tickets and comments are processed with ugly names
                continue

            try:
                item_name = current_rev.fqname.fullname
                rendered = show_item(item_name, CURRENT)
            except Forbidden:
                print(f"Failed to dump {current_rev.name}: Forbidden")
                continue
            except KeyError:
                print(f"Failed to dump {current_rev.name}: KeyError")
                continue

            file_name = Path(item_name + ".html")

            if not isinstance(rendered, str):
                print(f"Rendering failed for {file_name} with response {rendered}")
                continue

            # remove item ID from: href="/+get/+7cb364b8ca5d4b7e960a4927c99a2912/example.drawio"
            rendered = re.sub(invalid_href, ' href="/+get/', rendered)

            # remove item ID from: src="/+get/+7cb364b8ca5d4b7e960a4927c99a2912/svg"
            rendered = re.sub(invalid_src, ' src="/+get/', rendered)

            # make internal links target ".html" files
            rendered = re.sub(link_regex, fix_page_link, rendered)

            # make hrefs relative to root folder
            rel_path2root = PARENT_DIR * len(re.findall("/", item_name))
            rendered = rendered.replace('href="/', 'href="' + rel_path2root)
            rendered = rendered.replace('src="/static/', 'src="' + rel_path2root + "static/")
            rendered = rendered.replace('src="/+serve/', 'src="+serve/')
            rendered = rendered.replace('href="+index/"', 'href="+index"')  # trailing slash changes relative position

            # TODO: fix basic theme
            rendered = rendered.replace('<a href="">', f'<a href="{app.cfg.default_root}">')

            # correct links inside document
            for node in used_dirs:
                node_href = f'href="{rel_path2root}{node}"'
                rendered = rendered.replace(node_href, node_href[:-1] + '.html"')

            item = app.storage[current_rev.fqname.fullname]
            rev = item[CURRENT]

            # copy raw data for all items to output /+get directory;
            # images are required, text items are of marginal/no benefit
            create_raw_data_file(get_dir / file_name, rev)

            # save rendered items or raw data to dump directory root
            if is_raw_data_content(item, file_name):
                # do not put a rendered html-formatted file with a name like video.mp4 into root;
                # browsers want raw data
                create_raw_data_file(Path(html_root) / file_name, rev)
            else:
                # extension ".html" is required for browsing html content
                assert file_name.suffix == ".html"
                create_html_file(Path(html_root) / file_name, rendered)

            # save item_name for the index generation
            names.append((item_name, str(file_name)))

            if current_rev.fqname.fullname == app.cfg.default_root:
                if convenience_duplicates:
                    # make duplicates of home page that are easy to find in directory list and open with a click
                    for target in [(current_rev.name + ".html"), ("_" + current_rev.name + ".html")]:
                        create_html_file(html_root / target, rendered)
                # save a copy for creation of index page
                home_page = rendered

        create_index_page(home_page, theme, names, html_root, app.cfg.default_root)

        logging.info("Dump html complete")


def is_raw_data_content(item: Item, filename: Path) -> bool:
    contenttype = item.meta["contenttype"].split(";")[0]
    return contenttype in (CONTENTTYPE_MEDIA + CONTENTTYPE_OTHER) and filename.suffix in (
        CONTENTTYPE_MEDIA_SUFFIX + CONTENTTYPE_OTHER_SUFFIX
    )


def get_wiki_local_dir() -> Path:
    return Path(app.cfg.serve_files["wiki_local"])


def is_page_url(url: str):
    if url.startswith("#"):
        return False
    if url.startswith("/+"):
        return False
    if url.startswith("/_"):
        return False
    if url.startswith("/static/"):
        return False
    parsed = urlparse(url)
    if parsed.scheme:
        return False
    return True


def fix_page_link(m):
    target = m.group(2)
    return m.group(1) + m.group(2) + (".html" if is_page_url(target) else "") + m.group(3)


def get_used_dirs(query):
    """
    get a list of item_names which have subitems (nodes in a tree)
    """
    item = Item.create()  # gives toplevel index
    revs = flaskg.storage.search_meta(query, idx_name=LATEST_REVS, limit=None)
    dirs, files = item.make_flat_index(revs, True)
    # get intersection of dirs and files: items that have subitems
    used_dir_fullnames = {x.fullname for x in dirs} & {x.fullname for x in files}
    used_dirs = set()
    for file_ in used_dir_fullnames:
        if file_.namespace:
            used_dirs.add("/".join((file_.namespace, file_.value)))
        else:
            used_dirs.add(file_.value)
    logging.debug("used_dirs: %s", str(used_dirs))
    return used_dirs


def create_raw_data_file(filename: Path, rev: Revision):
    filename.parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "wb") as f:
        rev.data.seek(0)
        shutil.copyfileobj(rev.data, f)
        try:
            print(f"Saved file named {filename} as raw data")
        except UnicodeEncodeError:
            print("Saved file named {} as raw data".format(filename.encode("ascii", errors="replace")))


def create_html_file(filename: Path, content):
    filename.parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "wb") as f:
        f.write(content.encode("utf8"))
        try:
            print(f"Saved file named {filename}")
        except UnicodeEncodeError:
            print("Saved file named {}".format(filename.encode("ascii", errors="replace")))


def create_index_page(home_page: str, theme: str, names: list[tuple[str, str]], html_root: Path, wiki_root: Path):
    if not home_page:
        print(
            'Error: index pages not created because no home page exists, expected an item named "{}".'.format(wiki_root)
        )
        return

    # create an index page by replacing the content of the home page with a list of items
    # work around differences in basic and modernized theme layout
    # TODO: this is likely to break as new themes are added
    if theme == "basic":
        start = '<div class="moin-content" role="main">'  # basic
        end = '<footer class="navbar moin-footer">'
        div_end = "</div>"
    else:
        start = '<div id="moin-content">'  # modernized , topside, topside cms
        end = '<footer id="moin-footer">'
        div_end = "</div></div>"

    # build a page named "+index" containing links to all wiki items
    links = []
    names.sort(key=lambda item: item[0])
    for name in names:
        links.append(f'<li><a href="{name[1]}">{name[0]}</a></li>')
    name_links = "<h1>Index</h1><ul>{0}</ul>".format("\n".join(links))

    try:
        part1 = home_page.split(start)[0]
        part2 = home_page.split(end)[1]
        page = part1 + start + name_links + div_end + end + part2
    except IndexError:
        page = home_page
        print(f"Error: failed to find {end} in item named {wiki_root}")

    for target in ["+index", "index.html"]:
        with open(html_root / target, "wb") as f:
            f.write(page.encode("utf8"))
