from flask import Flask, render_template, request, url_for
import requests, time, json
from datetime import datetime, timedelta
from jinja2.filters import FILTERS


app = Flask(__name__)
app.config.from_pyfile('config.py')

def color_from_rank(rank):
    if rank is None:
        return ""
    if rank == "legendary grandmaster":
        return "rated-user user-legendary"
    if "grandmaster" in rank:
        return "rated-user user-red"
    if rank == "candidate master":
        return "rated-user user-violet"
    if "master" in rank:
        return "rated-user user-orange"
    if rank == "expert":
        return "rated-user user-blue"
    if rank == "specialist":
        return "rated-user user-cyan"
    if rank == "pupil":
        return "rated-user user-green"
    if rank == "newbie":
        return "rated-user user-gray"
    return ""

def color_from_rating(rating):
    if rating >= 3000:
        return "rated-user user-legendary"
    if rating >= 2400:
        return "rated-user user-red"
    if rating >= 2100:
        return "rated-user user-orange"
    if rating >= 1900:
        return "rated-user user-violet"
    if rating >= 1600:
        return "rated-user user-blue"
    if rating >= 1400:
        return "rated-user user-cyan"
    if rating >= 1200:
        return "rated-user user-green"
    if rating >= -1000:
        return "rated-user user-gray"
    return ""

FILTERS['color_from_rank'] = color_from_rank
FILTERS['color_from_rating'] = color_from_rating

@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def submit():
    cf_id = request.form['cf']
    concerned = cf_id.split(';')[0]
    return render_template('query.html', contests=request_codeforces(cf_id), rated_color=cf_community_rated_color(cf_id), concerned = concerned)

@app.route('/faq', methods=['GET'])
def faq():
    return render_template('faq.html')

def create_table_html(data):
    html = '<table class="table table-striped table-bordered table-hover">\n'

    # Create header row
    html += '  <tr>\n'
    for key in data[0].keys():
        html += '    <th>{}</th>\n'.format(key)
    html += '  </tr>\n'

    # Create data rows
    for row in data:
        html += '  <tr>\n'

        for key, value in row.items():
            if key == 'creationTimeSeconds':
                # Convert Unix timestamp to datetime object
                datetime_obj = datetime.fromtimestamp(value)
                # Format datetime object as string
                value = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
            elif key == 'relativeTimeSeconds':
                if value == 2147483647:
                    value = 'N/A'
                else:
                    # Convert seconds to time period
                    time_period = timedelta(seconds=value)
                    # Format time period as string
                    value = str(time_period)

            html += '    <td>{}</td>\n'.format(value)

        html += '  </tr>\n'

    html += '</table>\n'

    return html


def request_codeforces(id):
    if id is None or len(id) < 1:
        return None
    concerned = id.split(';')[0]

    # First, get a list of all available contests
    url = 'https://codeforces.com/api/contest.list'
    params = {
        'gym': False,
    }
    response = requests.get(url, params=params)
    response_data = response.json()
    status = response_data['status']
    if status != 'OK':
        return status

    # Sort the list of contests in reverse chronological order
    contests = sorted(response_data['result'], key=lambda x: x['startTimeSeconds'], reverse=True)

    contests = [c for c in contests if c['phase'] == 'FINISHED' and c['type'] == 'CF']

    # Get the recent 10 contests that are not in gym
    recent_contests = contests[:30]

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

if __name__ == '__main__':
    app.run()