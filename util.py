from datetime import datetime, timedelta
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

def render_rated_handle(handle, rank):
    if isinstance(rank, str):
        return f'<span class="{color_from_rank(rank)}">{handle}</span>'
    else:
        return f'<span class="{color_from_rating(rank)}">{handle}</span>'

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
