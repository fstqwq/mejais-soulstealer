from flask import Flask, render_template, request, url_for
from jinja2.filters import FILTERS
from apscheduler.schedulers.background import BackgroundScheduler

import sys, subprocess, threading

from util import *
from fetcher import *
from legacy_request_codeforces import *

app = Flask(__name__)
app.config.from_pyfile('config.py')

def init():
    FILTERS['color_from_rank'] = color_from_rank
    FILTERS['color_from_rating'] = color_from_rating
    FILTERS['render_handles'] = render_handles
    FILTERS['shorten_cf_round_names'] = shorten_cf_round_names
    FILTERS['parse_time'] = parse_time
    FILTERS['parse_verdict'] = parse_verdict
    FILTERS['parse_submission_link'] = parse_submission_link
    FILTERS['parse_problem_link'] = parse_problem_link
    app.jinja_env.globals.update(dump_all_handles=dump_all_handles)


    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    initialize_db()
    initialize_users()
    initialize_contests()

@app.route('/')
def index_page():
    return render_template('index.html', data={})

@app.route('/query', methods=['POST'])
def submit():
    cf_id = request.form['cf']
    concerned = cf_id.split(';')[0]
    return render_template('query.html', contests=request_codeforces(cf_id), rated_color=cf_community_rated_color(cf_id), concerned = concerned)

@app.route('/faq', methods=['GET'])
def faq():
    return render_template('faq.html')

@app.route('/add', methods=['POST'])
def add():
    id = request.form['add']
    if extend_users([id]):
        return render_template('index.html', data={'success_info' : 'OK ' + id})
    else:
        return render_template('index.html', data={'warning_info' : 'FAILED ' + id})

@app.route('/show', methods=['POST', 'GET'])
def show():
    if request.method == 'POST':
        ids = request.form['ids']
    else:
        ids = request.args['ids']
    try:
        data = query_handles_contest(ids)
    except Exception as e:
        return render_template('index.html', data={'err_msg' : e})
    return render_template('show.html', data=data)

def run_flask(host):
    return subprocess.call([sys.executable, sys.argv[0], host])

def main(argv):
    port = 11451
    debug = True

    if argv:
        init()
        app.run(host=argv[0], port=port, debug=debug)
    else:
        hosts = [
            "0.0.0.0",
            "::",
        ]
        threads = list()
        for host in hosts:
            threads.append(threading.Thread(target=run_flask, args=(host,)))

        for idx, thread in enumerate(threads):
            print("Starting on {0:s}:{1:d}".format(hosts[idx], port))
            thread.start()

if __name__ == '__main__':
    # app.run(host='::',port=11451)
    print("Python {0:s} {1:d}bit on {2:s}\n".format(" ".join(item.strip() for item in sys.version.split("\n")), 64 if sys.maxsize > 0x100000000 else 32, sys.platform))
    main(sys.argv[1:])
    print("\nDone.")