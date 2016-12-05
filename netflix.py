from bs4 import BeautifulSoup
import requests
import codecs
import json
import time
import re


# TODO: add comments

# This code essentially mimics a browser, rather than starting a complete
# instance of one. It also accounts for multiple profiles and gets all the
# viewing history

# Don't use Selenium when you can build a better program without it
#     - Juan Potato

class NetflixSession:
    '''Class to manage netflix sessions for scraping'''
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0'}

    def __init__(self, email, password):
        page = self.session.get('https://www.netflix.com/Login',
                                headers=self.headers)
        soup = BeautifulSoup(page.text, 'lxml')

        authURL = soup.find('input', attrs={'name': 'authURL'})['value']

        self.paramaters = {
            'email': email,
            'password': password,
            'rememberMe': True,
            'flow': 'websiteSignUp',
            'mode': 'login',
            'action': 'loginAction',
            'withFields': 'email,password,rememberMe,nextPage',
            'authURL': authURL,
            'nextPage': 'https://www.netflix.com/viewingactivity'
        }

    def escape(self, string):
        # escape anything that isnt escaped (\xXX)
        string = re.sub(r'\\([^x])', r'\\\\\1', string)
        # unescape \xXX codes
        return codecs.decode(string, 'unicode_escape')

    def login(self):
        ''' Returns False if incorrect pass/email, otherwise True '''
        page = self.session.post('https://www.netflix.com/Login',
                                 data=self.paramaters, headers=self.headers)

        contextData = re.search(r'contextData\s+=\s+({[\s\S]+?});', page.text)
        contextData = json.loads(self.escape(contextData.group(1)))
        self.contextData = contextData

        return 'Login' not in page.url

    def get_profile_guids(self):
        profile_guids = []

        for profile in self.contextData['profilesModel']['data']['profiles']:
            profile_guids.append(profile['guid'])

        self.contextData['profilesModel']['data']['active']['guid']

        return profile_guids

    def get_active_profile(self):
        return self.contextData['profilesModel']['data']['active']

    def switch_user(self, guid):
        if guid == self.get_active_profile()['guid']:
            # if we are switching to ourselves, do nothing
            return

        url = 'https://www.netflix.com/SwitchProfile?tkn={}'
        self.session.get(url.format(guid), headers=self.headers)
        page = self.session.get('https://www.netflix.com/viewingactivity',
                                headers=self.headers)

        contextData = re.search(r'contextData\s+=\s+({[\s\S]+?});', page.text)
        contextData = json.loads(self.escape(contextData.group(1)))
        self.contextData = contextData

    def get_viewing_activity(self):
        serverDefs = self.contextData['serverDefs']['data']
        url = '/'.join([serverDefs['SHAKTI_API_ROOT'],
                        serverDefs['BUILD_IDENTIFIER'],
                        'viewingactivity'])

        authURL = self.contextData['userInfo']['data']['authURL']

        page = 0
        viewing_activity = []

        while True:
            paramaters = {
                'pg': page,
                'pgSize': 100,
                '_': int(time.time() * 1000),
                'authURL': authURL
            }
            res = self.session.get(url, params=paramaters).json()

            if len(res['viewedItems']) > 0:
                viewing_activity.extend(res['viewedItems'])
                page += 1
            else:
                break

        return viewing_activity


'''
# Example program, TODO: move to its own file soon
import json
import re
from get_netflix_activity import NetflixSession

email = 'you@email.com'
password = 'Password'

user = NetflixSession(email, password)
user.login()
for guid in user.get_profile_guids():
    user.switch_user(guid)
    print(user.get_viewing_activity())  # TODO: process this and output to file
'''
