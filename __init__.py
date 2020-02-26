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
import subprocess
import traceback
from urllib.parse import quote
import re
import requests

from mycroft.messagebus.message import Message
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.util import get_cache_directory

from pyradios import RadioBrowser


class Radio(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="Radio")
        self.curl = None
        self.regexes = {}
        self.STREAM = '{}/stream'.format(get_cache_directory('RadioSkill'))

    def CPS_match_query_phrase(self, phrase):
        # Look for regex matches
        # Play (radio|station|stream) <data>
        match = re.search(self.translate_regex('radio'), phrase)
        try:
            data = re.sub(self.translate_regex('radio'), '', phrase)
            rb = RadioBrowser()
            stations = rb.search(name=data,bitrateMin='128')
            stations != []
            self.log.info('CPS Match (radio): ' + stations[0]['name'] +
                          ' | ' + stations[0]['url'])

            if match:
                return (stations[0]['name'],
                        CPSMatchLevel.EXACT,
                        {"station": stations[0]["name"],
                         "url": stations[0]["url"],
                         "image": stations[0]['favicon']})
            else:
                return (stations[0]['name'],
                        CPSMatchLevel.TITLE,
                        {"station": stations[0]["name"],
                         "url": stations[0]["url"],
                         "image": stations[0]['favicon']})
        except Exception:
            return None

    def CPS_start(self, phrase, data):
        url = data['url']
        station = data['station']
        image = data['image']
        try:
            self.stop()

            # (Re)create Fifo
            if os.path.exists(self.STREAM):
                os.remove(self.STREAM)
            os.mkfifo(self.STREAM)

            # Speak intro while downloading in background
            self.speak_dialog('play.radio',
                              data={"station": station},
                              wait=True)

            self.log.debug('Running curl {}'.format(url))
            args = ['curl', '-L', '-s', quote(url, safe=":/"),
                    '-o', self.STREAM]
            self.curl = subprocess.Popen(args)

            # Begin the radio stream
            self.log.info('Station url: {}'.format(url))
            self.CPS_play(('file://' + self.STREAM, 'audio/mpeg'))
            self.CPS_send_status(image=image, track=station)

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

    def CPS_send_status(self, artist='', track='', image=''):
        data = {'skill': self.name,
                'artist': artist,
                'track': track,
                'image': image,
                'status': None  # TODO Add status system
                }
        self.bus.emit(Message('play:status', data))

    # Get the correct localized regex
    def translate_regex(self, regex):
        if regex not in self.regexes:
            path = self.find_resource(regex + '.regex')
            if path:
                with open(path) as f:
                    string = f.read().strip()
                self.regexes[regex] = string
        return self.regexes[regex]

    def exists_url(url):
        r = requests.head(url)
        if r.status_code < 400:
            return True
        else:
            return False


def create_skill():
    return Radio()
