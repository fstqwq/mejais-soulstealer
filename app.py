from flask import Flask, render_template, request, url_for, jsonify
from jinja2.filters import FILTERS
import sys, threading

from util import *
from fetcher import *
from legacy_request_codeforces import *

from config import * # SECRET_KEY

app = Flask(__name__)
app.config.from_pyfile('config.py')

with app.app_context():
    FILTERS['color_from_rank'] = color_from_rank
    FILTERS['color_from_rating'] = color_from_rating
    FILTERS['render_handles'] = render_handles
    FILTERS['shorten_cf_round_names'] = shorten_cf_round_names
    FILTERS['parse_time'] = parse_time
    FILTERS['parse_verdict'] = parse_verdict
    FILTERS['parse_submission_link'] = parse_submission_link
    FILTERS['parse_problem_link'] = parse_problem_link
    FILTERS['parse_contest_link'] = parse_contest_link
    app.jinja_env.globals.update(dump_all_handles=dump_all_handles)


    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    initialize_db()
    initialize_users()
    initialize_contests()
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=worker_part_time, daemon=True).start()

@app.route('/')
def index_page():
    return render_template('index.html', data={})

@app.route('/query', methods=['POST'])
def submit():
    return jsonify({'status': 'DEPRECATED'}),200,{"ContentType":"application/json"}
    cf_id = request.form['cf']
    concerned = cf_id.split(';')[0]
    return render_template('query.html', contests=request_codeforces(cf_id), rated_color=cf_community_rated_color(cf_id), concerned = concerned)

@app.route('/faq', methods=['GET'])
def faq():
    return render_template('faq.html')

@app.route('/add', methods=['POST'])
def add():
    id = request.form['add']
    if id.startswith(SECRET_KEY):
        id = split_handles(id[len(SECRET_KEY):])
    else:
        id = [id]
    if extend_users(id):
        return render_template('index.html', data={'success_info' : 'OK ' + str(id)})
    else:
        return render_template('index.html', data={'warning_info' : 'FAILED ' + str(id)})

@app.route('/show', methods=['GET'])
def show():
    try:
        ids = request.args['ids']
        if 'page' in request.args:
            page = int(request.args['page'])
        else:
            page = 1
        if 'main' in request.args and len(request.args['main']) > 0:
            concerned = request.args['main']
        else:
            concerned = None
        data = query_handles_contest(ids, page=page, concerned=concerned)
    except Exception as e:
        return render_template('index.html', data={'err_msg' : e})
    return render_template('show.html', data=data)

@app.route('/recent_submission', methods=['GET'])
def recent_submission():
    try:
        id = request.args['id']
        stamp = request.args['last']
        status, data = check_recent_submissions(id, stamp.replace('Last update: ', ''))
    except Exception as e:
        return jsonify({'status': 'FAILED', 'comment' : e}),200,{"ContentType":"application/json"}
    if status == 'OK':
        return jsonify({'status': 'OK', 'result': render_template('recent_submission', data=data)}),200,{"ContentType":"application/json"}
    else:
        return jsonify({'status': 'WAITING'}),200,{"ContentType":"application/json"}

def main(argv):
    port = 11451
    debug = True
    app.run(host=argv[0], port=port, debug=debug)

if __name__ == '__main__':
    # app.run(host='::',port=11451)
    print("Python {0:s} {1:d}bit on {2:s}\n".format(" ".join(item.strip() for item in sys.version.split("\n")), 64 if sys.maxsize > 0x100000000 else 32, sys.platform))
    main(sys.argv[1:])
    print("\nDone.")