import json
import yt_search_lib as yt

# Main Program

if __name__ == '__main__':
    #### SEARCH PARAMETERS ####
    CH_BATCH_LIMIT = 3
    VIDEO_LIMIT = 10
    QUERY_LIST = []     # Enter list of query requests as strings

    #### DOWNLOAD PARAMETERS ####
    DOWNLOAD_VIDEOS = True
    AUDIO_ONLY = True
    VIDEO_DIRECTORY_NAME = 'video_data'

    open('ch_video.json', 'w').close()
    open('channel_official.json', 'w').close()
    open('channel_to_be_verified.json', 'w').close()
    if DOWNLOAD_VIDEOS:
        yt.make_directory(VIDEO_DIRECTORY_NAME)

    # Channel searching
    channel_official = []
    channel_to_be_verified = []
    for q in QUERY_LIST:
        channel = yt.channelBatchPick(yt.robustQuery(q), CH_BATCH_LIMIT)
        if channel is None:
            continue

        if yt.isOfficialChannel(channel):
            channel_official.append(channel)
        else:
            channel_to_be_verified.append(channel)

    with open('channel_official.json', 'a') as outfile:
        json.dump(channel_official, outfile, indent=4, sort_keys=True)

    with open('channel_to_be_verified.json', 'a') as outfile:
        json.dump(channel_to_be_verified, outfile, indent=4, sort_keys=True)

    video_valid = []
    for ch_o in channel_official:
        ch_o = yt.searchChannelVideo(channel['channelId'], VIDEO_LIMIT)
        video_valid.extend(ch_o)

    # Video Searching
    with open('ch_video.json', 'a') as outfile:
        json.dump(video_valid, outfile, indent=4, sort_keys=True)
        print 'Found ' + str(len(video_valid)) + ' related resources.'

    if DOWNLOAD_VIDEOS:
        for video in video_valid:
            channel = video['snippet']['channelTitle'] + '-' + video['snippet']['channelId']
            yt.vid_download(video, VIDEO_DIRECTORY_NAME + '/' + channel, audio_only=AUDIO_ONLY)
