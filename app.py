from flask import Flask, render_template, request, url_for
import requests
from datetime import datetime, timedelta


app = Flask(__name__)
app.config.from_pyfile('config.py')


@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def submit():
    cf_id = request.form['cf']
    at_id = request.form['at']
    return render_template('query.html', table_html=request_codeforces(cf_id))

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
    url = 'https://codeforces.com/api/user.status'
    params = {
        'handle': id,
        'from': 1,
        'count': 10,
        'key': 'CF_API_KEY',
        'secret': 'CF_API_SECRET'
    }
    response = requests.get(url, params=params)
    response_data = response.json()
    status = response_data['status']
    if status != 'OK':
        return status
    
    # Create HTML table
    html = create_table_html(response_data['result'])
    return html


if __name__ == '__main__':
    app.run()