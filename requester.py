import requests
import logging

def request_contest_list (gym=False):
    url = 'https://codeforces.com/api/contest.list'
    params = {
        'gym': gym
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return 'FAILED', str(response.status_code)
    response_data = response.json()
    status = response_data['status']
    if status != 'OK':
        logging.warning(status)
        return status, response_data['comment']

    contests = response_data['result'] 
    if not gym:
        contests = [c for c in contests if c['phase'] == 'FINISHED' and c['type'] == 'CF']
    return 'OK', contests

def request_contest_standings(contestId, from_=1, count=1000, handles=None, showUnofficial=True):
    url = 'https://codeforces.com/api/contest.standings'
    if handles:
        handles = ';'.join(handles)
    params = {
        'contestId': contestId,
        'from': from_,
        'count': count,
        'handles': handles,
        'showUnofficial': showUnofficial
    }
    if not handles:
        params.pop('handles')

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return str(response.status_code), str(response.status_code)

    response_data = response.json()
    status = response_data['status']
    if status != 'OK':
        logging.warning(status)
        return status, str(response_data)

    return 'OK', response_data['result']

def request_user_status(handle, from_=1, count=100):
    url = 'https://codeforces.com/api/user.status'
    params = {
        'handle': handle,
        'from': from_,
        'count': count
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return str(response.status_code), []

    response_data = response.json()
    status = response_data['status']
    if status != 'OK':
        logging.warning(status)
        return status, str(response_data)

    return 'OK', response_data['result']

def request_user_ratedList(activeOnly=True, includeRetired=False, contestId = None):
    url = 'https://codeforces.com/api/user.ratedList'
    params = {
        'activeOnly': activeOnly,
        'includeRetired': includeRetired,
        'contestId': contestId
    }
    if not contestId:
        params.pop('contestId')
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return str(response.status_code), []

    logging.info("rated response received")

    response_data = response.json()
    status = response_data['status']
    if status != 'OK':
        logging.warning(status)
        return status, str(response_data)

    return 'OK', response_data['result']

def request_user_info(handles):
    url = 'https://codeforces.com/api/user.info'
    params = {
        'handles': ';'.join(handles)
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return str(response.status_code), str(response.json())

    response_data = response.json()
    status = response_data['status']
    if status != 'OK':
        logging.warning(status)
        return status, str(response_data)

    return 'OK', response_data['result']