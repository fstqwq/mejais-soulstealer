import shelve
import time
from requester import *
from util import *

DB_FILE = 'mejai.db'

handle_dict = {}
contest_dict = {}

def initialize_db():
    logging.info('initialize db')
    with shelve.open(DB_FILE) as db:
        if 'mejai' not in db: # token that when a databased initialized successufully
            logging.info('new db')
            db.clear() # reconstruct database
            db["contest"] = {}
            db['handle'] = {}
            db['mejai'] = True
        else:
            logging.info('ok db')
            global handle_dict, contest_dict
            handle_dict = db["handle"]
            contest_dict = db["contest"]

def commit():
    with shelve.open(DB_FILE) as db:
        db["contest"] = contest_dict
        db['handle'] = handle_dict

def update_users(input_handles=None):
    status, users = request_user_info(handle_dict.keys() if not input_handles else input_handles)
    if status != 'OK':
        logging.info(status + users)
        return False
    for user in users:
        handle = user['handle']
        print(user)
        handle_dict[handle] = user
    commit()
    return True

def expand_users(handles):
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
        """
        status, users = request_user_ratedList(False, True)
        if status == 'OK':
            logging.info(f'received users = {len(users)}')
            users = users[:600] # debug
            for user in users:
                handle = user['handle']
                handle_dict[handle] = user
            logging.info(f'users : {len(handle_dict)}')
            commit()
            return True
        else:
            logging.warning("request failed : " + user)
            return False
        """
        return expand_users(['tourist'])
    return False
    # return update_users()

def update_contests():
    for contest in contest_dict.values():
        logging.info(f'loading contest {contest["id"]} : ' + contest['name'])
        status, result = request_contest_standings(contest['id'], handles=handle_dict.keys())
        if status != 'OK':
            logging.info(f'failed : {result}')
        else:
            result['result_time'] = int(time.time())
            for k, v in result['contest'].items():
                result[k] = v
            result.pop('contest')
            contest_dict[contest['id']] = result
            logging.info(f'success : count = {len(result["rows"])}')

def initialize_contests():
    logging.info('initialize contests')
    if len(contest_dict) > 0:
        return False
    status, contests = request_contest_list ()
    if status != 'OK':
        logging.warning('load contest list failed: ' + contests)
        return False
    contests = contests[:25]
    for contest in contests:
        logging.info(f'loading contest {contest["id"]} : ' + contest['name'])
        status, result = request_contest_standings(contest['id'], handles=handle_dict.keys())
        if status != 'OK':
            logging.info(f'failed : {result}')
        else:
            result['result_time'] = int(time.time())
            for k, v in result['contest'].items():
                result[k] = v
            result.pop('contest')
            contest_dict[contest['id']] = result
            logging.info(f'success : count = {len(result["rows"])}')
    commit()
    return True

def query_handles_contest(handles, from_ = 1, to = 100, main_concerned = None):
    if handles is None or len(handles) == 0:
        logging.info('handles = ' + str(handles))
        raise Exception('bad handle: ' + handles)
    if isinstance(handles, str):
        if ' ' in handles:
            handles = handles.split()
        elif ';' in handles:
            handles = handles.split(';')
        elif ',' in handles:
            handles = handles.split(',')
        else:
            handles = handles.split()
        handles = [handle.replace(',', '').replace(';', '').replace(' ', '') for handle in handles]
    if handles is None or len(handles) == 0:
        logging.info('handles = ' + str(handles))
        return []
    new_handles = []
    for handle in handles:
        if handle not in handle_dict.keys():
            logging.info('new handle ' + handle)
            new_handles.append(handle)
    
    if len(new_handles):
        expand_users (new_handles)
        for handle in new_handles:
            if handle not in handle_dict:
                raise Exception(handle + ' does not exist!')

    assert len(handles) > 0
    if main_concerned is None:
        main_concerned = handles[0]
    assert main_concerned in handles


    
    rendered_handles = {}
    contest_list = []

    for handle in handles:
        rendered_handles[handle] = render_rated_handle(handle, handle_dict[handle]['rank'])

    contests = list(contest_dict.values())
    contests = sorted(contests, key=lambda x:x['startTimeSeconds'], reverse=True)[max(0, from_-1):min(len(contests), to)]
    for contest in contests:
        standings = []
        for p in contest['problems']:
            p['concerned'] = 'no'
        
        for row in contest['rows']:
            party_members = [m['handle'] for m in row['party']['members']]
            is_watched = False
            is_concerned = False
            for member in party_members:
                if member == main_concerned:
                    is_concerned = True
                    is_watched = True
                elif member in handles:
                    is_watched = True
            if is_watched:
                rendered_members = [render_rated_handle(member,
                    handle_dict[member]['rank']) for member in party_members]
                problem_results = []
                for p, problem in zip(contest['problems'], row['problemResults']):
                    rejected = problem['rejectedAttemptCount']
                    if problem['points'] > 0:
                        state = 'accepted'
                        show = '+'
                        if is_concerned:
                            if row['party']['participantType'] != 'PRACTICE':
                                p['concerned'] = 'accepted'
                            elif p['concerned'] != 'accepted':
                                p['concerned'] = 'accepted-upsolve'
                    else:
                        state = 'rejected' if rejected > 0 else 'no'
                        show = '-'
                        if is_concerned and p['concerned'] == 'no':
                            p['concerned'] = state
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
    return {'concerned': main_concerned, 'contests': contest_list, 'rendered_handles': rendered_handles}