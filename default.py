# *  Credits:
# *
# *  original Artist Slideshow code by ronie
# *  updates and additions since v1.3.0 by pkscout
# *
# *  divingmule for script.image.lastfm.slideshow
# *  grajen3 for script.ImageCacher
# *  sfaxman for smartUnicode
# *
# *  code from all scripts/examples are used in script.artistslideshow
# *  
# *  Last.fm:      http://www.last.fm/
# *  fanart.tv:    http://www.fanart.tv
# *  theaudiodb:   http://www.theaudiodb.com

try:
    from itertools import izip_longest as _zip_longest
except ImportError:
    from itertools import zip_longest as _zip_longest
import os, random, re, sys, time
import xml.etree.ElementTree as _xmltree
import json as _json
from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs
from kodi_six.utils import py2_encode, py2_decode
from collections import OrderedDict as _ordereddict
from resources.common.fileops import checkPath, writeFile, readFile, deleteFile, deleteFolder, copyFile, moveFile
from resources.common.url import URL
from resources.common.transforms import getImageType, itemHash, itemHashwithPath
from resources.common.xlogger import Logger
from resources.common.kodisettings import getSettingBool, getSettingInt, getSettingNumber, getSettingString
import resources.plugins

addon        = xbmcaddon.Addon()
addonname    = addon.getAddonInfo('id')
addonversion = addon.getAddonInfo('version')
addonpath    = addon.getAddonInfo('path')
addonicon    = xbmc.translatePath('%s/icon.png' % addonpath )
language     = addon.getLocalizedString
preamble     = '[Artist Slideshow]'
logdebug     = getSettingBool( addon, "logging" ) 

lw      = Logger( preamble=preamble, logdebug=logdebug )
JSONURL = URL( 'json' )
txtURL  = URL( 'text' )
imgURL  = URL( 'binary' )

# this section imports all the scraper plugins, initializes, and sorts them
def _get_plugin_settings( preamble, module, description ):
    if module == 'local':
        return 'true', 0
    try:
        active = addon.getSetting( preamble + module )
    except ValueError:
        active = 'false'
    except Exception as e:
        lw.log( ['unexpected error while parsing %s setting for %s' % (description, module), e] )
        active = 'false'        
    if active == 'true':
        try:
            priority = int( addon.getSetting( preamble + "priority_" + module ) )
        except ValueError:
            priority = 10
        except Exception as e:
            lw.log( ['unexpected error while parsing %s priority for %s' % (description, module), e] )
            priority = 10
    else:
        priority = 10
    return active, priority

bio_plugins = {'names':[], 'objs':{}}
image_plugins = {'names':[], 'objs':{}}
album_plugins = {'names':[], 'objs':{}}
similar_plugins = {'names':[], 'objs':{}}
mbid_plugins = {'names':[], 'objs':{}} 
for module in resources.plugins.__all__:
    full_plugin = 'resources.plugins.' + module
    __import__( full_plugin )
    imp_plugin = sys.modules[ full_plugin ]
    lw.log( ['loaded plugin ' + module] )
    plugin = imp_plugin.objectConfig()
    scrapers = plugin.provides()
    if 'bio' in scrapers:
        bio_active, bio_priority = _get_plugin_settings( 'ab_', module, 'artist bio' )
        if bio_active == 'true':
            bio_plugins['objs'][module] = plugin
            bio_plugins['names'].append( [bio_priority, module] )
            lw.log( ['added %s to bio plugins' % module] )
    if 'images' in scrapers:
        img_active, img_priority = _get_plugin_settings( '', module, 'artist images' )
        if img_active == 'true':
            image_plugins['objs'][module] = plugin
            image_plugins['names'].append( [img_priority, module] )
            lw.log( ['added %s to image plugins' % module] )
    if 'albums' in scrapers:
        ai_active, ai_priority = _get_plugin_settings( 'ai_', module, 'artist albums' )
        if ai_active == 'true':
            album_plugins['objs'][module] = plugin
            album_plugins['names'].append( [ai_priority, module] )
            lw.log( ['added %s to album info plugins' % module] )
    if 'similar' in scrapers:
        sa_active, sa_priority = _get_plugin_settings( 'sa_', module, 'similar artists' )
        if sa_active == 'true':
            similar_plugins['objs'][module] = plugin
            similar_plugins['names'].append( [ai_priority, module] )
            lw.log( ['added %s to similar artist plugins' % module] )
    if 'mbid' in scrapers:
        mbid_plugins['objs'][module] = plugin
        mbid_plugins['names'].append( [1, module] )
        lw.log( ['added %s to mbid plugins' % module] )


LANGUAGES = (
# Full Language name[0]         ISO 639-1[1]   Script Language[2]
    ("Albanian"                   , "sq",            "0"  ),
    ("Arabic"                     , "ar",            "1"  ),
    ("Belarusian"                 , "hy",            "2"  ),
    ("Bosnian"                    , "bs",            "3"  ),
    ("Bulgarian"                  , "bg",            "4"  ),
    ("Catalan"                    , "ca",            "5"  ),
    ("Chinese"                    , "zh",            "6"  ),
    ("Croatian"                   , "hr",            "7"  ),
    ("Czech"                      , "cs",            "8"  ),
    ("Danish"                     , "da",            "9"  ),
    ("Dutch"                      , "nl",            "10" ),
    ("English"                    , "en",            "11" ),
    ("Estonian"                   , "et",            "12" ),
    ("Persian"                    , "fa",            "13" ),
    ("Finnish"                    , "fi",            "14" ),
    ("French"                     , "fr",            "15" ),
    ("German"                     , "de",            "16" ),
    ("Greek"                      , "el",            "17" ),
    ("Hebrew"                     , "he",            "18" ),
    ("Hindi"                      , "hi",            "19" ),
    ("Hungarian"                  , "hu",            "20" ),
    ("Icelandic"                  , "is",            "21" ),
    ("Indonesian"                 , "id",            "22" ),
    ("Italian"                    , "it",            "23" ),
    ("Japanese"                   , "ja",            "24" ),
    ("Korean"                     , "ko",            "25" ),
    ("Latvian"                    , "lv",            "26" ),
    ("Lithuanian"                 , "lt",            "27" ),
    ("Macedonian"                 , "mk",            "28" ),
    ("Norwegian"                  , "no",            "29" ),
    ("Polish"                     , "pl",            "30" ),
    ("Portuguese"                 , "pt",            "31" ),
    ("PortugueseBrazil"           , "pb",            "32" ),
    ("Romanian"                   , "ro",            "33" ),
    ("Russian"                    , "ru",            "34" ),
    ("Serbian"                    , "sr",            "35" ),
    ("Slovak"                     , "sk",            "36" ),
    ("Slovenian"                  , "sl",            "37" ),
    ("Spanish"                    , "es",            "38" ),
    ("Swedish"                    , "sv",            "39" ),
    ("Thai"                       , "th",            "40" ),
    ("Turkish"                    , "tr",            "41" ),
    ("Ukrainian"                  , "uk",            "42" ),
    ("Vietnamese"                 , "vi",            "43" ),
    ("Farsi"                      , "fa",            "13" ),
    ("Portuguese (Brazil)"        , "pb",            "32" ),
    ("Portuguese-BR"              , "pb",            "32" ),
    ("Brazilian"                  , "pb",            "32" ) )


class Main( object ):

    def __init__( self ):
        self._parse_argv()
        self._init_window()
        if self._get_infolabel( self.ARTISTSLIDESHOWRUNNING ) == "True" and not self.RUNFROMSETTINGS:
            lw.log( ['script already running'] )
        else:
            self._upgrade_settings()
            self._get_settings()
            self._init_vars()
            self._make_dirs()
            self._upgrade()
            if self._run_from_settings():
                return
            self.LastCacheTrim = 0
            self._set_property("ArtistSlideshowRunning", "True")
            if( xbmc.Player().isPlayingAudio() == False and self._get_infolabel( self.EXTERNALCALL ) == '' ):
                lw.log( ['no music playing'] )
                if( self.DAEMON == "False" ):
                    self._set_property("ArtistSlideshowRunning")
            else:
                lw.log( ['first song started'] )
                time.sleep(1) # it may take some time for Kodi to read the tag info after playback started
                self._use_correct_artwork()
                self._trim_cache()
            while (not xbmc.abortRequested):
                time.sleep(1)
                if self._get_infolabel( self.ARTISTSLIDESHOWRUNNING ) == "True":
                    if( xbmc.Player().isPlayingAudio() == True or self._get_infolabel( self.EXTERNALCALL ) != '' ):
                        if set( self.ALLARTISTS ) != set( self._get_current_artists() ):
                            self._clear_properties()
                            self.UsingFallback = False
                            self._use_correct_artwork()
                            self._trim_cache()
                        elif(not (self.DownloadedAllImages or self.UsingFallback)):
                            if(not (self.LocalImagesFound and self.PRIORITY == 1)):
                                lw.log( ['same artist playing, continue download'] )
                                self._use_correct_artwork()
                    else:
                        time.sleep(2) # doublecheck if playback really stopped
                        if( xbmc.Player().isPlayingAudio() == False and self._get_infolabel( self.EXTERNALCALL ) == '' ):
                            if ( self.DAEMON == "False" ):
                                self._set_property( "ArtistSlideshowRunning" )
                else:
                    self._clear_properties()
                    break
            try:
                self._set_property("ArtistSlideshow.CleanupComplete", "True")
            except Exception as e:
                lw.log( ['unexpected error while setting property.', e] )


    def _clean_dir( self, dir_path ):
        try:
            dirs, old_files = xbmcvfs.listdir( dir_path )
        except Exception as e:
            lw.log( ['unexpected error while getting directory list', e] )
            old_files = []
        for old_file in old_files:
            if not old_file.endswith( '.nfo' ):
                success, loglines = deleteFile( os.path.join(dir_path, old_file) )


    def _clean_text( self, text ):
        text = re.sub('<a [^>]*>|</a>|<span[^>]*>|</span>','',text)
        text = re.sub('&quot;','"',text)
        text = re.sub('&amp;','&',text)
        text = re.sub('&gt;','>',text)
        text = re.sub('&lt;','<',text)
        text = re.sub('User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.','',text)
        text = re.sub('Read more about .* on Last.fm.','',text)
        return text.strip()

    
    def _clear_properties( self ):
        self.MBID = ''
        self.FANARTNUMBER = False
        self._set_property( "ArtistSlideshow", self.INITDIR )
        self._clean_dir( self.MergeDir )
        self._clean_dir( self.TRANSITIONDIR )
        self._set_property( "ArtistSlideshow.ArtistBiography" )
        for count in range( 50 ):
            self._set_property( "ArtistSlideshow.%d.SimilarName" % ( count + 1 ) )
            self._set_property( "ArtistSlideshow.%d.SimilarThumb" % ( count + 1 ) )
            self._set_property( "ArtistSlideshow.%d.AlbumName" % ( count + 1 ) )
            self._set_property( "ArtistSlideshow.%d.AlbumThumb" % ( count + 1 ) )


    def _delete_folder( self, folder ):
        success, loglines = deleteFolder( folder )
        if success:
            lw.log( ['deleted folder ' + folder] )
        else:
            lw.log( loglines )


    def _download( self, src, dst, dst2 ):
        if (not xbmc.abortRequested):
            tmpname = os.path.join( self.DATAROOT, 'temp', src.rsplit('/', 1)[-1] )
            lw.log( ['the tmpname is ' + tmpname] )
            if xbmcvfs.exists( tmpname ):
                success, loglines = deleteFile( tmpname )
                lw.log( loglines )
            success, loglines, urldata = imgURL.Get( src, params=self.params )
            lw.log( loglines )
            if success:
                success, loglines = writeFile( bytearray( urldata ), tmpname )
                lw.log( loglines )
            if not success:
                return False
            if xbmcvfs.Stat( tmpname ).st_size() > 999:
                if not xbmcvfs.exists ( dst ):
                    success, loglines = copyFile( tmpname, dst2 )
                    lw.log( loglines )
                    success, loglines = moveFile( tmpname, dst )
                    lw.log( loglines )
                    return True
                else:
                    lw.log( ['image already exists, deleting temporary file'] )
                    success, loglines = deleteFile( tmpname )
                    lw.log( loglines )
                    return False
            else:
                success, loglines = deleteFile( tmpname )
                lw.log( loglines )
                return False
    

    def _get_artistinfo( self ):
        bio = ''
        bio_params = {}
        bio_params['mbid'] = self.MBID
        bio_params['infodir'] = self.INFODIR
        bio_params['localartistdir'] = os.path.join( self.LOCALARTISTPATH, py2_decode( self.NAME ) )
        bio_params['lang'] = self.LANGUAGE
        bio_params['artist'] = self.NAME
        bio = ''
        try:
            bio_plugins['names'].sort( key=lambda x: x[0] )
        except TypeError:
            pass
        for plugin_name in bio_plugins['names']:
            lw.log( ['checking %s for bio' % plugin_name[1]] )
            bio_params['donated'] = addon.getSetting( plugin_name[1] + "_donated" )
            bio, loglines = bio_plugins['objs'][plugin_name[1]].getBio( bio_params )
            lw.log( loglines )
            if bio:
                lw.log( ['got a bio from %s, so stop looking' % plugin_name] )
                break
        if bio:
            self.biography = self._clean_text(bio)
        else:
            self.biography = ''
        album_params = {}
        album_params['infodir'] = self.INFODIR
        album_params['localartistdir'] = os.path.join( self.LOCALARTISTPATH, py2_decode( self.NAME ) )
        album_params['lang'] = self.LANGUAGE
        album_params['artist'] = self.NAME
        albums = []
        try:
            album_plugins['names'].sort( key=lambda x: x[0] )
        except TypeError:
            pass
        for plugin_name in album_plugins['names']:
            lw.log( ['checking %s for album info' % plugin_name[1]] )
            album_params['donated'] = addon.getSetting( plugin_name[1] + "_donated" )
            albums, loglines = album_plugins['objs'][plugin_name[1]].getAlbumList( album_params )
            lw.log( loglines )
            if not albums == []:
                lw.log( ['got album list from %s, so stop looking' % plugin_name] )
                break
        if albums == []:
            self.albums = []
        else:
            self.albums = albums
        similar_params = {}
        similar_params['infodir'] = self.INFODIR
        similar_params['localartistdir'] = os.path.join( self.LOCALARTISTPATH, py2_decode( self.NAME ) )
        similar_params['lang'] = self.LANGUAGE
        similar_params['artist'] = self.NAME
        similar_artists = []
        try:
            similar_plugins['names'].sort( key=lambda x: x[0] )
        except TypeError:
            pass
        for plugin_name in similar_plugins['names']:
            lw.log( ['checking %s for similar artist info' % plugin_name[1]] )
            similar_artists, loglines = similar_plugins['objs'][plugin_name[1]].getSimilarArtists( similar_params )
            lw.log( loglines )
            if not similar_artists == []:
                lw.log( ['got similar artist list from %s, so stop looking' % plugin_name] )
                break
        if  similar_artists == []:
            self.similar = []
        else:
            self.similar = similar_artists
        self._set_properties()


    def _get_current_artists( self ):
        current_artists = []
        for artist, mbid in self._get_current_artists_info( ):
            current_artists.append( artist )
        return current_artists


    def _get_current_artists_info( self ):
        featured_artists = ''
        artist_names = []
        artists_info = []
        mbids = []
        if( xbmc.Player().isPlayingAudio() == True ):
            try:
                playing_file = xbmc.Player().getPlayingFile()
                # playing_file = xbmc.Player().getPlayingFile() + ' - ' + xbmc.Player().getMusicInfoTag().getArtist() + ' - ' + xbmc.Player().getMusicInfoTag().getTitle()
            except RuntimeError:
                return artists_info
            except Exception as e:
                lw.log( ['unexpected error getting playing file back from Kodi', e] )
                return artists_info
            if playing_file != self.LASTPLAYINGFILE:
                # if the same file is playing, use cached JSON response instead of doing a new query
                response = xbmc.executeJSONRPC ( '{"jsonrpc":"2.0", "method":"Player.GetItem", "params":{"playerid":0, "properties":["artist", "musicbrainzartistid"]},"id":1}' )
                self.LASTPLAYINGFILE = playing_file
            else:
                lw.log( ['same file playing, returning cached artists_info'] )
                return self.ARTISTS_INFO
            artist_names = _json.loads(response).get( 'result', {} ).get( 'item', {} ).get( 'artist', [] )
            mbids = _json.loads(response).get( 'result', {} ).get( 'item', {} ).get( 'musicbrainzartistid', [] )
            try:
                playing_song = xbmc.Player().getMusicInfoTag().getTitle()
            except RuntimeError:
                playing_song = ''
            except Exception as e:
                lw.log( ['unexpected error gettting playing song back from XBMC', e] )
                playing_song = ''
            if not artist_names:
                lw.log( ['No artist names returned from JSON call, assuming this is an internet stream'] )
                try:
                    playingartist = playing_song[0:(playing_song.find('-'))-1]
                except RuntimeError:
                    playingartist = ''
                    playing_song = ''
                except Exception as e:
                    lw.log( ['unexpected error gettting playing song back from Kodi', e] )
                    playingartist = ''
                    playing_song = ''
                artist_names = self._split_artists( playingartist )
            featured_artists = self._get_featured_artists( playing_song )
        elif self._get_infolabel( self.SKININFO['artist'] ):
            artist_names = self._split_artists( self._get_infolabel(self.SKININFO['artist']) )
            mbids = self._get_infolabel( self.SKININFO['mbid'] ).split( ',' )
            featured_artists = self._get_featured_artists( self._get_infolabel(self.SKININFO['title']) )
        if featured_artists:
            for one_artist in featured_artists:
                artist_names.append( one_artist.strip(' ()') )
        lw.log( ['starting with the following artists', artist_names] )
        lw.log( ['disable multi artist is set to ' + str( self.DISABLEMULTIARTIST )] )
        if self.DISABLEMULTIARTIST:
            if len( artist_names ) > 1:
                lw.log( ['deleting extra artists'] )
                del artist_names[1:]
            if len( mbids ) > 1:
                lw.log( ['deleting extra MBIDs'] )
                del mbids[1:]
        lw.log( ['left with', artist_names] )
        for artist_name, mbid in _zip_longest( artist_names, mbids, fillvalue='' ):
            if artist_name:
                artists_info.append( (py2_encode( artist_name ), self._get_musicbrainz_id( py2_encode( artist_name ), mbid )) )
        self.ARTISTS_INFO = artists_info
        return artists_info


    def _get_directory_list( self, trynum='first' ):
        lw.log( ['checking %s for artist images' % self.CACHEDIR] )
        try:
            dirs, files = xbmcvfs.listdir( self.CACHEDIR )
        except OSError:
            files = []
        except Exception as e:
            lw.log( ['unexpected error getting directory list', e] )
            files = []
        if not files and trynum == 'first':
            s_name = self._set_safe_artist_name( self.NAME )
            lw.log( ['did not work with %s, trying %s' % (py2_decode( self.NAME ), s_name)] )           
            self.CACHEDIR = os.path.join( self.LOCALARTISTPATH, s_name, self.FANARTFOLDER )
            files = self._get_directory_list( 'second' )
        return files
        

    def _get_featured_artists( self, data ):
        replace_regex = re.compile( r"ft\.", re.IGNORECASE )
        split_regex = re.compile( r"feat\.", re.IGNORECASE )
        the_split = split_regex.split( replace_regex.sub( 'feat.', data ) )
        if len( the_split ) > 1:
            return self._split_artists( the_split[-1] )
        else:
            return []


    def _get_folder_size( self, start_path ):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk( start_path ):
            for f in filenames:
                fp = os.path.join( dirpath, f )
                total_size += os.path.getsize( fp )
        return total_size


    def _get_image_list( self ):
        images = []
        image_params = {}
        image_params['mbid'] = self._get_musicbrainz_id( self.NAME, self.MBID )
        image_params['lang'] = self.LANGUAGE
        image_params['artist'] = self.NAME
        image_params['infodir'] = self.INFODIR
        for plugin_name in image_plugins['names']:
            image_list = []
            lw.log( ['checking %s for images' % plugin_name[1]] )
            image_params['getall'] = addon.getSetting( plugin_name[1] + "_all" )
            image_params['clientapikey'] = addon.getSetting( plugin_name[1] + "_clientapikey" )
            image_params['donated'] = addon.getSetting( plugin_name[1] + "_donated" )
            image_list, loglines = image_plugins['objs'][plugin_name[1]].getImageList( image_params )
            lw.log( loglines )
            images.extend( image_list )
            image_params['mbid'] = self._get_musicbrainz_id( self.NAME, self.MBID ) 
        return images


    def _get_infolabel( self, item ):
        try:
            infolabel = xbmc.getInfoLabel( item )
        except:
            lw.log( ['problem reading information from %s, returning blank' % item] )
            infolabel = ''
        return infolabel


    def _get_local_images( self ):
        self.LocalImagesFound = False
        if not self.NAME:
            lw.log( ['no artist name provided'] )
            return
        artist_path = os.path.join( self.LOCALARTISTPATH, py2_decode( self.NAME ) )
        self.CACHEDIR = os.path.join( artist_path, self.FANARTFOLDER )
        lw.log( ['cachedir = %s' % self.CACHEDIR] )
        artist_path_exists, loglines = checkPath( os.path.join( artist_path, '' ), False )
        copy_files = []
        if self.INCLUDEFANARTJPG and artist_path_exists:
           copy_files.append( 'fanart.jpg' )
           copy_files.append( 'fanart.png' )
        if self.INCLUDEFOLDERJPG and artist_path_exists:
            copy_files.append( 'folder.jpg' )
            copy_files.append( 'folder.png' )
        for one_file in copy_files:
            result, loglines = checkPath( os.path.join( self.CACHEDIR, '' ) )
            lw.log( loglines )
            success, loglines = copyFile( os.path.join( artist_path, one_file ), os.path.join( self.CACHEDIR, one_file ) )
            lw.log( loglines )
        files = self._get_directory_list()
        for file in files:
            if file.lower().endswith('tbn') or file.lower().endswith('jpg') or file.lower().endswith('jpeg') or file.lower().endswith('gif') or file.lower().endswith('png'):
                self.LocalImagesFound = True
        if self.LocalImagesFound:
            lw.log( ['local images found'] )
            if self.ARTISTNUM == 1:
                self._set_artwork_skininfo( self.CACHEDIR )
                self._get_artistinfo()
        if self.TOTALARTISTS > 1:
            self._merge_images()


    def _get_musicbrainz_id( self, theartist, mbid ):
        self._set_infodir( theartist )
        lw.log( ['Looking for a musicbrainz ID for artist ' + theartist] )
        if mbid:
            lw.log( ['returning ' + mbid] )
            return mbid
        mbid_params = {}
        mbid_params['infodir'] = self.INFODIR
        for plugin_name in mbid_plugins['names']:
            lw.log( ['checking %s for mbid' % plugin_name[1]] )
            mbid, loglines = mbid_plugins['objs'][plugin_name[1]].getMBID( mbid_params )
            lw.log( loglines )
            if mbid:
                lw.log( ['returning ' + mbid] )
                return mbid
        lw.log( ['no musicbrainz ID found for artist ' + theartist] )
        return ''


    def _get_playing_item( self, item ):
        got_item = False
        playing_item = ''
        max_trys = 3
        num_trys = 1
        while not got_item:
            try:
                if item == 'album':
                    playing_item = xbmc.Player().getMusicInfoTag().getAlbum()
                elif item == 'title':
                    playing_item = xbmc.Player().getMusicInfoTag().getTitle()                
                got_item = True
            except RuntimeError:
                got_title = False
            except Exception as e:
                got_title = False
                lw.log( ['unexpected error getting %s from Kodi' % item, e] )
            if num_trys > max_trys:
                break
            else:
                num_trys = num_trys + 1
                self._wait(1)
                if self._playback_stopped_or_changed():
                    break
        #if nothing is playing, assume the information was passed by another add-on
        if not playing_item:
            playing_item = self._get_infolabel( self.SKININFO[item] )
        return playing_item


    def _get_settings( self ):
        self.LANGUAGE = getSettingString( addon, 'language' )
        for language in LANGUAGES:
            if self.LANGUAGE == language[2]:
                self.LANGUAGE = language[1]
                lw.log( ['language = %s' % self.LANGUAGE] )
                break
        self.PRIORITY = getSettingInt( addon, 'priority' )
        self.USEFALLBACK = getSettingBool( addon, 'fallback' )
        self.FALLBACKPATH = getSettingString( addon, 'fallback_path' )
        self.USEOVERRIDE = getSettingBool( addon, 'slideshow' )
        self.OVERRIDEPATH = getSettingString( addon, 'slideshow_path' )
        self.DISABLEMULTIARTIST = getSettingBool( addon, 'disable_multiartist' )
        self.MAXCACHESIZE = getSettingInt( addon, 'max_cache_size', default=1024 ) * 1000000
        artist_image_storage = getSettingInt( addon, 'artist_image_storage' )
        if artist_image_storage == 1:
            self.KODILOCALSTORAGE = True
            self.LOCALARTISTSTORAGE = True
            self.RESTRICTCACHE = False
            self.INCLUDEFANARTJPG = False
            self.INCLUDEFOLDERJPG = False
            self.FANARTFOLDER = ''
            response = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"musiclibrary.artistsfolder"}, "id":1}')
            lw.log( ['got the following response back from Kodi for music artist folder'] )
            lw.log( [response] )
            try:
                self.LOCALARTISTPATH = _json.loads(response)['result']['value']
            except (IndexError, KeyError, ValueError):
                self.KODILOCALSTORAGE = False
                self.LOCALARTISTSTORAGE = False
                self.LOCALARTISTPATH = ''
                self.RESTRICTCACHE = getSettingBool( addon, 'restrict_cache' )
                self.FANARTFOLDER = 'extrafanart'
        elif artist_image_storage == 2:
            self.KODILOCALSTORAGE = False
            self.LOCALARTISTSTORAGE = True
            self.LOCALARTISTPATH = getSettingString( addon, 'local_artist_path' )        
            self.RESTRICTCACHE = getSettingBool( addon, 'restrict_cache' )
            self.INCLUDEFANARTJPG = getSettingBool( addon, 'include_fanartjpg' )
            self.INCLUDEFOLDERJPG = getSettingBool( addon, 'include_folderjpg' )
            self.FANARTFOLDER = getSettingString( addon, 'fanart_folder', default='extrafanart' )
        else:
            self.KODILOCALSTORAGE = False
            self.LOCALARTISTSTORAGE = False
            self.LOCALARTISTPATH = ''
            self.INCLUDEFANARTJPG = False
            self.INCLUDEFOLDERJPG = False
            self.RESTRICTCACHE = getSettingBool( addon, 'restrict_cache' )
            self.FANARTFOLDER = 'extrafanart'
        lw.log( ['LOCALARTISTSTORAGE is ' + str( self.LOCALARTISTSTORAGE ), 'KODILOCALSTORAGE is ' + str( self.KODILOCALSTORAGE ), 'LOCALARTISTPATH is ' + self.LOCALARTISTPATH, 'RESTRICTCACHE is ' + str( self.RESTRICTCACHE ), 'INCLUDEFANARTJPG is ' + str( self.INCLUDEFANARTJPG ), 'INCLUDEFOLDERJPG is ' + str( self.INCLUDEFOLDERJPG ), 'FANARTFOLDER is ' + self.FANARTFOLDER] )
        if getSettingInt( addon, 'artist_info_storage' ) == 1:
            self.LOCALINFOSTORAGE = True
            self.LOCALINFOPATH = getSettingString( addon, 'local_info_path' )
        else:
            self.LOCALINFOSTORAGE = False
            self.LOCALINFOPATH = ''
        lw.log( ['LOCALINFOSTORAGE is ' + str( self.LOCALINFOSTORAGE ), 'LOCALINFOPATH is ' + self.LOCALINFOPATH ] )
        self.NOTIFICATIONTYPE = getSettingInt( addon, 'show_progress' )
        if self.NOTIFICATIONTYPE == 2:
            self.PROGRESSPATH = getSettingString( addon, 'progress_path' )
            lw.log( ['set progress path to %s' % self.PROGRESSPATH] )
        else:
            self.PROGRESSPATH = ''
        pl = getSettingInt( addon, "storage_target" )
        if pl == 0:
            self.ENDREPLACE = getSettingString( addon, "end_replace" )
            self.ILLEGALCHARS = list( '<>:"/\|?*' )
        elif pl == 2:
            self.ENDREPLACE = '.'
            self.ILLEGALCHARS = [':']
        else:
            self.ENDREPLACE = '.'
            self.ILLEGALCHARS = [os.path.sep]
        self.ILLEGALREPLACE = addon.getSetting( "illegal_replace" )


    def _init_vars( self ):
        self.FANARTNUMBER = False
        self.DATAROOT = xbmc.translatePath( addon.getAddonInfo('profile') )
        self.IMGDB = '_imgdb.nfo'
        self._set_property( "ArtistSlideshow.CleanupComplete" )
        self._set_property( "ArtistSlideshow.ArtworkReady" )
        self.SKININFO = {}
        for item in self.FIELDLIST:
            if self.PASSEDFIELDS[item]:
                self.SKININFO[item[0:-5]] = "Window(%s).Property(%s)" % ( self.WINDOWID, self.PASSEDFIELDS[item] )
            else:
                self.SKININFO[item[0:-5]] = ''
        self.EXTERNALCALLSTATUS = self._get_infolabel( self.EXTERNALCALL )
        lw.log( ['external call is set to ' + self._get_infolabel( self.EXTERNALCALL )] )
        if getSettingBool( addon, "transparent" ):
            self._set_property("ArtistSlideshowTransparent", 'true')
            self.INITDIR = os.path.join( self.DATAROOT, 'resources', 'transparent' )
        else:
            self._set_property("ArtistSlideshowTransparent", '')
            self.INITDIR = os.path.join( self.DATAROOT, 'resources', 'black' )
        self._set_property("ArtistSlideshow", self.INITDIR)
        self.NAME = ''
        self.ALLARTISTS = []
        self.MBID = ''
        self.VARIOUSARTISTSMBID = '89ad4ac3-39f7-470e-963a-56509c546377'
        self.LASTPLAYINGFILE = ''
        self.LASTJSONRESPONSE = ''
        self.LASTARTISTREFRESH = 0
        self.LocalImagesFound = False
        self.CachedImagesFound = False
        self.ImageDownloaded = False
        self.DownloadedAllImages = False
        self.UsingFallback = False
        self.MINREFRESH = 9.9
        self.TRANSITIONDIR = os.path.join( self.DATAROOT, 'transition' )
        self.MergeDir = os.path.join( self.DATAROOT, 'merge' )
        self.params = {}


    def _init_window( self ):
        self.WINDOW = xbmcgui.Window( int(self.WINDOWID) )
        self.ARTISTSLIDESHOW = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow" )
        self.ARTISTSLIDESHOWRUNNING = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshowRunning" )
        self.EXTERNALCALL = "Window(%s).Property(%s)" % ( self.WINDOWID, "ArtistSlideshow.ExternalCall" )


    def _make_dirs( self ):
        exists, loglines = checkPath( os.path.join( self.INITDIR, '' ) )
        lw.log( loglines )
        exists, loglines = checkPath( os.path.join( self.DATAROOT, '' ) )
        lw.log( loglines )
        thedirs = ['temp', 'ArtistSlideshow', 'ArtistInformation', 'transition', 'merge']
        for onedir in thedirs:
            exists, loglines = checkPath( os.path.join( self.DATAROOT, onedir, '' ) )
            lw.log( loglines )


    def _merge_images( self ):
        lw.log( ['merging files from primary directory %s into merge directory %s' % (self.CACHEDIR, self.MergeDir)] )
        self.MergedImagesFound = False
        dirs, files = xbmcvfs.listdir(self.CACHEDIR)
        for file in files:
            if(file.lower().endswith('tbn') or file.lower().endswith('jpg') or file.lower().endswith('jpeg') or file.lower().endswith('gif') or file.lower().endswith('png')):
                self.MergedImagesFound = True
                img_source = os.path.join( self.CACHEDIR, py2_decode( file ) )
                img_dest = os.path.join( self.MergeDir, itemHash( img_source ) + getImageType( img_source ) )               
                success, loglines = copyFile( img_source, img_dest )
                lw.log( loglines )
        if self.ARTISTNUM == self.TOTALARTISTS:
            wait_elapsed = time.time() - self.LASTARTISTREFRESH
            if( wait_elapsed > self.MINREFRESH ):
                self._wait( self.MINREFRESH - (wait_elapsed % self.MINREFRESH) )
            else:
                self._wait( self.MINREFRESH - (wait_elapsed + 2) )  #not sure why there needs to be a manual adjustment here
            if not self._playback_stopped_or_changed():
                lw.log( ['switching slideshow to merge directory'] )
                self._set_artwork_skininfo( self.MergeDir )


    def _move_to_kodi_storage( self ):
        lw.log( ['moving images from one place to another'] )


    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except IndexError:
            params = {}        
        except Exception as e:
            lw.log( ['unexpected error while parsing arguments', e] )
            params = {}
        self.WINDOWID = params.get( "windowid", "12006")
        lw.log( ['window id is set to %s' % self.WINDOWID] )
        self.PASSEDFIELDS = {}
        self.FIELDLIST = ['artistfield', 'titlefield', 'albumfield', 'mbidfield']
        for item in self.FIELDLIST:
            self.PASSEDFIELDS[item] = params.get( item, '' )
            lw.log( ['%s is set to %s' % (item, self.PASSEDFIELDS[item])] )
        self.DAEMON = params.get( "daemon", "False" )
        if self.DAEMON == "True":
            lw.log( ['daemonizing'] )
        self.RUNFROMSETTINGS = False
        self.MOVETOKODISTORAGE = False
        checkmove = params.get( "movetokodistorage", "False" )
        if checkmove.lower() == 'true': 
            self.MOVETOKODISTORAGE = True
            self.RUNFROMSETTINGS = True


    def _playback_stopped_or_changed( self ):
        if set( self.ALLARTISTS ) != set( self._get_current_artists() ) or self.EXTERNALCALLSTATUS != self._get_infolabel( self.EXTERNALCALL ):
            self._clear_properties()
            return True
        else:
            return False


    def _refresh_image_directory( self ):
        if( self._get_infolabel( self.ARTISTSLIDESHOW ) == self.TRANSITIONDIR):
            self._set_artwork_skininfo( self.CACHEDIR )
            lw.log( ['switching slideshow to ' + self.CACHEDIR] )
        else:
            self._set_artwork_skininfo( self.TRANSITIONDIR )
            lw.log( ['switching slideshow to ' + self.TRANSITIONDIR] )
        self.LASTARTISTREFRESH = time.time()
        lw.log( ['Last slideshow refresh time is ' + str(self.LASTARTISTREFRESH)] )


    def _remove_trailing_dot( self, thename ):
        if thename[-1] == '.' and len( thename ) > 1 and self.ENDREPLACE != '.':
            return self._remove_trailing_dot( thename[:-1] + self.ENDREPLACE )
        else:
            return thename
    

    def _run_from_settings( self ):
        if self.MOVETOKODISTORAGE:
            self._move_to_kodi_storage()
            return True
        return False


    def _set_artwork_skininfo( self, dir ):
        self._set_property( 'ArtistSlideshow', dir )
        self._set_property( 'ArtistSlideshow.ArtworkReady', 'true')
    

    def _set_cachedir( self, theartist ):
        self.CACHEDIR = self._set_thedir( theartist, 'ArtistSlideshow' )


    def _set_image_name( self, url ):
        if not self.KODILOCALSTORAGE:
            return url.rsplit('/', 1)[-1]
        ext = os.path.splitext( url )[1]
        if self.FANARTNUMBER:
            self.FANARTNUMBER += 1
        else:
            files = self._get_directory_list()
            files.sort()
            lw.log( files )
            if files:
                lastfile = files[-1]
                try:
                    tmpname = os.path.splitext( lastfile )[0]
                except IndexError:
                    return url.rsplit('/', 1)[-1]
                try:
                    self.FANARTNUMBER = int( re.search('(\d+)$', tmpname).group(0) ) + 1
                except:
                    self.FANARTNUMBER = 1
            else:
                self.FANARTNUMBER = 1
        return "fanart" + str( self.FANARTNUMBER ) + ext
            

    def _set_infodir( self, theartist ):
        self.INFODIR = self._set_thedir( theartist, 'ArtistInformation' )


    def _set_properties( self ):
        similar_total = ''
        album_total = ''
        self._set_property( "ArtistSlideshow.ArtistBiography", self.biography )
        for count, item in enumerate( self.similar ):
            self._set_property( "ArtistSlideshow.%d.SimilarName" % ( count + 1 ), item[0] )
            self._set_property( "ArtistSlideshow.%d.SimilarThumb" % ( count + 1 ), item[1] )
            similar_total = str( count )
        for count, item in enumerate( self.albums ):
            self._set_property( "ArtistSlideshow.%d.AlbumName" % ( count + 1 ), item[0] )
            self._set_property( "ArtistSlideshow.%d.AlbumThumb" % ( count + 1 ), item[1] )
            album_total = str( count )
        self._set_property( "ArtistSlideshow.SimilarCount", similar_total )
        self._set_property( "ArtistSlideshow.AlbumCount", album_total )
        

    def _set_property( self, property_name, value="" ):
        #sets a property (or clears it if no value is supplied)
        #does not crash if e.g. the window no longer exists.
        try:
          self.WINDOW.setProperty( property_name, value )
          lw.log( ['%s set to %s' % (property_name, value)] )
        except Exception as e:
          lw.log( ["Exception: Couldn't set propery " + property_name + " value " + value , e])


    def _set_safe_artist_name( self, theartist ):
        s_name = ''
        lw.log( ['the illegal characters are ', self.ILLEGALCHARS, 'the replacement is ' + self.ILLEGALREPLACE] )
        for c in list( self._remove_trailing_dot( theartist ) ):
            if c in self.ILLEGALCHARS:
                s_name = s_name + self.ILLEGALREPLACE
            else:
                s_name = s_name + c  
        return py2_decode( s_name )


    def _set_thedir( self, theartist, dirtype ):
        CacheName = self._set_safe_artist_name( theartist )
        if dirtype == 'ArtistSlideshow' and self.LOCALARTISTSTORAGE and self.LOCALARTISTPATH:
            thedir = os.path.join( self.LOCALARTISTPATH, CacheName, self.FANARTFOLDER )
        elif dirtype == 'ArtistInformation' and self.LOCALINFOSTORAGE and self.LOCALINFOPATH:
            thedir = os.path.join( self.LOCALINFOPATH, CacheName, 'information' )
        else:
            thedir = os.path.join( self.DATAROOT, dirtype, CacheName )
        exists, loglines = checkPath( os.path.join( thedir, '' ) )
        lw.log( loglines )
        return thedir


    def _split_artists( self, response):
        return response.replace(' ft. ',' / ').replace(' feat. ',' / ').split(' / ')


    def _start_download( self ):
        self.FANARTNUMBER = False
        self.CachedImagesFound = False
        self.DownloadedFirstImage = False
        self.DownloadedAllImages = False
        self.ImageDownloaded = False
        self.FirstImage = True
        cached_image_info = False
        if not self.NAME:
            lw.log( ['no artist name provided'] )
            return
        if self.PRIORITY == 2 and self.LocalImagesFound:
            pass
            #self.CACHEDIR was successfully set in _get_local_images
        else:
            self._set_cachedir( self.NAME )
        lw.log( ['cachedir = %s' % self.CACHEDIR] )
        if self.ARTISTNUM == 1:
            self._get_artistinfo()
        dirs, files = xbmcvfs.listdir( self.CACHEDIR )
        for file in files:
            if (file.lower().endswith('tbn') or file.lower().endswith('jpg') or file.lower().endswith('jpeg') or file.lower().endswith('gif') or file.lower().endswith('png')) or (self.PRIORITY == 2 and self.LocalImagesFound):
                self.CachedImagesFound = True
        if self.CachedImagesFound:
            lw.log( ['cached images found'] )
            cached_image_info = True
            self.LASTARTISTREFRESH = time.time()
            if self.ARTISTNUM == 1:
                self._set_artwork_skininfo( self.CACHEDIR )
        else:
            self.LASTARTISTREFRESH = 0
            if self.ARTISTNUM == 1:
                if self.NOTIFICATIONTYPE == 1:
                    self._set_property("ArtistSlideshow", self.INITDIR)
                    command = 'XBMC.Notification(%s, %s, %s, %s)' % (py2_encode( language(30300 )), py2_encode( language(30301) ), 5000, py2_encode( addonicon ))
                    xbmc.executebuiltin( command )
                elif self.NOTIFICATIONTYPE == 2:
                    self._set_property("ArtistSlideshow", self.PROGRESSPATH)
                else:
                    self._set_property("ArtistSlideshow", self.INITDIR)
        lw.log( ['downloading images'] )
        imgdb = os.path.join( self.INFODIR, self.IMGDB )
        lw.log( ['checking download cache file ' + imgdb] )
        loglines, cachelist_str = readFile( imgdb )
        lw.log( loglines )
        for url in self._get_image_list():
            lw.log( ['the url to check is ' + url] )
            if( self._playback_stopped_or_changed() ):
                return
            url_image_name = url.rsplit('/', 1)[-1]
            path = os.path.join( self.CACHEDIR, self._set_image_name( url ) )
            path2 = os.path.join( self.TRANSITIONDIR, url_image_name )
            lw.log( ['checking %s against %s' % (url_image_name, cachelist_str)] )
            if not (url_image_name in cachelist_str):
                if self._download(url, path, path2):
                    lw.log( ['downloaded %s to %s' % (url, path)]  )
                    lw.log( ['updating download database at ' + imgdb] )
                    cachelist_str = cachelist_str + url_image_name + '\r'
                    success, loglines = writeFile( cachelist_str, imgdb )
                    lw.log( loglines )
                    self.ImageDownloaded = True
            if self.ImageDownloaded:
                if( self._playback_stopped_or_changed() and self.ARTISTNUM == 1 ):
                    self._set_artwork_skininfo( self.CACHEDIR )
                    self.LASTARTISTREFRESH = time.time()
                    self._clean_dir( self.TRANSITIONDIR )
                    return
                if not self.CachedImagesFound:
                    self.CachedImagesFound = True
                wait_elapsed = time.time() - self.LASTARTISTREFRESH
                if( wait_elapsed > self.MINREFRESH ):
                    if( not (self.FirstImage and not self.CachedImagesFound) ):
                        self._wait( self.MINREFRESH - (wait_elapsed % self.MINREFRESH) )
                    if( not self._playback_stopped_or_changed() and self.ARTISTNUM == 1 ):
                        self._refresh_image_directory()
                self.FirstImage = False
        if self.ImageDownloaded:
            lw.log( ['finished downloading images'] )
            self.DownloadedAllImages = True
            if( self._playback_stopped_or_changed() ):
                self._set_artwork_skininfo( self.CACHEDIR )
                self.LASTARTISTREFRESH = time.time()
                self._clean_dir( self.TRANSITIONDIR )
                return
            lw.log( ['cleaning up from refreshing slideshow'] )
            wait_elapsed = time.time() - self.LASTARTISTREFRESH
            if( wait_elapsed < self.MINREFRESH ):
                self._wait( self.MINREFRESH - wait_elapsed )
            if( not self._playback_stopped_or_changed() ):
                if self.ARTISTNUM == 1:
                    self._refresh_image_directory()
                    if self.NOTIFICATIONTYPE == 1 and not cached_image_info:
                        command = 'XBMC.Notification(%s, %s, %s, %s)' % (py2_encode( language(30304) ), py2_encode( language(30305) ), 5000, py2_encode( addonicon ))
                        xbmc.executebuiltin(command)
                if self.TOTALARTISTS > 1:
                    self._merge_images()
            if( self._get_infolabel( self.ARTISTSLIDESHOW ) == self.TRANSITIONDIR and self.ARTISTNUM == 1):
                self._wait( self.MINREFRESH )
                if( not self._playback_stopped_or_changed() ):
                    self._refresh_image_directory()
            self._clean_dir( self.TRANSITIONDIR )
        if not self.ImageDownloaded:
            lw.log( ['no images downloaded'] )
            self.DownloadedAllImages = True
            if not self.CachedImagesFound:
                if self.ARTISTNUM == 1:
                    lw.log( ['setting slideshow directory to blank directory'] )
                    self._set_property("ArtistSlideshow", self.INITDIR)
                    if self.NOTIFICATIONTYPE == 1 and not cached_image_info:
                        command = 'XBMC.Notification(%s, %s, %s, %s)' % (py2_encode( language(30302) ), py2_encode( language(30303) ), 10000, py2_encode( addonicon ))
                        xbmc.executebuiltin(command)
            elif self.TOTALARTISTS > 1:
                self._merge_images()


    def _trim_cache( self ):
        if (self.RESTRICTCACHE and not self.PRIORITY == 2):
            now = time.time()
            cache_trim_delay = 0   #delay time is in seconds
            if (now - self.LastCacheTrim > cache_trim_delay):
                lw.log( ['trimming the cache down to %s bytes' % self.MAXCACHESIZE]  )
                cache_root = os.path.join( self.DATAROOT, 'ArtistSlideshow', '')
                folders, fls = xbmcvfs.listdir( cache_root )
                try:
                    folders.sort( key=lambda x: os.path.getmtime( os.path.join( cache_root, x ) ), reverse=True )
                except Exception as e:
                    # if there are any problems, don't try and delete the older cache files
                    lw.log( ['unexpected error sorting cache directory', e] )
                    return
                cache_size = 0
                first_folder = True
                for folder in folders:
                    if( self._playback_stopped_or_changed() ):
                        break
                    cache_size = cache_size + self._get_folder_size( os.path.join (cache_root, folder ) )
                    lw.log( ['looking at folder %s cache size is now %s' % (folder, cache_size)] )
                    if( cache_size > self.MAXCACHESIZE and not first_folder ):
                        self._clean_dir( os.path.join(cache_root, folder) )
                        lw.log( ['deleted files in folder %s' % folder] )
                    first_folder = False
                self.LastCacheTrim = now


    def _use_correct_artwork( self ):
        self.ALLARTISTS = self._get_current_artists()
        self.ARTISTNUM = 0
        self.TOTALARTISTS = len( self.ALLARTISTS )
        self.MergedImagesFound = False
        got_images = False
        for artist, mbid in self._get_current_artists_info( ):
            self.ARTISTNUM += 1
            self.NAME = artist
            self.MBID = mbid
            self._set_infodir( self.NAME )
            if self.USEOVERRIDE:
                lw.log( ['using override directory for images'] )
                self._set_property("ArtistSlideshow", self.OVERRIDEPATH)
                self._set_artwork_skininfo( self.OVERRIDEPATH )
                if(self.ARTISTNUM == 1):
                    self._get_artistinfo()
            elif self.PRIORITY == 1 and self.LOCALARTISTPATH:
                lw.log( ['looking for local artwork'] )
                self._get_local_images()
                if not self.LocalImagesFound:
                    lw.log( ['no local artist artwork found, start download'] )
                    self._start_download()
            elif self.PRIORITY == 2 and self.LOCALARTISTPATH:
                lw.log( ['looking for local artwork'] )
                self._get_local_images()
                lw.log( ['start download'] )
                self._start_download()
            else:
                lw.log( ['start download'] )
                self._start_download()
                if not (self.CachedImagesFound or self.ImageDownloaded):
                    lw.log( ['no remote artist artwork found, looking for local artwork'] )
                    self._get_local_images()
            if not got_images:
                got_images = self.LocalImagesFound or self.CachedImagesFound or self.ImageDownloaded or self.MergedImagesFound
        if not got_images:
            self._delete_folder( os.path.join( self.INFODIR, '' ) )
            self._delete_folder( os.path.join( self.CACHEDIR, '' ) )
            self._delete_folder( os.path.join( os.path.abspath( os.path.join( self.INFODIR, '..') ), '' ) )
            self._delete_folder( os.path.join( os.path.abspath( os.path.join( self.CACHEDIR, '..') ), '' ) )
            if self.USEFALLBACK:
                lw.log( ['no images found for any currently playing artists, using fallback slideshow'] )
                lw.log( ['fallbackdir = ' + self.FALLBACKPATH] )
                self.UsingFallback = True
                self._set_property("ArtistSlideshow", self.FALLBACKPATH)
                self._set_artwork_skininfo( self.FALLBACKPATH )


    def _update_check_file( self, path, text, message ):
        success, loglines = writeFile( text, path )
        lw.log( loglines )
        if success:
            lw.log( [message] )


    def _upgrade_settings( self ):
        #this is where any code goes for one time upgrade routines related to settings
        checkfile = os.path.join( xbmc.translatePath( addon.getAddonInfo('profile') ), 'migrationcheck.nfo' )
        loglines, data = readFile( checkfile )
        lw.log( loglines )
        if '3.0.0' not in data:
            if getSettingBool( addon, 'localstorageonly' ):
                addon.setSetting( 'artist_image_storage', '2' )
            if getSettingBool( addon, 'localinfostorage' ):
                addon.setSetting( 'artist_info_storage', '1')
                addon.setSetting( 'local_info_path', addon.getSetting( 'local_artist_path' ))


    def _upgrade( self ):
        #this is where any code goes for one time upgrade routines
        checkfile = os.path.join( xbmc.translatePath( addon.getAddonInfo('profile') ), 'migrationcheck.nfo' )
        loglines, data = readFile( checkfile )
        lw.log( loglines )
        if '3.0.0' not in data:
            src_root = os.path.join( self.DATAROOT, 'ArtistSlideshow' )
            dst_root = os.path.join( self.DATAROOT, 'ArtistInformation')
            exists, loglines = checkPath( os.path.join( src_root, '' ) )
            if exists:
                try:
                    dirs, files = xbmcvfs.listdir( src_root )
                except OSError:
                    dirs = []
                except Exception as e:
                    lw.log( ['unexpected error getting directory list', e] )
                    dirs = []
                if dirs:
                    for dir in dirs:
                        src = os.path.join( src_root, dir, self.IMGDB )
                        dst = os.path.join( dst_root, dir, self.IMGDB )
                        success, loglines = moveFile( src, dst )
                        lw.log( loglines )
            src_root = getSettingString( addon, 'local_artist_path' )
            dst_root = src_root
            exists, loglines = checkPath( os.path.join( src_root, '' ) )
            if exists:
                try:
                    dirs, files = xbmcvfs.listdir( src_root )
                except OSError:
                    dirs = []
                except Exception as e:
                    lw.log( ['unexpected error getting directory list', e] )
                    dirs = []
                if dirs:
                    for dir in dirs:
                        src = os.path.join( src_root, dir, self.FANARTFOLDER, self.IMGDB )
                        dst = os.path.join( dst_root, dir, 'information', self.IMGDB )
                        success, loglines = moveFile( src, dst )
                        lw.log( loglines )
            self._update_check_file( checkfile, '3.0.0', 'preference conversion complete' )
        

    def _wait( self, wait_time ):
        waited = 0
        while( waited < wait_time ):
            time.sleep(0.1)
            waited = waited + 0.1
            if self._playback_stopped_or_changed():
                self._set_property( "ArtistSlideshow", self.INITDIR )
                self._set_property( "ArtistSlideshow.ArtworkReady" )
                self.Abort = True
                return


lw.log( ['script version %s started' % addonversion], xbmc.LOGNOTICE )
lw.log( ['debug logging set to %s' % str( logdebug )], xbmc.LOGNOTICE )
slideshow = Main()
lw.log( ['script stopped'], xbmc.LOGNOTICE )
