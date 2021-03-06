from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session
)
from werkzeug.exceptions import abort

from .auth import login_required
from .db import get_db
import numpy as np
import os

bp = Blueprint('gridworld_app', __name__)

MAPS_PER_LEVEL = 4
MAX_MAPS_PER_LEVEL = 5
NUM_LEVELS = 3

COLORS = ['red', 'green', 'blue', 'black']
CONFIDENCES = ["very bad", "bad", "fair", "good", "very good"]
APP_PATH = "."#"/var/www/html/web_gridworld/web_gridworld"

@bp.route('/')
def index():
    if g.user is not None:
        return render_template('gridworld_app/prescreen.html')
    else:
        return render_template('gridworld_app/index.html', posts={})


@bp.route('/prescreen', methods=('POST',))
def prescreen():
    elements = ['english', 'vision', 'colorblind', 'age']
    response = ""
    total = 0
    for e in elements:
        response += request.form[e]
        total += int(request.form[e])

    db = get_db()
    db.execute('UPDATE user SET prescreen=? WHERE id = ?', (response, g.user['id'],))
    db.commit()

    if total != len(elements):
        return render_template('gridworld_app/end_study.html')
    return base_tutorial()


@bp.route('/playgame', methods=('GET', 'POST'))
@login_required
def playgame():
    db = get_db()
    u = db.execute('SELECT accuracy, competency FROM user WHERE id = ?', (g.user['id'],)).fetchone()
    accuracy_level = u[0]
    competency_level = u[1]
    report_level = session['level']
    report_level = session['l_order'][int(report_level)]
    confidence = ""

    if report_level == '0':
        map_number = '0'
        color = int(session['c_order'][int(session['c_ctr'])])
        map_path = os.path.join(APP_PATH,"flaskr/maps/map0")
    else:
        map_number = session['l' + report_level + '_order'][int(session['ctr'])]
        color = int(session['c_order'][int(session['c_ctr'])])
        map_path = os.path.join(APP_PATH,"flaskr/maps/level_" + report_level + "/map" + map_number)

        if int(report_level) == 2:
            if accuracy_level == 0:  # accurate confidence statements

                conf_path = "_confidence.txt"
                if competency_level == 1:
                    conf_path = "_confidence1.txt"

                with open(map_path + conf_path) as file:
                    for line in file.readlines():
                        confidence = line.strip()
                        break
            else:
                # randomize confidence statement
                rand_conf = CONFIDENCES[np.random.randint(0, len(CONFIDENCES))]
                confidence = "<b>Report:</b> The robot has <b>" + rand_conf \
                             + " confidence</b> in navigating to the green square."
        elif int(report_level) == 3:

            if accuracy_level == 0:  # accurate confidence statements

                conf_path = "_confidence.txt"
                if competency_level == 1:
                    conf_path = "_confidence1.txt"

                with open(map_path + conf_path) as file:
                    for line in file.readlines():
                        confidence = line.strip()
                        break
            else:
                # randomize confidence statement
                rand_conf1 = CONFIDENCES[np.random.randint(0, len(CONFIDENCES))]
                rand_conf2 = CONFIDENCES[np.random.randint(0, len(CONFIDENCES))]
                confidence = "<b>Report:</b> The robot has <b>" + rand_conf1 \
                             + " confidence</b> in navigating to the blue square, and <b>" + rand_conf2 \
                             + " confidence </b> in navigating from the blue square to the green square."

    confidence = confidence.replace('robot', '<u>' + COLORS[color] + ' robot</u>')
    obstacles = []
    dangers = []
    randomizers = []
    subgoal = []
    goal = []
    policy = []
    with open(map_path + "_policy.txt") as file:
        for line in file.readlines():
            line = line.strip()
            for l in line.split(','):
                policy.append(int(l))

    with open(map_path + ".txt") as file:
        for y, line in enumerate(file.readlines()):
            for x, c in enumerate(line):
                if c == 'o':
                    obstacles.append([x, y])
                if c == 'g':
                    randomizers.append([x, y])
                if c == 'd':
                    dangers.append([x, y])
                if c == 'G':
                    goal = [x, y]
                if c == 'r':
                    subgoal = [x, y]
                if c == 'a':
                    agent = [x, y]
    data = {
        'conf': confidence,
        'goal': goal,
        'subgoal': subgoal,
        'agent': agent,
        'obstacles': obstacles,
        'dangers': dangers,
        'randomizers': randomizers,
        'robot_color': COLORS[color],  # just color
        'report': report_level,  # level: no report, report, segmented report
        'competency': competency_level,  # level: competent (good), incompetent (random)
        'accuracy': accuracy_level,  # level: accurate, random
        'map_number': map_number,  # The reference number for this map
        'policy': policy  # The policy to execute
    }
    print(session)
    print("Rendering new map:")
    print("  map_number={}".format(map_number))
    print("  color={}".format(COLORS[color]))
    print("  report={}".format(report_level))
    print("  competency={}".format(competency_level))
    print("  accuracy={}".format(accuracy_level))
    return render_template('gridworld_app/gridworld_game.html', start_data=data)


@bp.route('/endgame', methods=('GET', 'POST'))
@login_required
def endgame():
    if request.method == 'POST':
        js = request.get_json()
        js = js['postData']
        print("RECEIVED :" + str(js))

        score = 5.0
        if js['outcome'] == 'ABORT':
            score -= 3.0
        if int(js['h_steps']) > 0:
            score -= int(js['h_steps'])*0.1
        if js['outcome'] == 'DEAD':
            score = 0.0
        if score <= 0.0:
            score = 0.0

        db = get_db()
        db.execute(
            'INSERT INTO results '
            '(user_id, tot_mission_time_s, tot_mission_steps, path, map_number, accuracy_level, competency_level, report_level, confidence, score) '
            ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (g.user['id'],  js['t_mission_time'], js['t_mission_steps'], str(js['path']), js['map_num'], js['accuracy'],
             js['competency'], js['report'], js['conf'], str(score))
        )
        db.commit()

        session['score'] = str(score)
        session['ctr'] = str(int(session['ctr']) + 1)
        if session['level'] == '0':
            session['level'] = '1'
            session['ctr'] = '0'
            print("changing level")
        elif int(session['ctr']) % MAPS_PER_LEVEL == 0:
            session['level'] = str(int(session['level']) + 1)
            session['ctr'] = '0'
            print("changing level")

    return render_template('gridworld_app/outcome.html', post={'score': session['score']})


@bp.route('/outcome', methods=('GET', 'POST'))
@login_required
def outcome():
    if session['ctr'] == '0':
        color = int(session['c_order'][int(session['c_ctr'])])
        color = COLORS[color]
        level = 4 if int(session['l_order'][int(session['level'])-1]) >= 1 else 1
        print("color "+session['c_order'])
        print(int(session['l_order'][int(session['level'])-1]))
        print("order "+session['l_order'])
        print("level  "+session['level'])
        session['c_ctr'] = str(int(session['c_ctr'])+1)
        post = {"color": color, "level": int(level)}
        return render_template('gridworld_app/mdmt.html', post=post)
    return playgame()


@bp.route('/trust_question', methods=('POST',))
@login_required
def trust_question():
    elements = ['reliable', 'capable', 'predictable',
                'skilled', 'someone_you_can_count_on',
                'competent', 'consistent', 'meticulous']
    response = ""
    for e in elements:
        response += request.form[e]

    tutorial = session['l_order'][int(session['level'])]
    if session['level'] == '1':
        color = int(session['c_order'][int(session['c_ctr'])])
        color = COLORS[color]
        db = get_db()
        db.execute('UPDATE user SET practice_trust = ? WHERE id = ?', (response, g.user['id'],))
        db.commit()
        return render_template('gridworld_app/tutorial'+tutorial+'.html', post={"color": color})
    elif session['level'] == '2':
        color = int(session['c_order'][int(session['c_ctr'])])
        color = COLORS[color]
        db = get_db()
        db.execute('UPDATE user SET first_trust = ? WHERE id = ?', (response, g.user['id'],))
        db.commit()
        return render_template('gridworld_app/tutorial'+tutorial+'.html', post={"color": color})
    elif session['level'] == '3':
        color = int(session['c_order'][int(session['c_ctr'])])
        color = COLORS[color]
        db = get_db()
        db.execute('UPDATE user SET second_trust = ? WHERE id = ?', (response, g.user['id'],))
        db.commit()
        return render_template('gridworld_app/tutorial'+tutorial+'.html', post={"color": color})
    elif session['level'] == '4':
        db = get_db()
        db.execute('UPDATE user SET third_trust = ? WHERE id = ?', (response, g.user['id'],))
        db.commit()
        return render_template('gridworld_app/open_question.html', post={})


@bp.route('/open_question', methods=('GET', 'POST'))
@login_required
def open_question():
    if request.method == 'POST':
        open_q = request.form['open_text']
        age = request.form['age']
        gender = request.form['gender']
        education = request.form['education']

        db = get_db()
        db.execute('UPDATE user SET open_question=?, age=?, gender=?, education=? WHERE id = ?',
                   (open_q, age, gender, education, g.user['id'],))
        db.commit()

    db = get_db()
    u = db.execute('SELECT code FROM user WHERE id = ?', (g.user['id'],)).fetchone()
    completion_code = u[0]
    session.clear()
    return render_template('gridworld_app/thank_you.html', post={'code': completion_code})


@bp.route('/base_tutorial', methods=('GET', 'POST'))
@login_required
def base_tutorial():
    # choose color order from [red, green, blue]
    color_order = np.random.choice([0, 1, 2, 3], 4, replace=False)
    # choose accuracy level from [accurate, random]
    accuracy_level = np.random.randint(0, 2)
    # choose competency level from [competent, random]
    competency_level = np.random.randint(0, 2)
    # choose a completion code for the user (hopefully this is random enough)
    completion_code = "NC-"+str(np.random.randint(111111111, 999999999))+"-HRT"
    # get the client IP address
    client_ip = str(request.remote_addr)

    level_0_map_order = np.random.choice(np.arange(0, MAX_MAPS_PER_LEVEL), MAPS_PER_LEVEL, replace=False)
    level_1_map_order = np.random.choice(np.arange(0, MAX_MAPS_PER_LEVEL), MAPS_PER_LEVEL, replace=False)
    level_2_map_order = np.random.choice(np.arange(0, MAX_MAPS_PER_LEVEL), MAPS_PER_LEVEL, replace=False)
    level_order = np.random.choice(np.arange(1, NUM_LEVELS+1), NUM_LEVELS, replace=False)

    session['l1_order'] = "".join([str(x) for x in level_0_map_order])
    session['l2_order'] = "".join([str(x) for x in level_1_map_order])
    session['l3_order'] = "".join([str(x) for x in level_2_map_order])
    session['c_order'] = "".join([str(x) for x in color_order])
    session['l_order'] = '0'+"".join([str(x) for x in level_order])+"4"
    session['level'] = '0'
    session['ctr'] = '0'
    session['score'] = '0'
    session['c_ctr'] = '0'

    db = get_db()
    db.execute(
        'UPDATE user SET accuracy=?, competency=?, code=?, client_ip=? WHERE id = ?',
        (accuracy_level, competency_level, completion_code, client_ip, g.user['id'],))
    db.commit()
    print("Setting up new participant:")
    print("  IP addr={}".format(client_ip))
    print("  color_order={}".format([COLORS[x] for x in color_order]))
    print("  accuracy_level={}".format("accurate" if accuracy_level == 0 else "random"))
    print("  competency_level={}".format("accurate" if competency_level == 0 else "random"))
    print("  completion_code={}".format(completion_code))
    print("  level_order={}".format(session['l_order']))

    post = {'title': 'tutorial'}
    return render_template('gridworld_app/base_tutorial.html', post=post)


@bp.route('/base_quiz', methods=('GET', 'POST'))
@login_required
def base_quiz():
    elements = ['info', 'manual', 'false', 'automatic', 'hole', 'glass']
    response = ""
    for e in elements:
        response += request.form[e]
    print(response)
    color = int(session['c_order'][int(session['c_ctr'])])
    color = COLORS[color]
    db = get_db()
    db.execute('UPDATE user SET base_quiz = ? WHERE id = ?', (response, g.user['id'],))
    db.commit()
    return render_template('gridworld_app/base_tutorial_answers.html', post={"color": color})


@bp.route('/quiz1', methods=('GET', 'POST'))
@login_required
def quiz1():
    elements = ['info', 'control', 'false']
    response = ""
    for e in elements:
        response += request.form[e]
    print(response)
    db = get_db()
    db.execute('UPDATE user SET quiz1 = ? WHERE id = ?', (response, g.user['id'],))
    db.commit()
    return render_template('gridworld_app/tutorial1_answers.html', post={})


@bp.route('/quiz2', methods=('GET', 'POST'))
@login_required
def quiz2():
    elements = ['info', 'conf', 'badConf', 'false', 'goodConf', 'fairConf']
    response = ""
    for e in elements:
        response += request.form[e]
    print(response)
    db = get_db()
    db.execute('UPDATE user SET quiz2 = ? WHERE id = ?', (response, g.user['id'],))
    db.commit()
    return render_template('gridworld_app/tutorial2_answers.html', post={})


@bp.route('/quiz3', methods=('GET', 'POST'))
@login_required
def quiz3():
    elements = ['info', 'false', 'conf', 'badConf', 'goodConf', 'fairConf']
    response = ""
    for e in elements:
        response += request.form[e]
    print(response)
    db = get_db()
    db.execute('UPDATE user SET quiz3 = ? WHERE id = ?', (response, g.user['id'],))
    db.commit()
    return render_template('gridworld_app/tutorial3_answers.html', post={})


@bp.route('/end_study', methods=('GET', 'POST'))
def end_study():
    session.clear()
    return redirect(url_for('end_study'))
