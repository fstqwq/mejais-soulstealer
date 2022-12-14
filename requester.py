import requests
import logging

def request_general(url, params):
    try:
        response = requests.get(url, params=params)
    except Exception as e:
        return 'FAILED', str(e)
    if response.status_code != 200:
        logging.warning(url)
        logging.warning(params)
        logging.warning('HTTP' + str(response.status_code))
        return 'HTTP', str(response.status_code)
    try:
        response_data = response.json()
    except:
        return 'FAILED', 'JSON decode failed. Maybe CodeForces is unavailable.'
    status = response_data['status']
    
    if status != 'OK':
        comment = response_data['comment']
        logging.warning(status + comment)
        return status, comment
    result = response_data['result']
    return 'OK', result
    

def request_contest_list (gym=False):
    url = 'https://codeforces.com/api/contest.list'
    params = {
        'gym': gym
    }

    status, result = request_general(url, params)

    if status != 'OK':
        return status, result

    if not gym:
        result = [c for c in result if c['phase'] == 'FINISHED' and (c['type'] == 'CF' or 'Educational' in c['name'] or 'Rated' in c['name'] or 'Mirror' in c['name'])]
    return status, result

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

    return request_general(url, params)

def request_user_status(handle, from_=1, count=15000):
    url = 'https://codeforces.com/api/user.status'
    params = {
        'handle': handle,
        'from': from_,
        'count': count
    }
    return request_general(url, params)

def request_user_ratedList(activeOnly=True, includeRetired=False, contestId = None):
    url = 'https://codeforces.com/api/user.ratedList'
    params = {
        'activeOnly': activeOnly,
        'includeRetired': includeRetired,
        'contestId': contestId
    }
    if not contestId:
        params.pop('contestId')
    return request_general(url, params)

def request_user_info(handles):
    url = 'https://codeforces.com/api/user.info'
    params = {
        'handles': ';'.join(handles)
    }
    return request_general(url, params)