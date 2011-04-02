#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ZDF Mediathek Download/Streaming Skript
# v0.5.3 <apoc@sixserv.org> http://apoc.sixserv.org/
# Stand: 2009-12-22
# Artikel: http://sixserv.org/2009/12/21/mtgetzdf-mediathek-downloadstream/
# Sollte auf jeder standard Python installation laufen, wenn nicht mailt mir bitte :)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

##
# "Pseudo" constants for download and streaming commands
#
# %URL% and %OUTFILE% will be replaced. If you notice buffering lags in 
# streaming mode increase the cache size.
#
# alternativly: CMD_DOWNLOAD='mmsrip "--output=%OUTFILE%" "%URL%"'
CMD_DOWNLOAD = 'mplayer -prefer-ipv4 -noframedrop -dumpfile "%OUTFILE%" -dumpstream -playlist "%URL%"'
CMD_STREAM   = 'mplayer -fs -zoom -display :0.0 -prefer-ipv4 -cache 2000 -playlist "%URL%"'

# used for url constructing
URL_BASE = "http://www.zdf.de"

# fixxed enums for mode
DOWNLOAD = 0
STREAM   = 1

# default settings that can change via the options
quality        = 2      # DSL X000 (1k or 2k is currently supported)
mode           = STREAM # streaming the videos per default
search         = None
maxr           = 10     # maximum results to proceed
interactive    = False  # interactive video and channel selection
verbose        = False
directory      = "./"
title_filename = False
ignore_channel = False  # ignoriert kanaele in suchergebnissen
colors         = True   # aktiviert kursiv und fettschrift in select_entries()

import getopt
import sys
import string
import re
import urllib
import os
import htmlentitydefs

##
# thanks to Fredrik Lundh for this function:
# http://effbot.org/zone/re-sub.htm#unescape-html
##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

##
# Gather all entries in url
#
# Load url, parses for videos or channels including metadata. Proceed with
# next page if necessary until <maxr> entries are found or end is reeched.
#
# The returning list includes dictionary entries for each found video or channel,
# in the following format:
# {'id': ID, 'type': TYPE, 'url': URL, 'info': list(infoA, infoB, ...)}
#
# @param string mediathek url
# @return list
def gather_entries(url):
    global verbose, URL_BASE, maxr, ignore_channel
    
    entry_count = maxr

    entries = []
    
    while True:
        
        # laden der url inhalte => contents
        if verbose: print " [+] Gathering url: "+url
        try:
            url = re.sub('&amp;', '&', url)
            site = urllib.urlopen(url)
            contents = site.read()
        except:
            print "Error in retriving url(%s)" % url
            sys.exit(2)
        
        if verbose: print " [+] Searching page for videos/kanaele"

        # die beiden regex's matchen auf Videos _und_ Kanaele
        # 1ter ist url und titel 2ter ist url und untertitel url sollte gleich sein
        found=[]

        matches = re.findall('<p><b><a href="([^"]+)">([^<]+)<br', contents)
        matches += re.findall('class="grey"><a href="([^"]+)".?>([^<]+)<\/a><\/p>', contents)

        for match in matches:
            found_url = match[0]
            found_type = ''
            found_id = None

            # je nach format der gefundenen url wird type gesetzt zu video...
            video_match = re.match('/ZDFmediathek/beitrag/video/([0-9]+)/', found_url)
            if video_match:
                found_type = 'video'
                found_id = video_match.group(1)

            # oder 'kanaluebersicht'
            if not ignore_channel:
                kanaluebersicht_match = re.match('/ZDFmediathek/kanaluebersicht/aktuellste/([0-9]+)', found_url)
                if kanaluebersicht_match:
                    found_type = 'kanal'
                    found_id = kanaluebersicht_match.group(1)

            # nur videos oder kanal urls werden berücksichtigt, bilderstrecken 
            # und interaktive inhalte werden ignoriert
            if found_id:
                try:
                    found_info = [ match[1] ]
                    # search for duplicate entry in found
                    for item in found: # if found just add found data to str data

                        if item['id'] == found_id:
                            item['info'] += found_info
                            break

                    else: # yeah finally, first time using this python feature :)

                        # wurde die id _nicht_ gefunden baue neues dict
                        found += [{'id': found_id, 'type': found_type, 'url': found_url, 'info': found_info}]

                except IndexError: # sollte beim debugging gut helfen
                     if verbose: print " [+] IndexError in parsing! Payload: "+match+"/"+id_match

        if verbose: print " [+] FOUND: %d entries" % len(found)
        
        # verschiebt "max result" gefundene einträge nach entries
        for item in found:
            entries += [item]
            entry_count -= 1
            if entry_count <= 0: break

        # break if no next pages
        if not 'Nutzen Sie unsere Suchfilter' in contents:
            break

        #
        # proceed with next page
        #
        next_match = re.findall('<a href="([^"]+)" class="forward">Weiter</a>', contents)
        if not next_match:
            next_match = re.findall('<a href="([^"]+)" class="weitereBeitraege">Weitere  Beitr&auml;ge laden.<\/a>', contents)

        if entry_count > 0 and len(next_match) > 0:
            if verbose: print " [+] Found Next Link!"
            url = next_match[0]
            if not 'http://' in url:
                url = URL_BASE+url
        else:
            entry_count = 0

        if entry_count <= 0:
            break
            
        if verbose: print " [+] entry_count: %d" % entry_count

    return entries

##
# Print and makes user selection, return url list
#
# The parameter entries format is the same returned from gather_entries(),
# the function prints the entries and if the interactive setting is True the 
# the user can enter a selection of entries, the method generates a list
# of all selected entries and returns a url list. ["<URL A>", "<URL B>", ...]
#
# @see gather_entries
# @param list including dictionaries in gather_entries format
# @return list
def select_entries(entries):
    global URL_BASE, verbose, interactive, colors

    # print numeric list, create selected list with urls
    selected = []
    i = 1
    for item in entries:
        if len(item) != 4:
            if verbose: print " [+] Video Item Error! (Wrong List structure!)"
            next

        url = item['url']

        if verbose: print " == > %s" % url

        print "%d : (%s)" % (i, string.capitalize(item['type']))

        # vertausche "kategorie" mit titel, das alles mit info is ein wenig
        # unstrukturiert vll mal neu schreiben
        if len(item['info']) >= 2:
            (item['info'][0], item['info'][1]) = (item['info'][1], item['info'][0])

        for idx, info in enumerate(item['info']):
            info = unescape(info)
            if colors and idx == 0:
                print "\t\x1B[3m%s\x1B[0m" % info
            elif colors and idx == 1:
                print "\t\x1B[1m%s\x1B[0m" % info
            elif colors and idx == 2:
                print "\t\x1B[3m(%s)\x1B[0m" % info
            else: # no colors:
                print "\t%s" % info
        print

        if not item['info'][0]:
            title = None
        else:
            title = item['info'][0]

        selected += [URL_BASE+url]
        i+=1

    if interactive:
        print "Select Videos to play(space seperated list):"
        print " ===> ",
        sel = sys.stdin.readline()[:-1]
        sel_idx = sel.split(' ')
        new_selected=[]
        for idx, t in enumerate(selected):
            if str(idx+1) in sel_idx:
                new_selected += [t]
        selected = new_selected
        print
        print "+----------------------------------------------------------+"
        print

    return selected

##
# Gather video link, parses for asx and execute cmd
#
# The function loads the given link, parses for a asx link in the given quality 
# setting(DSL 1000 / DSL 2000) and execute stream or download command according
# to the mode setting.
#
# @param string
def proceed_video(url):
    global mode, verbose, directory
    if verbose: print " [+] Proceed Video URL: Gathering video url: "+url
    try:
        url = re.sub('&amp;', '&', url)
        site = urllib.urlopen(url)
        contents = site.read()
    except:
        print "Error in retriving url(%s)" % url
        sys.exit(2)
    asx_match = re.findall('DSL %d000 <a href="(.*asx)"' % quality, contents)

    if len(asx_match) <= 0:
        return False
    asx = asx_match[0]
    if mode == STREAM:
        cmd = re.sub('%URL%', asx, CMD_STREAM)
        if verbose: print " [+] Execute Shell Command: "+cmd
        os.system(cmd)
    else:
        filename = re.findall("/([^\/]+)\.asx", asx)[0] + ".wmv"

        if title_filename: # nur wenn der cli parameter gesetzt ist
            title_match = re.findall('<h1 class="beitragHeadline">([^<]+)</h1>', contents)
            if title_match:
                title = title_match[0]
                # convert space
                title = re.sub(' ', "-", title)
                # strip all not alpha
                title = re.sub('[^a-zA-Z0-9-]', '', title)
                title = re.sub('[-]+', '_', title)
                filename = title + '.wmv'

        cmd = re.sub('%OUTFILE%', directory+filename, CMD_DOWNLOAD)
        cmd = re.sub('%URL%', asx, cmd)
        if verbose: print " [+] Execute Shell Command: "+cmd
        os.system(cmd)

##
# print usage screen and exit
def usage():
    print """ZDF Mediathek Download/Streaming Skript
v0.5 <apoc@sixserv.org> http://apoc.sixserv.org/
Stand: 2009-12-20

Syntax: %s <URL/ID> [OPTIONS]

  <URL/ID>                   mediathek video/kanal url oder id  
  -1                         qualitaet DSL 1000
  -2                         qualitaet DSL 2000 (Standard)
  -m, --mode <d/s>           download(d) oder streaming(s)
  -d, --dir <directory>      das verzeichnis wohin gespeichert werden soll(.)
  -t, --title                benutzt nicht den stream dateinamen sondern titel
  -s, --search <topic>       suche in der mediathek
  -l, --maxr <max>           wieviele ergebnisse verarbeiten(suche/kategorie)
  -c, --ignore-channel       ignoriert kanaele
      --no-colors            deaktiviert die kursiv und fettschrift
  -i                         interaktiv, auswahl der zu spielenden videos
  -v                         erweiterte ausgabe, zu debugging zwecken
  -h, --help                 zeigt diese hilfe
""" % sys.argv[0]

#
# Parsing command line arguments
#
try:
    opts, args = getopt.getopt(sys.argv[1:], "12m:d:ts:l:civh", 
    ["mode=", "dir=", "title", "search=", "maxr=", "ignore-channel", "no-colors", "help"])
except getopt.GetoptError, err:
    print str(err)
    usage()
    sys.exit(2)

#
# Change default settings according to the parameters
#
try:
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-1"):
            quality = 1
        elif o in ("-2"):
            quality = 2
        elif o in ("-m", "--mode"):
            if a != "d" and a != "s":
                print "mode d or s!"
                sys.exit()
            if a == "d":
                mode = DOWNLOAD
            else:
                mode = STREAM
        elif o in ("-d", "--dir"):
            directory = a
            if not os.path.isdir(directory):
                print "Error: No Directory!"
                sys.exit()
            # missing / ?
            if directory[-1:] != '/':
                directory += '/'
        elif o in ("-t", "--title"):
            title_filename = True
        elif o in ("-s", "--search"):
            search = a
        elif o in ("-l", "--maxr"):
            maxr = int(a)
        elif o in ("-c", "--ignore-channel"):
            ignore_channel = True
        elif o in ("--no-colors"):
            colors = False
        elif o in ("-i"):
            interactive = True
        elif o in ("-v"):
            verbose = True
        else:
            assert False, "unhandled option"
except ValueError:
    print "Error in parsing parameter types."
    sys.exit(2)

#
# Print usage screen if url is missing
#
if len(sys.argv) <= 1:
    usage()
    exit


#
# Assign url or id variable
#
url_id = sys.argv[-1]

#
# Replace url_id with search url if seach option is given
#
if search:
    print "Searching... "+search
    url_id = "http://www.zdf.de/ZDFmediathek/suche?sucheText=%s&offset=0&flash=off" % urllib.quote_plus(search)
    if verbose: print " [+] Search URL: %s" % url_id

#
# Handling video ID
#
if re.match("^[0-9]+$", url_id):
    if verbose: print " [+] Proceed with Id: %s" % url_id
    proceed_video(URL_BASE+"/ZDFmediathek/beitrag/video/%s/?flash=off" % url_id)

#
# Handling video or channel url
#
elif re.match("^http:", url_id):
    if verbose: print " [+] Proceed with URL: %s" % url_id

    # make sure flash is off:
    if "flash=" in url_id:
        url_id = re.sub('flash=on', 'flash=off', url_id)
    else:
        if "?" in url_id:
            url_id += "&flash=off"
        else:
            url_id += "?flash=off"

    #
    # Handle Video URL:
    #
    if re.findall("/video/", url_id):
        proceed_video(url_id)

    #
    # Handling Channel or Search URL:
    #
    else: # kategorie url z.B. zeige liste/auswahl und abspielen
        url = url_id
        proceed_urls = []
        while True:
            entries = gather_entries(url)
            selection = select_entries(entries)
            for select_url in selection:
                if 'kanal' in select_url:
                    if verbose: print " [+] Follow Kanal entry!"
                    url = select_url
                    break
                else:
                    if verbose: print " [+] Proceed with Video:"
                    proceed_video(select_url)
            else:
                break

#EOF
