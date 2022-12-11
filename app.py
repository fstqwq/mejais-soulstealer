from flask import Flask, render_template, request, url_for
import requests, json
from jinja2.filters import FILTERS
from apscheduler.schedulers.background import BackgroundScheduler

from util import *
from legacy_request_codeforces import *

app = Flask(__name__)
app.config.from_pyfile('config.py')

FILTERS['color_from_rank'] = color_from_rank
FILTERS['color_from_rating'] = color_from_rating

scheduler = BackgroundScheduler()
scheduler.add_job(update_contests, 'interval', seconds=30, max_instances=1)
scheduler.start()

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
    if expand_users([id]):
        return render_template('index.html', data={'success_info' : 'OK ' + id})
    else:
        return render_template('index.html', data={'info' : 'FAILED ' + id})

@app.route('/show', methods=['POST', 'GET'])
def show():
    if request.method == 'POST':
        ids = request.form['ids']
    else:
        ids = request.args['ids']
    try:
        data = query_handles_contest(ids)
    except Exception as e:
        return render_template('index.html', data={'err_msg' : str(e)})
    return render_template('show.html', data=data)

def init():
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    initialize_db()
    initialize_users()
    initialize_contests()

if __name__ == '__main__':
    init()
    app.run(host='0.0.0.0',port=11451)