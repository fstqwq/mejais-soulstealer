

from util import *
from fetcher import *
from requester import *

def request_codeforces(id):
    if id is None or len(id) < 1:
        return None
    concerned = id.split(';')[0]

    status, contests = request_contest_list(gym=False)
    if status != 'OK':
        return status

    # Sort the list of contests in reverse chronological order

    # Get the recent 10 contests that are not in gym
    recent_contests = contests[:6]

    for contest in recent_contests:
        url = 'https://codeforces.com/api/contest.standings'
        if contest['phase'] != 'FINISHED':
            contest['query_status'] = 'Contest is at phase ' + contest['phase']
        else:
            params = {
                'contestId': contest['id'],
                'from': 1,
                'count': 10,
                'handles': id,
                'showUnofficial': True
            }
            response = requests.get(url, params=params)
            response_data = response.json()
            status = response_data['status']
            if status != 'OK':
                contest['query_status'] = 'Query return: ' + str(response_data)
            else:
                contest['query_status'] = 'OK'
                result = response_data['result']
                for row in result['rows']:
                    if concerned in [m['handle'] for m in row['party']['members']]:
                        for problem, results in zip(result['problems'], row['problemResults']):
                            if results['points'] > 0:
                                problem['concerned_accepted'] = True
                            elif results['rejectedAttemptCount'] > 0:
                                problem['concerned_attemped'] = True
                ac, rj, all = 0, 0, 0
                for problem in result['problems']:
                    if 'concerned_accepted' in problem.keys():
                        ac += 1
                    elif 'concerned_attemped' in problem.keys():
                        rj += 1
                    all += 1
                contest['concerned_status'] = 'AK' if ac == all else 'OPEN' if ac > 0 else 'RJ' if rj > 0 else 'NEW'
                contest['query_result'] = result
    print(recent_contests)
    return recent_contests

def cf_community_rated_color(handles):
    base_url = 'https://codeforces.com/api/user.info'
    params = {
        'handles': handles
    }

    response = requests.get(base_url, params=params)
    response_data = response.json()

    # Check if the request was successful
    if response_data['status'] != 'OK':
        raise Exception('Failed to retrieve user information')

    # Extract the rank of each user from the response
    users = response_data['result']
    ranks = {}
    for user in users:
        color = color_from_rank(user['rank'])
        ranks[user['handle']] = color

    return ranks
