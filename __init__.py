"""
skill Radio
Copyright (C) 2020  Andreas Lorensen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
from os.path import join, abspath, dirname
import subprocess
import traceback
from urllib.parse import quote

from mycroft.messagebus.message import Message
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.util import get_cache_directory
from mycroft.util.parse import match_one

from pyradios import RadioBrowser


class Radio(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="Radio")
        self.curl = None
        self.now_playing = None
        self.STREAM = '{}/stream'.format(get_cache_directory('RadioSkill'))

    def CPS_match_query_phrase(self, phrase):
        rb = RadioBrowser()
        rbstations = rb.search(name=phrase)
        stations = {}
        for rbstation in rbstations:
            key = rbstation['name']
            url = rbstation['url_resolved']
            stations[key] = url
        # Get match and confidence
        match, confidence = match_one(phrase, stations)
        # If the confidence is high enough return a match
        self.log.info(match)
        if confidence > 0.5:
            return (match, CPSMatchLevel.EXACT, {"station": phrase, "url": match})
        # Otherwise return None
        else:
            return None

    def CPS_start(self, phrase, data):
        url = data['url']        
        station = data['station']
        try:
            self.stop()
            self.now_playing = station

            # (Re)create Fifo
            if os.path.exists(self.STREAM):
                os.remove(self.STREAM)
            os.mkfifo(self.STREAM)

            # Speak intro while downloading in background
            self.speak_dialog('play.radio', data={"station": self.now_playing}, wait=True)

            self.log.debug('Running curl {}'.format(url))
            args = ['curl', '-L', quote(url, safe=":/"), '-o', self.STREAM]
            self.curl = subprocess.Popen(args)

            # Begin the radio stream
            self.log.info('Station url: {}'.format(url))
            self.CPS_play(('file://' + self.STREAM, 'audio/mpeg'))
            
            # TODO download image from RadioBrowser so we could show it n display
            # self.CPS_send_status(image=image or image_path('generic.png'),
            #                     track=self.now_playing)

        except Exception as e:
            self.log.error("Error: {0}".format(e))
            self.log.info("Traceback: {}".format(traceback.format_exc()))
            self.speak_dialog('could.not.play')

    def stop(self):
        # Stop download process if it's running.
        if self.curl:
            try:
                self.curl.kill()
                self.curl.communicate()
            except Exception as e:
                self.log.error('Could not stop curl: {}'.format(repr(e)))
            finally:
                self.curl = None
            self.CPS_send_status()
            return True

    def PlayCPS_send_status(self, artist='', track='', image=''):
        data = {'skill': self.name,
                'artist': artist,
                'track': track,
                'image': image,
                'status': None  # TODO Add status system
                }
        self.bus.emit(Message('play:status', data))


def create_skill():
    return Radio()
