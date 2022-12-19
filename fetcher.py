import shelve
import time
from enum import Enum
import threading, queue
from requester import *
from util import *

DB_FILE = 'mejai.db'

dict_lock = threading.Lock()

handle_dict = {}
contest_dict = {}
last_upd_msg = None

SUB, CONTEST, USER, CONTEST_LIST = 0, 1, 2, 3

def db_read():
    global handle_dict, contest_dict, last_upd_msg
    with shelve.open(DB_FILE) as db:
        handle_dict = db["handle"]
        contest_dict = db["contest"]
        last_upd_msg = db['mejai']

def db_commit(update_type = 3):
    global handle_dict, contest_dict, last_upd_msg
    with shelve.open(DB_FILE) as db:
        if update_type & CONTEST:
            db['mejai'] = last_upd_msg
            db["contest"] = contest_dict
        if update_type & USER:
            db['handle'] = handle_dict

# in-memory cache, no need to write in db since it's fast
submissions_dict = {}
submissions_last_upd = {}
submissions_last_request = {}

def initialize_db():
    logging.info('initialize db')
    with shelve.open(DB_FILE) as db:
        if 'mejai' not in db or 'contest' not in db or 'handle' not in db:
            logging.info('new db')
            db.clear() # reconstruct database
            db["contest"] = {}
            db['handle'] = {}
            db['mejai'] = None
    db_read()
    logging.info(last_upd_msg)

user_standing_worker_threshold = time.time() - 60 * 60

def update_users(input_handles=None):
    status, users = request_user_info(input_handles)
    if status != 'OK':
        logging.info(status + users)
        return False
    for user in users:
        handle = user['handle']
        handle_dict[handle] = user
        current_time = time.time()
        user['result_time'] = current_time
        global user_standing_worker_threshold
        user_standing_worker_threshold = current_time
    db_commit(USER)
    return len(users) > 0

def extend_users(handles):
    with dict_lock:
        handles = [h for h in handles if h not in handle_dict.keys()]

    if len(handles) > 0:
        return update_users(handles)
    else:
        return False # nothing has been done

def initialize_users():
    logging.info('initialize users')
    logging.info(f'users : {len(handle_dict)}')
    # if len(handle_dict) == 0:
        # initialize the handle set, with user information
    #    return extend_users(['tourist'])
    return False

MAX_HANDLES = 100

def update_contest(contest_id):
    global contest_dict
    with dict_lock:
        assert contest_id in contest_dict
        contest = contest_dict[contest_id]
        logging.info(f'loading contest {contest_id} : ' + contest['name'])
        handles = list(handle_dict.keys())[:MAX_HANDLES]
        if len(handles) == 0:
            return
    status, result = request_contest_standings(contest['id'], handles=handles)
    with dict_lock:
        if status != 'OK':
            logging.info(f'{status} : {result}')
            if 'disabled_until' in contest:
                count = contest['disabled_until'][0] + 1
                contest['disabled_until'] = (count, time.time() + (count ** 2) * 5 * 60)
            else:
                contest['disabled_until'] = (0, time.time() + 5 * 60)
        else:
            if 'disabled_until' in contest:
                contest.pop('disabled_until')
            contest['rows'] = result['rows']
            contest['problems'] = result['problems']
            contest['result_time'] = time.time()
            contest_dict[contest['id']] = contest
            global last_upd_msg
            last_upd_msg = f'Contest {contest["id"]} ({contest["name"]}) : {datetime.now().strftime("%B %d %Y %I:%M:%S %p")}, with last handle {handles[-1]}'
            logging.info(f'success : count = {len(result["rows"])} ' + last_upd_msg)
        # db_commit(CONTEST)

def update_contest_list():
    status, contests = request_contest_list ()
    if status != 'OK':
        logging.warning('load contest list failed: ' + contests)
        return False
    with dict_lock:
        global contest_dict
        for contest in contests:
            contest_id = contest['id']
            if contest_id not in contest_dict:
                contest['rows'] = []
                contest['problems'] = []
                contest_dict[contest['id']] = contest
            else:
                for key, value in contest.items():
                    contest_dict[contest['id']][key] = value
        contest_dict = dict(sorted(contest_dict.items(), key=lambda x:x[1]['startTimeSeconds'], reverse=True))
        assert contest_id in contest_dict
        db_commit(CONTEST)
        return True

def initialize_contests():
    logging.info('initialize contests')
    if len(contest_dict) > 0:
        return False
    update_contest_list()
    return True

def update_handle_submissions(handle):
    logging.info(f'handle update, acquiring {handle}')
    dict_lock.acquire()
    logging.info(f'update handle {handle}')

    assert handle in handle_dict

    if len(submissions_dict.get(handle, list())) > 0:
        # update
        old_submissions = submissions_dict[handle]
        old_latest_id = old_submissions[0]['id']
        dict_lock.release()
        
        for count in [100]:
            status, result = request_user_status(handle, 1, count)
            with dict_lock: # auto release
                if status != 'OK' or len(result):
                    break # retry

                if len(result) == 0:
                    submissions_dict[handle] = []
                    submissions_last_upd[handle] = time.time()
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
    else:
        dict_lock.release()

    # new
    logging.info(1)
    status, result = request_user_status(handle)
    logging.info(2)
    with dict_lock:
        logging.info(3)
        if status != 'OK':
            return status, result
        submissions_last_upd[handle] = time.time()
        submissions_dict[handle] = result
        return 'OK', len(result)

SUBMISSION_AUTO_THRESHOLD = 5 # seconds
TOO_MANY_REQUESTS = 20
INTERVAL = .5
CONTEST_LIST_THRESHOLD = 12 * 60 * 60 # seconds

job_queue = queue.Queue(TOO_MANY_REQUESTS)


last_task_complete = time.time() # init

last_upd_contest_list = 0

def should_update_handle_submissions(handle):
    if handle in submissions_last_upd and time.time() - submissions_last_upd[handle] < SUBMISSION_AUTO_THRESHOLD:
        return False
    return True

def worker():
    global last_task_complete, last_upd_contest_list, user_standing_worker_threshold
    while True:
        diff_time = time.time() - last_task_complete
        if diff_time < INTERVAL:
            time.sleep(INTERVAL - diff_time) # don't be so fast!
        request_time, job_type, name = job_queue.get() # (time, type, name)
        logging.info(f'job received : {request_time} {job_type} {name}')

        if job_type == SUB: # name = handle
            if name not in submissions_last_upd or should_update_handle_submissions(name):
                update_handle_submissions(name)
                logging.info("complete_time: " + str(submissions_last_upd[name] - request_time))
                last_task_complete = time.time()
        elif job_type == CONTEST: # name = id
            if name not in contest_dict or 'result_time' not in contest_dict[name] or contest_dict[name]['result_time'] <= request_time:
                update_contest(name)
                last_task_complete = time.time()
        else:
            if update_contest_list():
                current_time = time.time()
                last_upd_contest_list = current_time
                user_standing_worker_threshold = current_time
            last_task_complete = time.time()
        job_queue.task_done()



def worker_part_time():
    global user_standing_worker_threshold, last_upd_contest_list
    while True:
        job_queue.join()
        diff_time = time.time() - last_task_complete
        if diff_time < 5 * INTERVAL:
            time.sleep(5 * INTERVAL - diff_time) # don't be so fast!
            continue
        
        current_time = time.time()
        if current_time - last_upd_contest_list > CONTEST_LIST_THRESHOLD:
            try:
                job_queue.put_nowait((time.time(), CONTEST_LIST, None))
            except:
                logging.warning('the queue is filled in just a second. how could it be possible?')
        else:
            with dict_lock:
                found = False
                for contest in contest_dict.values():
                    if 'result_time' not in contest or contest['result_time'] < user_standing_worker_threshold:
                        if 'disabled_until' not in contest or contest['disabled_until'][1] < time.time():
                            found = True
                            job_queue.put((time.time(), CONTEST, contest['id'])) 
                            break
                if not found:
                    user_standing_worker_threshold = time.time()
                    db_commit()



def preprocess_handles(handles):
    if handles is None or len(handles) == 0 or len(handles) > 10000:
        raise Exception(f'bad handles : input len = {None if handles is None else len(handles)}')
    handles = split_handles(handles)
    
    if handles is None or len(handles) == 0 or len(handles) > 100:
        raise Exception(f'bad handles : len(handles) = {None if handles is None else len(handles)}')

    for handle in handles:
        if handle not in handle_dict.keys():
            raise Exception(f'You should add handle {handle} before query')

    return handles

def query_handles_contest(handles, page = 1, concerned = None):
    with dict_lock:
        logging.info('start query')
        handles = preprocess_handles(handles)

        if concerned is None:
            concerned = handles[0]
        assert concerned in handles
    
        is_new_to_submission = concerned not in submissions_last_upd

    too_many_msg = None
    '''
    if is_new_to_submission:
        logging.info('new handle')
        status, result  = update_handle_submissions(concerned)
        if status != 'OK':
            raise Exception(result)
    else:
    '''
    try:
        if concerned not in submissions_last_request or (
            concerned not in submissions_last_upd or
            submissions_last_request[concerned] < submissions_last_upd[concerned]
        ): # not in queue
            job_queue.put((time.time(), SUB, concerned), True, INTERVAL)
        else:
            logging.info('in queue, skipped')
    except Exception as e:
        logging.info(e)
        too_many_msg = True
    
    with dict_lock:

        logging.info('end update')
        
        rendered_handles = {}
        contest_list = []

        for handle in handles:
            rendered_handles[handle] = render_rated_handle(handle, handle_dict[handle].get('rank', ''))
        
        total = len(contest_dict)
        max_page = (total + 99) // 100
        page = min(page, max_page)
        page = max(page, 1)
        from_ = (page - 1) * 100 + 1
        to = from_ + 99
        from_ = max(from_, 1)
        to = min(to, total)

        contests = list(contest_dict.values())[from_-1:to]

        contest_concerned_submissions = {}
        contest_duration = {}
        for contest in contests:
            contest_concerned_submissions[contest['id']] = {}
            contest_duration[contest['id']] = contest['durationSeconds']
        NO, REJ, UP, AC = 0, 1, 2, 3
        concerned_verdicts = ['no', 'rejected', 'accepted-upsolve', 'accepted']

        concerned_submissions_list = submissions_dict.get(concerned, list())
        concerned_submissions_last_upd = submissions_last_upd.get(concerned, 'None')

        for submission in concerned_submissions_list:
            if 'contestId' not in submission:
                continue # e.g. acmsguru
            if 'verdict' not in submission:
                continue # e.g. running
            contest_id = submission['contestId']
            verdict = submission['verdict']
            Type = submission['author']['participantType']
            contested = Type != 'MANAGER' and Type != 'PRACTICE'
            if contest_id in contest_concerned_submissions:
                value = NO
                if verdict == 'OK':
                    value = AC if contested else UP
                elif verdict != 'COMPILATION_ERROR':
                    value = REJ
                # If it is, append the submission to the list of submissions for that contest
                old_value = contest_concerned_submissions[contest_id].get(submission['problem']['index'], NO)
                if old_value < value:
                    contest_concerned_submissions[contest_id][submission['problem']['index']] = value

        for contest in contests:
            standings = []

            contest_id = contest['id']
            concerned_submissions = contest_concerned_submissions[contest_id]
            for p in contest['problems']:
                p['concerned'] = concerned_submissions.get(p['index'], NO)
            for row in contest['rows']:
                party_members = [m['handle'] for m in row['party']['members']]
                participant_type = row['party']['participantType']
                is_watched = False
                is_concerned = False
                for member in party_members:
                    if member == concerned:
                        is_concerned = True
                        is_watched = True
                    elif member in handles:
                        is_watched = True
                if is_watched:
                    rendered_members = render_handles(party_members)
                    problem_results = []
                    for p, problem in zip(contest['problems'], row['problemResults']):
                        rejected = problem['rejectedAttemptCount']
                        if problem['points'] > 0:
                            if is_concerned:
                                p['concerned'] = max(p['concerned'], AC if participant_type != 'MANAGER' and participant_type != 'PRACTICE' else UP) 
                            state = 'y'
                            show = '+'
                        else:
                            if rejected > 0:
                                if is_concerned:
                                    p['concerned'] = max(p['concerned'], REJ) 
                                state = 'n'
                            else:
                                state = '0'
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
                    if 'penalty' in row:
                        row_dict['penalty'] = row['penalty']
                    if len(party_members) > 1:
                        row_dict['is_party'] = True
                    standings.append(row_dict)
            
            ac, rj, no = 0, 0, 0
            for p in contest['problems']:
                x = p['concerned']
                if x == REJ:
                    rj += 1
                elif x == NO:
                    no += 1
                else:
                    ac += 1
            if rj + no == 0 and ac > 0:
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
                'concerned_status': concerned_status,
                'result_time': parse_time(contest['result_time']) if 'result_time' in contest else None}
            contest_list.append(contest_return_dict)
        handles.remove(concerned)
        handles.insert(0, concerned)
        return {'concerned': concerned,
        'contests': contest_list,
        'contest_from' : from_,
        'contest_to' : to,
        'contest_total' : total,
        'pages': gen_page(page, max_page),
        'ids': ','.join(handles),
        'rendered_handles': rendered_handles,
        'last_upd_msg' : last_upd_msg,
        'recent_submissions' : concerned_submissions_list[:100],
        'recent_submissions_last_upd' : concerned_submissions_last_upd,
        'too_many_msg': too_many_msg,
        'submissions_updating': should_update_handle_submissions(concerned)}

def check_recent_submissions(handle, stamp):
    logging.info(handle)
    logging.info(stamp)
    logging.info(handle not in submissions_last_upd)
    with dict_lock:
        if handle not in submissions_last_upd or stamp == parse_time(submissions_last_upd[handle]):
            return 'WAITING', None
        return 'OK', {
        'concerned' : handle,
        'rendered_handles': {handle: render_rated_handle(handle, handle_dict[handle].get('rank', ''))},
        'recent_submissions' : submissions_dict.get(handle, list())[:100],
        'recent_submissions_last_upd' : submissions_last_upd.get(handle, None)
        }

def render_handles(handles):
    ret = []
    for h in handles:
        ret.append(render_rated_handle(h, handle_dict.get(h, dict()).get('rank', '')))
    return ret

def dump_all_handles():
    return render_handles(handle_dict.keys())