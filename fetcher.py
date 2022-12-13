import shelve
import time
from requester import *
from util import *

DB_FILE = 'mejai.db'

handle_dict = {}
contest_dict = {}
last_upd_msg = None

def db_read():
    global handle_dict, contest_dict, last_upd_msg
    with shelve.open(DB_FILE) as db:
        handle_dict = db["handle"]
        contest_dict = db["contest"]
        last_upd_msg = db['mejai']

def db_commit():
    global handle_dict, contest_dict, last_upd_msg
    with shelve.open(DB_FILE) as db:
        db["contest"] = contest_dict
        db['handle'] = handle_dict
        db['mejai'] = last_upd_msg

# in-memory cache, no need to write in db since it's fast
submissions_dict = {}
submissions_last_upd = {}

def initialize_db():
    logging.info('initialize db')
    with shelve.open(DB_FILE) as db:
        if 'mejai' not in db: # token that when a databased initialized successufully
            logging.info('new db')
            db.clear() # reconstruct database
            db["contest"] = {}
            db['handle'] = {}
            db['mejai'] = None
    db_read()

def update_users(input_handles=None):
    status, users = request_user_info(handle_dict.keys() if not input_handles else input_handles)
    if status != 'OK':
        logging.info(status + users)
        return False
    for user in users:
        handle = user['handle']
        user['result_time'] = time.time()
        handle_dict[handle] = user
    db_commit()
    return True

def extend_users(handles):
    handles = [h for h in handles if h not in handle_dict.keys()]

    if len(handles) > 0:
        return update_users(handles)
    else:
        return False # nothing has been done

def initialize_users():
    logging.info('initialize users')
    logging.info(f'users : {len(handle_dict)}')
    if len(handle_dict) == 0:
        # initialize the handle set, with user information
        return extend_users(['tourist'])
    return False

def update_contests():
    for contest in contest_dict.values():
        logging.info(f'loading contest {contest["id"]} : ' + contest['name'])
        handles = list(handle_dict.keys())
        if len(handles) == 0:
            continue
        status, result = request_contest_standings(contest['id'], handles=handles)
        if status != 'OK':
            logging.info(f'{status} : {result}')
        else:
            contest['rows'] = result['rows']
            contest['problems'] = result['problems']
            contest['result_time'] = int(time.time())
            contest_dict[contest['id']] = contest
            global last_upd_msg
            last_upd_msg = f'Contest {contest["id"]} ({contest["name"]}) : {datetime.now().strftime("%B %d %Y %I:%M:%S %p")}, with last handle {handles[-1]}'
            logging.info(f'success : count = {len(result["rows"])} ' + last_upd_msg)
    db_commit()

def initialize_contests():
    logging.info('initialize contests')
    if len(contest_dict) > 0:
        return False
    status, contests = request_contest_list ()
    if status != 'OK':
        logging.warning('load contest list failed: ' + contests)
        return False
    for contest in contests:
        contest['rows'] = []
        contest['problems'] = []
        contest_dict[contest['id']] = contest
    update_contests()
    db_commit()
    return True

SUBMISSION_AUTO_THRESHOLD = 10 # seconds
SUBMISSION_FULL_THRESHOLD = 10 * 60 * 60 # seconds

def update_handle_submissions(handle):
    logging.info('update handle ' + handle)
    assert handle in handle_dict

    if len(submissions_dict.get(handle, list())) > 0 and time.time() - submissions_last_upd[handle] < SUBMISSION_FULL_THRESHOLD:
        # update
        old_submissions = submissions_dict[handle]
        old_latest_id = old_submissions[0]['id']
        
        for count in [100]:
            status, result = request_user_status(handle, 1, count)
            if status != 'OK' or len(result):
                break # retry

            if len(result) == 0:
                logging.warning(f'submissions in dict len : {len(old_submissions)} but got zero length in update')
                return 'OK', 0

            result_last_id = result[-1]['id']
            if result[-1]['id'] > old_latest_id:
                break # too many, full update

            for i in range(len(old_submissions)):
                if old_submissions[i]['id'] < result_last_id:
                    result.extend(old_submissions[i:])
                    break

            submissions_dict[handle] = result
            submissions_last_upd[handle] = time.time()
            return 'OK', len(result)

    # new
    status, result = request_user_status(handle)
    if status != 'OK':
        return status, result
    submissions_last_upd[handle] = time.time()
    submissions_dict[handle] = result
    return 'OK', len(result)
    

def auto_update_handle_submissions(handle):
    assert handle in handle_dict

    if handle in submissions_last_upd and time.time() - submissions_last_upd[handle] < SUBMISSION_AUTO_THRESHOLD:
        return
    update_handle_submissions(handle)


def preprocess_handles(handles):
    if handles is None or len(handles) == 0 or len(handles) > 10000:
        raise Exception(f'bad handles : input len = {None if handles is None else len(handles)}')
    if isinstance(handles, str):
        if ';' in handles:
            handles = handles.split(';')
        elif ',' in handles:
            handles = handles.split(',')
        elif ' ' in handles:
            handles = handles.split(' ')
        else:
            handles = handles.split()
        handles = [handle.replace(',', '').replace(';', '').replace(' ', '') for handle in handles]
    
    if handles is None or len(handles) == 0 or len(handles) > 100:
        raise Exception(f'bad handles : len(handles) = {None if handles is None else len(handles)}')

    for handle in handles:
        if handle not in handle_dict.keys():
            raise Exception(f'You should add handle {handle} before query')

    return handles

def query_handles_contest(handles, from_ = 1, to = 100, concerned = None):
    logging.info('start query')
    handles = preprocess_handles(handles)

    if concerned is None:
        concerned = handles[0]
    assert concerned in handles
    
    rendered_handles = {}
    contest_list = []

    for handle in handles:
        rendered_handles[handle] = render_rated_handle(handle, handle_dict[handle].get('rank', ''))

    contests = list(contest_dict.values())
    contests = sorted(contests, key=lambda x:x['startTimeSeconds'], reverse=True)[from_-1:from_-1+to]

    contest_concerned_submissions = {}
    contest_duration = {}
    for contest in contests:
        contest_concerned_submissions[contest['id']] = {}
        contest_duration[contest['id']] = contest['durationSeconds']
    
    auto_update_handle_submissions(concerned)
    
    logging.info('end update')
    
    concerned_verdicts = ['no', 'rejected', 'accepted-upsolve', 'accepted']

    for submission in submissions_dict.get(concerned, list()):
        if 'contestId' not in submission:
            continue # e.g. acmsguru
        if 'verdict' not in submission:
            continue # e.g. running
        contest_id = submission['contestId']
        verdict = submission['verdict']
        if contest_id in contest_concerned_submissions:
            value = 0
            if verdict == 'OK' and submission['relativeTimeSeconds'] <= contest_duration[contest_id]:
                value = 3
            elif verdict == 'OK':
                value = 2
            elif verdict != 'COMPILATION_ERROR':
                value = 1
            # If it is, append the submission to the list of submissions for that contest
            old_value = contest_concerned_submissions[contest_id].get(submission['problem']['index'], 0)
            if old_value < value:
                contest_concerned_submissions[contest_id][submission['problem']['index']] = value

    for contest in contests:
        standings = []

        concerned_submissions = contest_concerned_submissions[contest['id']]
        for p in contest['problems']:
            p['concerned'] = concerned_verdicts[concerned_submissions.get(p['index'], 0)]
        
        for row in contest['rows']:
            party_members = [m['handle'] for m in row['party']['members']]
            is_watched = False
            is_concerned = False
            for member in party_members:
                if member == concerned:
                    is_concerned = True
                    is_watched = True
                elif member in handles:
                    is_watched = True
            if is_watched:
                rendered_members = [render_rated_handle(member,
                    handle_dict[member].get('rank', '')) for member in party_members]
                problem_results = []
                for p, problem in zip(contest['problems'], row['problemResults']):
                    rejected = problem['rejectedAttemptCount']
                    if problem['points'] > 0:
                        state = 'accepted'
                        show = '+'
                    else:
                        state = 'rejected' if rejected > 0 else 'no'
                        show = '-'
                    if rejected > 0:
                        show += str(rejected)
                    problem_results.append((state, show))

                row_dict = {'rank': row['rank'],
                    'points' : row['points'],
                    'members': rendered_members,
                    'type': row['party']['participantType'],
                    'problem_results': problem_results,
                    'is_concerned': is_concerned}
                standings.append(row_dict)
        
        ac, rj, no = 0, 0, 0
        for p in contest['problems']:
            x = p['concerned']
            if x == 'rejected':
                rj += 1
            elif x == 'no':
                no += 1
            else:
                ac += 1
        if rj + no == 0:
            concerned_status = 'AK'
        elif ac > 0:
            concerned_status = 'OPEN'
        elif rj > 0:
            concerned_status = 'RJ'
        else:
            concerned_status = 'NEW'
        contest_return_dict = {'name' : contest['name'],
            'id' : contest['id'],
            'problems' : contest['problems'],
            'standings' : standings,
            'concerned_status': concerned_status}
        contest_list.append(contest_return_dict)
    return {'concerned': concerned,
    'contests': contest_list,
    'rendered_handles': rendered_handles,
    'new_handles' : [], # deprecated
    'last_upd_msg' : last_upd_msg,
    'recent_submissions' : submissions_dict.get(concerned, list())[:40],
    'recent_submissions_last_upd' : submissions_last_upd.get(concerned, 'None')}

def render_handles(handles):
    ret = []
    for h in handles:
        ret.append(render_rated_handle(h, handle_dict[h].get('rank', '')))
    return ','.join(ret)

def dump_all_handles():
    return render_handles(handle_dict.keys())