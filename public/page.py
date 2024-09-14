from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
import sqlite3
from public.auth import login_required
from public.db import get_db
from datetime import datetime

bp = Blueprint('page', __name__)


@bp.route('/')
def index():
    db = get_db()
    users = db.execute(
        'SELECT username, points, correct_scores, id '
        'FROM user '
        'WHERE points >= 0 '
        'ORDER BY points DESC, correct_scores DESC'
    ).fetchall()

    users2 = []
    i = 1  # Miejsce
    j = 1  # Zmienna pomocnicza do śledzenia aktualnej pozycji
    k = 0  # Indeks użytkownika

    for k, user in enumerate(users):
        user_as_tuple = tuple(user)
        if k > 0 and user[1] == users[k - 1][1] and user[2] == users[k - 1][2]:
            j += 1
        else:
            i = j
            j += 1

        place = i
        user2 = user_as_tuple + (place,)
        users2.append(user2)

    return render_template('page/index.html', users2=users2)


@bp.route('/add_bet')
@login_required
def add_bet():
    db = get_db()

    # Pobieranie bieżącej daty i godziny
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_hour = int(now.strftime("%H"))

    # Pobieranie meczów na dzisiejszy dzień
    matches = db.execute(
        'SELECT id, country1, country2, date, hour '
        'FROM matches '
        'WHERE date = ? '
        'ORDER BY hour', (current_date,)
    ).fetchall()

    # Pobieranie zakładów użytkownika na dzisiejsze mecze
    your_bets = db.execute(
        'SELECT bets.user_id, bets.match_id, bets.result1, bets.result2, matches.country1, matches.country2 '
        'FROM bets '
        'INNER JOIN matches ON bets.match_id = matches.id '
        'WHERE bets.user_id = ? AND bets.match_id IN ( '
        '    SELECT id FROM matches WHERE date = ? '
        ') '
        'ORDER BY matches.hour', (g.user[0], current_date)
    ).fetchall()

    return render_template('page/add_bet.html', your_bets=your_bets, matches=matches,
                           current_date=current_date, current_hour=current_hour)


@bp.route('/bets')
def bets():
    db = get_db()
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_hour = int(datetime.now().strftime("%H"))

    # Pobierz wszystkie mecze na dany dzień
    matches = db.execute(
        'SELECT id, country1, country2, date, hour'
        ' FROM matches'
        ' WHERE date = ?'
        ' ORDER BY hour',
        (current_date,)
    ).fetchall()

    # Pobierz wszystkich użytkowników
    user_list = db.execute(
        'SELECT id, username'
        ' FROM user'
        ' WHERE points >= 0'
        ' ORDER BY points DESC, correct_scores DESC'
    ).fetchall()

    id_to_username = {user_id: username for user_id, username in user_list}
    lista_id = set(id_to_username.keys())  # Zmieniamy na zbiór dla efektywniejszego wyszukiwania

    # Pobierz wszystkie typy na dany dzień
    typy = db.execute(
        'SELECT bets.user_id, bets.match_id, bets.result1, bets.result2, user.username'
        ' FROM bets'
        ' INNER JOIN user ON bets.user_id = user.id'
        ' WHERE bets.match_id IN (SELECT id FROM matches WHERE date = ?)'
        ' ORDER BY bets.match_id, bets.result1, bets.result2',
        (current_date,)
    ).fetchall()

    # Organizujemy dane typów według meczów
    bets_by_match = {}
    for typ in typy:
        match_id = typ[1]
        if match_id not in bets_by_match:
            bets_by_match[match_id] = set()
        bets_by_match[match_id].add(typ[0])

    # Lista użytkowników, którzy nie dodali typów do każdego meczu
    missing_bets = {match_id: lista_id - users_who_betted for match_id, users_who_betted in bets_by_match.items()}

    # Przekształcamy na listę nazw użytkowników dla każdego meczu
    missing_bets_names = {
        match_id: [id_to_username[user_id] for user_id in missing_users]
        for match_id, missing_users in missing_bets.items()
    }

    # Przygotowujemy wyniki do renderowania
    win, draw, lose = [], [], []
    for typ in typy:
        if typ[2] - typ[3] > 0:
            win.append(typ)
        elif typ[2] - typ[3] == 0:
            draw.append(typ)
        else:
            lose.append(typ)

    twoje_typy2 = {match_id: sum(1 for typ in typy if typ[1] == match_id) for match_id in [match[0] for match in matches]}

    return render_template('page/bets.html', win=win, draw=draw, lose=lose, id_to_username=id_to_username,
                           missing_bets_names=missing_bets_names, lista_id=lista_id, current_hour2=current_hour,
                           typy=typy, twoje_typy2=twoje_typy2, matches=matches, current_date=current_date
    )


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if g.user['username'] == 'Smolar':
        if request.method == 'POST':
            country1 = request.form.get('country1', '').strip()
            country2 = request.form.get('country2', '').strip()
            date = request.form.get('date', '').strip()
            hour = request.form.get('hour', '').strip()

            error = None

            if not country1:
                error = 'Wpisanie pierwszego kraju jest wymagane.'
            elif not country2:
                error = 'Wpisanie drugiego kraju jest wymagane.'
            elif not date:
                error = 'Wpisanie daty jest wymagane.'

            if error is not None:
                flash(error)
            else:
                db = get_db()
                try:
                    db.execute(
                        'INSERT INTO matches (country1, country2, date, hour) VALUES (?, ?, ?, ?)',
                        (country1, country2, date, hour)
                    )
                    db.commit()
                    flash('Mecz został dodany pomyślnie!')
                    return redirect(url_for('page.index'))
                except Exception as e:
                    db.rollback()
                    flash(f'Wystąpił błąd: {str(e)}')

        return render_template('page/create.html')
    else:
        flash("Nie masz uprawnień do dodawania meczów")
        return redirect(url_for('page.index'))


def get_post(id):
    db = get_db()
    match = db.execute(
        'SELECT * FROM matches WHERE id = ?', (id,)
    ).fetchone()

    if match is None:
        abort(404, "Mecz o podanym id nie istnieje.".format(id))

    return match


@bp.route('/longterm', methods=('GET', 'POST'))
def longterm():
    db = get_db()
    start_date = datetime.now()
    current_hour = int(start_date.strftime("%H"))
    day = int(start_date.strftime("%d"))
    longterm_bets = db.execute(
        ' SELECT long_term.user_id, long_term.top_scorer, long_term.winner, long_term.w_poss, long_term.ts_poss, user.username'
        ' FROM long_term'
        ' INNER JOIN user ON long_term.user_id = user.id'
        ' ORDER BY long_term.winner ASC'
    ).fetchall()

    # your_bets = db.execute(
    #    ' SELECT top_scorer, winner'
    #    ' FROM long_term'
    #    ' WHERE user_id = ?', (g.user[0],)
    # ).fetchall()

    # if len(your_bets) == 0:
    #    your_bets = [[None, None]]
    #    your_bets[0][0] = "brak"
    #    your_bets[0][1] = "brak"

    if request.method == 'POST':
        top_scorer = (request.form['top_scorer'])
        winner = (request.form['winner'])
        error = None

        if not top_scorer and not winner:
            error = 'Musisz wpisać swoje typy!'

        db = get_db()

        if error is not None:
            flash(error)

        db = get_db()
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute('SELECT * FROM long_term')
        check = cur.fetchall()
        long_term_id = []

        if db.execute(
                'SELECT top_scorer FROM long_term WHERE user_id = ?', (g.user['id'],)
        ).fetchone() is None:
            db.execute(
                'INSERT INTO long_term (user_id, winner, top_scorer)'
                ' VALUES (?, ?, ?)', (g.user['id'], winner, top_scorer)
            )
            db.commit()
        else:
            db.execute(
                'UPDATE long_term SET top_scorer = ?, winner = ?'
                'WHERE user_id = ?', (top_scorer, winner, g.user['id'])
            )
            db.commit()

        return redirect(url_for('page.longterm'))

    return render_template('page/longterm.html', longterm_bets=longterm_bets,
                           current_hour=current_hour, day=day)


@bp.route('/profile/<int:id>')
def profile(id):
    db = get_db()

    # Pobierz zakłady użytkownika
    user_bets = db.execute(
        'SELECT bets.user_id, bets.match_id, bets.result1, bets.result2, matches.country1, matches.country2, matches.result1 AS match_result1, matches.result2 AS match_result2'
        ' FROM bets'
        ' INNER JOIN matches ON bets.match_id = matches.id'
        ' WHERE bets.user_id = ? AND matches.result1 IS NOT NULL'
        ' ORDER BY matches.date, matches.hour',
        (id,)
    ).fetchall()

    # Pobierz dane użytkownika
    user = db.execute(
        'SELECT username, points, correct_scores'
        ' FROM user'
        ' WHERE id = ?',
        (id,)
    ).fetchone()

    if user is None:
        abort(404, description="Użytkownik o podanym ID nie istnieje.")

    return render_template('page/profile.html', user=user, user_bets=user_bets)

    def calculate_points(bet1, bet2, res1, res2):
        points = 0
        bet_res = bet1 - bet2
        res = res1 - res2
        if bet1 == res1 and bet2 == res2:
            points += 3
        elif res > 0 and bet_res > 0:
            points += 1
        elif res == bet_res:
            points += 1
        elif res < 0 and bet_res < 0:
            points += 1
        else:
            points += 0
        return points

    user_bets2 = []
    for bet in user_bets:
        bet_as_tuple = tuple(bet)
        points = calculate_points(bet[2], bet[3], bet[6], bet[7])
        if points == 3:
            color = "green"
        elif points == 1:
            color = "yellow"
        else:
            color = "red"
        user_bet2 = bet_as_tuple + (points,)
        user_bet2 = user_bet2 + (color,)
        user_bets2.append(user_bet2)

    return render_template('page/profile.html', user_bets=user_bets, user_bets2=user_bets2, users=users)


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    match = get_post(id)

    if request.method == 'POST':
        country1 = request.form.get('country1')
        country2 = request.form.get('country2')
        result1 = request.form.get('result1')
        result2 = request.form.get('result2')
        error = None

        if not country1 or not country2:
            error = 'Both countries are required.'

        db = get_db()
        current_results = db.execute(
            'SELECT result1, result2 FROM matches WHERE id = ?',
            (id,)
        ).fetchone()

        if current_results and current_results[0] is not None and current_results[1] is not None:
            error = 'Match is already finished'

        if error is not None:
            flash(error)
        else:
            if result1 is not None and result2 is not None:
                db.execute(
                    'UPDATE matches SET result1 = ?, result2 = ? WHERE id = ?',
                    (result1, result2, id)
                )
                db.commit()
                points_update(id)
            else:
                db.execute(
                    'UPDATE matches SET country1 = ?, country2 = ? WHERE id = ?',
                    (country1, country2, id)
                )
                db.commit()

            return redirect(url_for('page.index'))

    return render_template('page/update.html', match=match)


@bp.route('/<int:id>/bet', methods=('GET', 'POST'))
@login_required
def bet(id):
    match = get_post(id)
    current_date = datetime.now()
    current_hour = int(current_date.strftime("%H"))

    db = get_db()
    hour = db.execute(
        'SELECT result1, result2, hour FROM matches WHERE id = ?',
        (id,)
    ).fetchone()

    if request.method == 'POST':
        try:
            result1 = int(request.form['result1'])
            result2 = int(request.form['result2'])
        except ValueError:
            flash('Musisz wpisać liczby.')
            return render_template('page/bet.html', hour=hour, match=match, current_hour=current_hour)

        # Check if match is over
        if hour[0] is not None and hour[1] is not None:
            flash('Mecz jest skończony.')
            return render_template('page/bet.html', hour=hour, match=match, current_hour=current_hour)

        db = get_db()
        # Check if user has already placed a bet on this match
        existing_bet = db.execute(
            'SELECT * FROM bets WHERE user_id = ? AND match_id = ?',
            (g.user['id'], id)
        ).fetchone()

        if existing_bet is None:
            db.execute(
                'INSERT INTO bets (user_id, match_id, result1, result2) VALUES (?, ?, ?, ?)',
                (g.user['id'], id, result1, result2)
            )
        else:
            db.execute(
                'UPDATE bets SET result1 = ?, result2 = ? WHERE user_id = ? AND match_id = ?',
                (result1, result2, g.user['id'], id)
            )
        db.commit()

        return redirect(url_for('page.add_bet'))

    return render_template('page/bet.html', hour=hour, match=match, current_hour=current_hour)


def points_update(id):
    db = get_db()
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    # Pobierz wynik meczu
    result = cur.execute(
        'SELECT result1, result2 FROM matches WHERE id = ?',
        (id,)
    ).fetchone()

    if not result:
        return  # Mecz nie istnieje

    result1, result2 = result
    res = result1 - result2

    # Pobierz wszystkie zakłady dla meczu
    bets = db.execute(
        'SELECT result1, result2, user_id FROM bets WHERE match_id = ?',
        (id,)
    ).fetchall()

    user_ids = set(bet[2] for bet in bets)  # Użyj setu do uniknięcia duplikatów ID użytkowników

    # Pobierz punkty i liczbę poprawnych wyników dla wszystkich użytkowników
    user_points = db.execute(
        'SELECT id, points, correct_scores FROM user WHERE id IN ({})'.format(
            ','.join('?' * len(user_ids))
        ),
        tuple(user_ids)
    ).fetchall()

    # Mapuj ID użytkowników do punktów i poprawnych wyników
    points_map = {user['id']: {'points': user['points'], 'correct_scores': user['correct_scores']} for user in
                  user_points}

    for bet in bets:
        bet_result1, bet_result2, user_id = bet
        bet_res = bet_result1 - bet_result2

        if user_id in points_map:
            user_points_data = points_map[user_id]
            points = user_points_data['points']
            correct_scores = user_points_data['correct_scores']

            if bet_result1 == result1 and bet_result2 == result2:
                points += 3
                correct_scores += 1
            elif res > 0 and bet_res > 0:
                points += 1
            elif res == bet_res:
                points += 1
            elif res < 0 and bet_res < 0:
                points += 1

            db.execute(
                'UPDATE user SET points = ?, correct_scores = ? WHERE id = ?',
                (points, correct_scores, user_id)
            )

    db.commit()
