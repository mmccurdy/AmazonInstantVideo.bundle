#   Copyright 2012-2013 Josh Kearney
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import account


c = SharedCodeService.constants


def Start():
    ObjectContainer.title1 = c.PLUGIN_TITLE
    ObjectContainer.art = R(c.PLUGIN_ART)

    DirectoryObject.thumb = R(c.PLUGIN_ICON_DEFAULT)
    VideoClipObject.thumb = R(c.PLUGIN_ICON_DEFAULT)
    InputDirectoryObject.thumb = R(c.PLUGIN_ICON_SEARCH)
    PrefsObject.thumb = R(c.PLUGIN_ICON_PREFS)
    NextPageObject.thumb = R(c.PLUGIN_ICON_NEXT)


@handler("/video/amazoninstantvideo", c.PLUGIN_TITLE, thumb=c.PLUGIN_ICON_DEFAULT, art=c.PLUGIN_ART)
def MainMenu():
    logged_in = account.authenticate()
    is_prime = account.is_prime()

    oc = ObjectContainer()

    if logged_in:
        if is_prime:
            oc.add(DirectoryObject(key=Callback(BrowseMenu, video_type="movies"), title="Browse Movies"))
            oc.add(DirectoryObject(key=Callback(BrowseMenu, video_type="tv"), title="Browse TV"))

        oc.add(DirectoryObject(key=Callback(LibraryMenu), title="Your Library"))

        if is_prime:
            oc.add(DirectoryObject(key=Callback(WatchlistMenu), title="Your Watchlist"))
            oc.add(DirectoryObject(key=Callback(SearchMenu), title="Search", thumb=R(c.PLUGIN_ICON_SEARCH)))

    oc.add(PrefsObject(title="Preferences"))

    return oc


@route("/video/amazoninstantvideo/librarymenu")
def LibraryMenu():
    oc = ObjectContainer(title2="Your Library")

    oc.add(DirectoryObject(key=Callback(BrowseMenu, video_type="movies", is_library=True), title="Movies"))
    oc.add(DirectoryObject(key=Callback(BrowseMenu, video_type="tv", is_library=True), title="TV"))

    return oc


@route("/video/amazoninstantvideo/watchlistmenu")
def WatchlistMenu():
    oc = ObjectContainer(title2="Your Watchlist")

    oc.add(DirectoryObject(key=Callback(BrowseMenu, video_type="movies", is_watchlist=True), title="Movies"))
    oc.add(DirectoryObject(key=Callback(BrowseMenu, video_type="tv", is_watchlist=True), title="TV"))

    return oc


@route("/video/amazoninstantvideo/searchmenu")
def SearchMenu():
    oc = ObjectContainer(title2="Search")

    oc.add(InputDirectoryObject(key=Callback(Search, video_type="movies"), title="Search Movies", prompt="Search for a Movie"))
    oc.add(InputDirectoryObject(key=Callback(Search, video_type="tv"), title="Search TV", prompt="Search for a TV show"))

    return oc


@route("/video/amazoninstantvideo/browsemenu", is_library=bool, is_watchlist=bool)
def BrowseMenu(video_type, is_library=False, is_watchlist=False, query=None, pagination_url=None):
    title = "Browse TV Shows" if video_type == "tv" else "Browse Movies"

    if query:
        if not pagination_url:
            # NOTE(jk0): Only build a query URL if we're performing a new
            # search and not using pagination on a previous search.
            query = query.replace(" ", "%20")
            browse_url = c.SEARCH_URL % query
    elif is_library:
        title = title + " (Library)"
        browse_url = c.ACCOUNT_URL % ("library", video_type)
    elif is_watchlist:
        title = title + " (Watchlist)"
        browse_url = c.ACCOUNT_URL % ("watchlist", video_type)
    elif video_type == "movies":
        browse_url = c.MOVIES_URL
    else:
        browse_url = c.TV_URL

    if pagination_url:
        browse_url = c.AMAZON_URL + pagination_url

    html = HTML.ElementFromURL(browse_url)
    videos = html.xpath(c.BROWSE_PATTERN)

    oc = ObjectContainer(title2=title)

    for item in videos:
        is_prime = True if len(item.xpath(c.IS_PRIME_PATTERN)) > 0 else False
        if is_watchlist and not is_prime:
            continue

        # NOTE(danielpunkass): We wrap the pattern matchers with try to avoid
        # total failure if one attribute is not found for an item.
        asin = ""
        title = ""
        image_link = ""
        try:
            asin = item.xpath(c.ASIN_PATTERN)[0]
            title = item.xpath(c.TITLE_PATTERN)[0].strip()
            image_link = item.xpath(c.IMAGE_LINK_PATTERN)[0]
        except IndexError:
            pass

        thumb = Resource.ContentsOfURLWithFallback(url=image_link, fallback=c.PLUGIN_ICON_DEFAULT)

        if video_type == "movies":
            url = c.MINI_PLAYER_URL % asin
            oc.add(MovieObject(url=url, title=title, thumb=thumb))
        else:
            oc.add(SeasonObject(key=Callback(TVSeason, asin=asin, title=title, thumb=thumb, is_library=is_library), rating_key=asin, title=title, thumb=thumb))

    pagination_url = html.xpath(c.PAGINATION_PATTERN)
    if len(pagination_url) > 0:
        oc.add(NextPageObject(key=Callback(BrowseMenu, video_type=video_type, query=query, pagination_url=pagination_url[0]), title="Next..."))

    if len(oc) == 0:
        return ObjectContainer(header="No Results", message="No results were found.")

    return oc


@route("/video/amazoninstantvideo/search")
def Search(query, video_type):
    return BrowseMenu(video_type=video_type, query=query)


@route("/video/amazoninstantvideo/tvseason", is_library=bool)
def TVSeason(asin, title, thumb, is_library):
    html = HTML.ElementFromURL(c.PRODUCT_URL % asin)
    episodes = html.xpath(c.EPISODE_BROWSE_PATTERN)

    oc = ObjectContainer(title2=title)

    for episode in episodes:
        is_owned = True if episode.xpath(c.IS_OWNED_PATTERN)[0].strip() == "Owned" else False

        if not is_library or is_owned:
            asin = episode.xpath(c.EPISODE_ASIN_PATTERN)[0]
            title = episode.xpath(c.EPISODE_TITLE_PATTERN)[0].strip()
            summary = episode.xpath(c.EPISODE_SUMMARY_PATTERN)[0].strip()

            url = c.MINI_PLAYER_URL % asin

            oc.add(EpisodeObject(url=url, title=title, summary=summary, thumb=thumb))

    return oc
