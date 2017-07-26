from __future__ import unicode_literals
import json
import re
import requests
import os
import errno
import youtube_dl as dl


#### Control Parameters ####
API_KEY = ' '       # Google API key for Youtube API v3
API_BASE_URL = 'https://www.googleapis.com/youtube/v3/'
VIDEO_BASE_URL = 'https://www.youtube.com/watch?v='
VERBOSE = True
JSON_VERBOSE_CHANNEL = False
JSON_VERBOSE_CHANNELVIDEO = False
RECURSIONMAX = 999


#### Tuning Parameters ####
C_RELEVANCELANGUAGE = 'en'
C_REGIONCODE = 'US'

V_DURATION = 'short'
V_MAXDURATION = 120
V_PUBLISHEDAFTER = '2016-01-01T00:00:00Z'
V_RELEVANCELANGUAGE = 'en'
V_REGIONCODE = 'US'


#### HELPER FUNCTIONS ####

def submitQuery(base_url, url_addon, params_raw, nextPageToken):
    """
    Submits a query and reads a response

    Returns:
    json object
    """
    if nextPageToken is not None:
        params_raw.append(('nextPageToken', nextPageToken))

    response = requests.get(base_url + url_addon, params_raw)

    if VERBOSE:
        print 'Full Request: ' + response.url
        print 'Response Status Code: ' + str(response.status_code)

    return response.json()


def make_directory(path):
    """
    Creates directory if it does not already exist

    Arguments:
    path -- directory path name

    Returns:
    None
    """
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


#### CHANNEL FUNCTIONS ####

def searchChannel(query, channelMax, nextPageToken=None, recur=0, count=0):
    """
    Queries for desired channel of target brand

    Arguments:
    query -- query string
    channelMax -- maximum number of channel results wanted

    Returns:
    List of channel json objects
    """
    if recur >= RECURSIONMAX:
        print 'warning: recursion limit reached'

    if count >= channelMax:
        return []

    if channelMax > 50:
        maxResults = 50
    else:
        maxResults = channelMax

    params_raw = [('part', 'snippet'),
                  ('type', 'channel'),
                  ('q', query),
                  ('relevanceLanguage', C_RELEVANCELANGUAGE),
                  ('regionCode', C_REGIONCODE),
                  ('order', 'relevance'),
                  ('maxResults', maxResults),
                  ('key', API_KEY)]
    page = submitQuery(API_BASE_URL, 'search', params_raw, nextPageToken)

    result = page.get('items')
    if (result is None) or (len(result) == 0):
        return []

    if page.get('nextPageToken'):
        result.extend(searchChannel(query, channelMax, page['nextPageToken'], recur + 1, count + maxResults))

    result_detailed = []
    for channel in result:
        result_detailed.append(getChannelSnippet(query, channel))

    if JSON_VERBOSE_CHANNEL:
        print json.dumps(result_detailed[0: channelMax], indent=4, sort_keys=True)

    return result_detailed[0: channelMax]


def getChannelSnippet(query, channel):
    """
    Gives channel details

    Arguments:
    query -- query string
    channel -- JSON object representing channel

    Returns:
    Channel details
    """
    return {'query': query,
            'channelId': channel['snippet']['channelId'],
            'channelTitle': channel['snippet']['channelTitle'],
            'description': channel['snippet']['description'],
            'publishedAt': channel['snippet']['publishedAt']}


def isOfficialChannel(channel):
    """
    Determines whether channel is official

    Arguments:
    channel -- channel object identical to output of searchChannel

    Returns:
    Boolean representing official or not
    """
    if 'official' in channel['description']:
        return True
    return False


def robustQuery(q):
    """
    Makes query string more robust

    Arguments:
    q -- query string

    Returns:
    Extended query string
    """
    return q + ' official'


def channelBatchPick(query, batchSize):
    """
    Searches for a batch of channels based on query string and picks
    the best match

    Arguments:
    query -- query string
    batchSize -- number of channels to analyze

    Returns:
    Chosen channel object
    """
    candidates = searchChannel(query, batchSize)
    if len(candidates) == 0:
        print 'channelBatchPick: no channel match found -> ' + query
        return None

    for c in candidates:
        if isOfficialChannel(c):
            return c
    return candidates[0]


#### VIDEO FUNCTIONS ####

def searchChannelVideo(channelId, ch_videoMax, nextPageToken=None, recur=0, count=0):
    """
    Targets desired video from a channel

    Returns:
    List of video json objects identical to a typical youtube video resource
    with an extra videoId
    """
    if recur >= RECURSIONMAX:
        print 'warning: recursion limit reached'

    if count >= ch_videoMax:
        return []

    if ch_videoMax > 50:
        maxResults = 50
    else:
        maxResults = ch_videoMax

    params_raw = [('part', 'snippet'),
                  ('channelId', channelId),
                  ('type', 'video'),
                  ('videoDuration', V_DURATION),
                  ('publishedAfter', V_PUBLISHEDAFTER),
                  ('relevanceLanguage', V_RELEVANCELANGUAGE),
                  ('regionCode', V_REGIONCODE),
                  ('order', 'relevance'),
                  ('maxResults', maxResults),
                  ('key', API_KEY)]
    page = submitQuery(API_BASE_URL, 'search', params_raw, nextPageToken)

    result = page.get('items')
    if (result is None) or (len(result) == 0):
        return []

    if page.get('nextPageToken'):
        result.extend(searchChannelVideo(channelId, ch_videoMax, page['nextPageToken'], recur + 1, count + maxResults))

    result = map(getVideoDetail, result)
    result = filterVideo(result)
    if JSON_VERBOSE_CHANNELVIDEO:
        print json.dumps(result[0: ch_videoMax], indent=4, sort_keys=True)

    return result[0: min(ch_videoMax, len(result))]


def getVideoDetail(video):
    """
    Gives video details

    Arguments:
    video -- video json object with ['id']['videoId']

    Returns:
    Very detailed video json object indentical to Youtube API v3
    """
    params_raw = [('part', 'snippet,contentDetails,statistics'),
                  ('id', video['id']['videoId']),
                  ('key', API_KEY)]
    page = submitQuery(API_BASE_URL, 'videos', params_raw, None)

    result = page.get('items')
    if (result is None) or (len(result) == 0):
        return []

    return {'videoId': video['id']['videoId'],
            'snippet': result[0]['snippet'],
            'contentDetails': result[0]['contentDetails'],
            'statistics': result[0]['statistics'],
            'videoUrl': VIDEO_BASE_URL + video['id']['videoId']}


def filterVideo(vid_list):
    """
    Filters results of getChannelVideo
    """
    output = []
    for video in vid_list:
        if parseDuration(video['contentDetails']['duration']) < V_MAXDURATION:
            output.append(video)

    return output


def parseDuration(duration):
    """
    Parses video duration encoded in ISO 8601 format

    Arguments:
    duration -- duration in ISO 8601 format

    Returns:
    duration in seconds
    """
    r = re.findall(r'\d+', duration)
    if len(r) == 1:
        return int(r[0])

    if len(r) == 2:
        return (int(r[0]) * 60) + int(r[1])


#### VIDEO DOWNLOAD ####

def vid_download(video, dl_location, audio_only):
    """
    Downloads video or audio only if specified

    Arguments:
    video -- video JSON object
    dl_location -- folder to place download
    audio_only -- Boolean indicating audio download only

    Returns:
    None
    """
    if VERBOSE:
        print 'Downloading video --> ' + video['videoId'] + ' | ' + 'From page --> ' + video['snippet']['channelTitle'] + '-' + video['snippet']['channelId']

    try:
        ydl_opts = {
            'outtmpl': dl_location + '/%(id)s - %(title)s',
            'quiet': True
        }

        if audio_only:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3'
            }]

        source = video['videoUrl']
        with dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([source])

    except BaseException:
        print 'WARNING: Cannot download video --> ' + video['video']['video_id'] + ' from ' + video['page']['page_name']
