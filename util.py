from datetime import datetime, timedelta
import logging
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
def shorten_cf_round_names(name: str):
    return name.replace('Educational Codeforces', 'Edu').replace('Codeforces', 'CF').replace('Round', '')

def parse_time(unix_timestamp: float):
    return datetime.fromtimestamp(unix_timestamp).strftime('%y-%m-%d %H:%M:%S')

def shorten_language(lang : str):
    return lang.replace('GNU ', '')

# FAILED, OK, PARTIAL, COMPILATION_ERROR, RUNTIME_ERROR, WRONG_ANSWER
# PRESENTATION_ERROR, TIME_LIMIT_EXCEEDED, MEMORY_LIMIT_EXCEEDED, IDLENESS_LIMIT_EXCEEDED
# SECURITY_VIOLATED, CRASHED, INPUT_PREPARATION_CRASHED, CHALLENGED
# SKIPPED, TESTING, REJECTED

def parse_verdict(submission):
    verdict = submission['verdict']
    tests = str(submission['passedTestCount'] + 1)
    if len(tests) < 3:
        tests += '&nbsp' * (3 - len(tests))

    class_type = ''
    
    if verdict == 'FAILED' or verdict == 'SECURITY_VIOLATED' or verdict == 'SKIPPED' or 'CRASHED' in verdict:
        class_type = 'verdict-failed'
    elif verdict == 'OK':
        class_type = 'verdict-accepted'
    elif verdict == 'TESTING':
        class_type = 'verdict-waiting'
    elif verdict == 'CHALLENGED':
        class_type = 'verdict-challenged'
    else:
        class_type = 'verdict-rejected'


    if verdict == 'FAILED':
        verdict = 'FL'
    elif verdict == 'OK':
        verdict = 'AC'
    elif verdict == 'WRONG_ANSWER':
        verdict = 'WA'
    elif 'ERROR' in verdict:
        verdict = verdict[0] + 'E'
    elif 'LIMIT_EXCEEDED' in verdict:
        verdict = verdict[0] + 'L'
    elif verdict == 'TESTING':
        verdict = 'WJ'
    elif verdict == 'CHALLENGED':
        verdict = 'Hacked'
    else:
        verdict = " ".join(verdict.split()).title() 
    return f'<span class="mono {class_type}">{verdict}</span><span class="mono supsub"><span class="superscript">{parse_time(submission["creationTimeSeconds"])[:-3]}</span><span class="subscript"><span class="{class_type}">{tests}</span><span>{shorten_language(submission["programmingLanguage"])[:11]}</span></span></span><span class="mono" style="user-select: none;">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>'

def parse_submission_link(submission):
  if 'contestId' in submission and submission['contestId'] < 100000:
    return "https://codeforces.com/contest/%d/submission/%d" % (submission['contestId'], submission['id'])
  elif 'problemsetName' in submission:
    return "https://codeforces.com/problemsets/%s/submission/99999/%d" % (submission['problemsetName'], submission['id'])
  else:
    return "https://codeforces.com/gym/%d/submission/%d" % (submission['contestId'], submission['id'])

def parse_problem_link(problem):
  if 'contestId' in problem and problem['contestId'] < 100000:
    return "https://codeforces.com/contest/%d/problem/%s" % (problem['contestId'], problem['index'])
  elif 'problemsetName' in problem:
    return "https://codeforces.com/problemsets/%s/problems/%s" % (problem['problemsetName'], problem['index'])
  else:
    return "https://codeforces.com/gym/%d/problem/%s" % (problem['contestId'], problem['index'])

def render_rated_handle(handle, rank):
    if isinstance(rank, str):
        class_type = color_from_rank(rank)
    else:
        class_type = color_from_rating(rank)
    return f'<a href="https://codeforces.com/profile/{handle}" target="_blank" class="{class_type}">{handle}</a>'

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
