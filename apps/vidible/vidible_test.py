
import unittest
import requests_mock

from .vidible import get_vidible_metadata


VIDIBLE_TEXT = """
(function () {
    _(
        {"status":{"code":"OK"},"jsVersion":"17.16.1039","id":"56bb474de4b0568f54a23ed7","wlcid":"538612f0e4b00fbb8e898655","bid":{"id":"56bb4724e4b05485f65670bd","videos":[{"videoId":"56bb4688e4b0b6448ed479dd","name":"Watch CCTV of incident in Romford McDonald's","videoUrls":["http://videos.vidible.tv/prod/2016-02/10/56bb4688e4b0b6448ed479dd_640x360_v1.mp4?oxdeb1EtQ4XC5ta_uM6pLRuyXdX_A09cVu_Uw9iwA_RUnZxrbI4ZKDeWOI4gLiPm","http://videos.vidible.tv/prod/2016-02/10/56bb4688e4b0b6448ed479dd_640x360_v1.ogg?Eqi5v8YcCAlqziP1mA8VPrXfta1eyHkhT46B7tdG5yzmOkoalIkvBMwy-52CWvAS"],"thumbnailId":"56bb46b4e4b0ba78d5744c69","thumbnail":"http://cdn.vidible.tv/prod/2016-02/10/56bb4688e4b0b6448ed479dd_60x60_A_v1.jpg","fullsizeThumbnail":"http://cdn.vidible.tv/prod/2016-02/10/56bb4688e4b0b6448ed479dd_1024x576_A_v1.jpg","subtitles":[],"captions":{},"metadata":{"duration":24000,"videoType":"VOD","commonRating":{"value":"G","descriptors":[],"minAge":0}},"videoSourceType":"FILE","iabCategories":[],"studioName":"Press Association","cuePoints":[],"cs":{"priority":false}}]},"playerTemplate":{"initialization":"click","mobileInit":"CLICK","mobileAutoplayWifiOnly":true,"fullscreenOnUnmute":false,"previewPoster":"IMAGE","sound":"normal","initialVolume":0.5,"videosToPlay":1,"videosToRequest":1,"shuffleVideos":false,"prerollFrequency":0,"backgroundSkinLocation":{"x":0,"y":0,"w":0,"h":0},"controlsSkin":"http://cdn.vidible.tv/prod/player/swf/17.06.342/ControlsAOL_5.swf","controlsSkinLocation":{"x":0,"y":0,"w":640,"h":360},"videoLocation":{"x":0,"y":0,"w":640,"h":360},"afterVideosUI":"next","scrubBarSkin":"http://cdn.vidible.tv/prod/2013-03/10/511e8160e4b0bf40bd0340a7_v2.swf","coveringsSkinLocation":{"x":0,"y":0,"w":640,"h":360},"surroundSkinLocation":{"x":0,"y":0,"w":0,"h":0},"playerWidth":640,"playerHeight":360,"controlsAutoPosition":true,"controlsChromeless":true,"controlsBackgroundAlpha":"1.0","controlsConfig":{"colorSchema":{"mainColor":{"backgroundAlpha":1.0}}},"nielsenSiteCampaign":"nlsn31325","nielsenChannelCampaign":"cmp185270","backgroundFill":true,"backgroundColor":0,"surround3DBevelShadowColor":16777215,"surround3DBevelHighlightColor":16777215,"surroundInnerRadius":0,"surroundCornerRadius":0,"surroundHole":false,"surround3D":false,"surround3DBevelSize":0,"surround3DBevelStrength":0.0,"publisherPayout":"None","publisherAmount":0.0,"metaData":{},"showLogo":false,"autoplayInView":0,"vrRenderer":"O2","isResponsive":false,"csid":"54ef07a8e4b020e2f828c02c","HLSExtra":"http://cdn.vidible.tv/prod/player/swf/17.06.342/hls-plugin.swf","IMAExtra":"http://cdn.vidible.tv/prod/player/swf/17.06.342/ima-ad-module.swf","YuMeExtra":"http://cdn.vidible.tv/prod/player/swf/17.06.342/yume-ad-module.swf","FreeWheelExtra":"http://cdn.vidible.tv/prod/player/swf/17.06.342/free-wheel-module.swf","VASTExtra":"http://cdn.vidible.tv/prod/player/swf/17.06.342/vast-ad-engine.swf","PlayerAdSystem":"http://cdn.vidible.tv/prod/player/swf/17.06.342/vidible-ad-server.swf","UIExtra":"http://cdn.vidible.tv/prod/player/swf/17.06.342/controls-sticky.swf","AgeGateExtra":"http://cdn.vidible.tv/prod/player/swf/17.06.342/age-gate.swf","SubtitlesExtra":"http://cdn.vidible.tv/prod/player/swf/17.06.342/subtitles.swf","ClickExtra":"http://cdn.vidible.tv/prod/player/swf/17.06.342/click-throughs.swf"},"timestamp":"20170623114355688","adSettings":{"podSize":1,"prerollInterleave":1,"strictSiteCheckForAds":false,"blockContentOnAdBlocker":false,"domainOptimisation":true,"adStrategy":"ADSET_BASED","useSsai":false,"companions":[],"aeg":[],"asids":[]},"playerWidget":{"playerType":"SMART","url":"http://cdn.vidible.tv/prod/player/swf/17.06.342/player-vast.swf","adOnly":false,"isAol":false},"geo":{"country":"cze","region":"10","zipCode":"100 00","areaCode":"0","connSpeed":"broadband"},"brandedContent":false,"sid":"97c459e9-d2da-495f-a537-edd01812dd3c","bsf":{"bs":{},"f":{"o2":0.0}}}
    );
    function _(json) {
    }
})()
"""  # noqa

SEARCH_TEXT = """
[{"id":"56bb4688e4b0b6448ed479dd","title":"Watch CCTV of incident in Romford McDonald's","description":"Detectives from Havering Borough investigating an attempted robbery at a McDonalds restaurant have issued CCTV footage of three men they wish to speak to in connection with the incident.","thumbnail":"http://img.vidible.tv/prod/2016-02/10/56bb4688e4b0b6448ed479dd_o_A_v1.jpg","url":"http://delivery.vidible.tv/video/redirect/56bb4688e4b0b6448ed479dd?bcid=538612f0e4b00fbb8e898655&w=640&h=360","size":2004079,"creationDate":1455113864099,"company":"Press Association","duration":24000,"width":640,"height":360,"mimeType":"video/ogg","modificationDate":1462876434275,"media":{},"plays":0,"companyId":"538612f0e4b00fbb8e898655","geoRestriction":{"whiteList":[],"blackList":[],"blackListMode":false},"deviceRestriction":{"whiteList":[],"blackListMode":false},"shortDescription":"Detectives from Havering Borough investigating an attempted robbery at a McDonalds restaurant have issued CCTV footage of three men they wish to speak to in connection with the incident."}]
"""  # noqa


class VidibleTestCase(unittest.TestCase):

    def test_get_vidible_metadata(self):
        pid = '56bb474de4b0568f54a23ed7'
        vid = '56bb4688e4b0b6448ed479dd'
        bcid = '538612f0e4b00fbb8e898655'
        with requests_mock.mock() as mock:
            mock.get('http://delivery.vidible.tv/jsonp/pid={pid}/{bcid}.js'.format(pid=pid, bcid=bcid),
                     text=VIDIBLE_TEXT)
            mock.get('http://api.vidible.tv/search?bcid={bcid}&query={video_id}'.format(video_id=vid, bcid=bcid),
                     text=SEARCH_TEXT)
            meta = get_vidible_metadata(bcid=bcid, pid=pid)
        assert(type(meta) is dict)
        assert(type(meta['height']) is int)
        assert(type(meta['width']) is int)
        assert(meta['mimeType'])
        assert(meta['url'])
        assert(meta['thumbnail'])
