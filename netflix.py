#!/usr/bin/python3
# -*- coding: utf-8 -*-

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

        self.contextData = None

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
        # string = re.sub(r'\\([^x])', r'\\\\\1', unicode(string, "utf-8"))
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

        return profile_guids

    def get_profiles(self):
        return self.contextData['profilesModel']['data']['profiles']

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


email = input('Email: ')
password = input('Password: ')

user = NetflixSession(email, password)

while not user.login():
    print('Incorrect username or password!')
    print('Please try again...')
    print('')
    email = input('Email: ')
    password = input('Password: ')

    user = NetflixSession(email, password)

profiles = user.get_profiles()

print('Select the number of the profile you would like to scrape...\n')

print('Enter', 'All')

for index, profile in enumerate(profiles):
    print(index, profile['firstName'])


activity = {}

while True:
    index = None
    try:
        index = input('> ')
        index = int(index)
        if -1 < index < len(profiles):
            user.switch_user(profiles[index]['guid'])
            user_activity = user.get_viewing_activity()
            user_name = profiles[index]['firstName']
            activity[user_name] = []

            for video in user_activity:
                if 'seriesTitle' in video:
                    name = '{} - {}'.format(video['seriesTitle'], video['title'])
                else:
                    name = video['title']
                activity[user_name].append(name)

            break
        else:
            print('That wasn\'t one of the numbers you could choose')
    except Exception as e:
        print(e)
        if index != '':
            print('Error! You didn\'t give me a number')
        else:
            for profile in profiles:
                user.switch_user(profile['guid'])
                user_activity = user.get_viewing_activity()
                user_name = profile['firstName']
                activity[user_name] = []
                
                for video in user_activity:
                    if 'seriesTitle' in video:
                        name = '{} - {}'.format(video['seriesTitle'], video['title'])
                    else:
                        name = video['title']
                    activity[user_name].append(name)
            break

for user in activity:
    print(user + ': ')
    print()
    print('\n'.join(activity[user]))
    print('\n')
