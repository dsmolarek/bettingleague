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
        ' SELECT username, points, correct_scores'
        ' FROM user'
        ' WHERE points >= 0'
        ' ORDER BY points DESC, correct_scores DESC'
    ).fetchall()
    return render_template('page/index.html', users=users)


@bp.route('/add_bet')
def add_bet():
    db = get_db()
    current_date = datetime.now()
    current_date2 = datetime.now()
    current_date = current_date.strftime("%Y-%m-%d")
    current_hour = int(current_date2.strftime("%H"))
    matches = db.execute(
        ' SELECT id, country1, country2, date2, date3, datetime'
        ' FROM matches'
        ' WHERE date2 = ?'
        ' ORDER BY date3', (current_date,)
    ).fetchall()

    your_bets = db.execute(
        ' SELECT bets.user_id, bets.match_id, bets.result1, bets.result2'
        ' FROM bets'
        ' INNER JOIN matches ON bets.match_id = matches.id'
        ' WHERE user_id = ? AND match_id in ( SELECT id FROM matches WHERE date2 = ? )'
        ' ORDER BY date3', (g.user['id'], current_date)
    ).fetchall()

    user_bets = db.execute(
        ' SELECT bets.user_id, bets.match_id, bets.result1, bets.result2, user.username, user.id'
        ' FROM bets'
        ' INNER JOIN user ON bets.user_id = user.id'
        ' WHERE match_id in ( SELECT id FROM matches WHERE date2 = ? ) AND user_id = ?'
        ' ORDER BY match_id', (current_date, g.user['id'])
        ).fetchall()    

    return render_template('page/add_bet.html', user_bets=user_bets, your_bets=your_bets, matches=matches,
                           current_date=current_date, current_hour=current_hour)


@bp.route('/bets')
def bets():
    db = get_db()
    current_date = datetime.now()
    current_date2 = datetime.now()
    current_date = current_date.strftime("%Y-%m-%d")
    current_hour2 = int(current_date2.strftime("%H"))
#    current_hour2 = current_hour2-2
    spis_id = []
    matches = db.execute(
        ' SELECT id, country1, country2, date2, date3, datetime'
        ' FROM matches'
        ' WHERE date2 = ?'
        ' ORDER BY date3', (current_date,)
    ).fetchall()

    user_list = db.execute(
        ' SELECT id, username'
        ' FROM user'
        ' WHERE points >= 0'
        ' ORDER BY points DESC, correct_scores DESC'
    ).fetchall()
    lista_id = []
    for i in range(0, len(user_list)):
        lista_id.append(int(user_list[i][0]))
    
    id_to_username = {}
    for i in range(0, len(user_list)):
        id_to_username.update({user_list[i][0]: user_list[i][1]})

    for match in matches:
        spis_id.append(match[0])
    typy = db.execute(
        ' SELECT bets.user_id, bets.match_id, bets.result1, bets.result2, user.username, user.id'
        ' FROM bets'
        ' INNER JOIN user ON bets.user_id = user.id'
        ' WHERE match_id in ( SELECT id FROM matches WHERE date2 = ? )'
        ' ORDER BY match_id', (current_date,)
        ).fetchall()
    pre_braki = lista_id
    pre2_braki = []
    braki = []
    
    for l in range(0, len(spis_id)):
        pre_braki = lista_id
        for i in range(0, len(lista_id)):
            for l in range(0, len(spis_id)):
                for typ in typy:
                    if spis_id[l] == typ[1]:
                        if typ[0] in lista_id:
                            pre_braki.remove(typ[0])
    pre2_braki.append(pre_braki)
        
            
    for i in range(0, len(pre2_braki)):
        for l in range(0, len(pre2_braki[i])):
            braki.append(id_to_username[pre2_braki[i][l]])

    preBetCount = db.execute(
        ' SELECT bets.user_id, bets.match_id, bets.result1, bets.result2, user.username, user.id'
        ' FROM bets'
        ' INNER JOIN user ON bets.user_id = user.id'
        ' WHERE match_id in ( SELECT id FROM matches WHERE date2 = ? )'
        ' ORDER BY match_id', (current_date,)
        ).fetchall()

    twoje_typy2 = {}
#    liczba_typow = int(0)
#    for idx in spis_id:
#        bets_count = db.execute(
#            ' SELECT bets.user_id, bets.match_id, bets.result1, bets.result2, user.username, user.id'
#            ' FROM bets'
#            ' INNER JOIN user ON bets.user_id = user.id'
#            ' WHERE match_id = ?)'
#            ' ORDER BY match_id', (idx,)
#        ).fetchall()
    for i in range(0, len(spis_id)):
        liczba_typow = 0
        for typ in typy:
            if spis_id[i] == typ[1]:
                liczba_typow = liczba_typow+1
        twoje_typy2.update({spis_id[i]:liczba_typow})
    
                
#    twoje_typy2=len(
    
    
     

    
    return render_template('page/bets.html', id_to_username=id_to_username, pre_braki=pre_braki, braki=braki, lista_id=lista_id, current_hour2=current_hour2, typy=typy, twoje_typy2=twoje_typy2, spis_id=spis_id, matches=matches, current_date=current_date)



@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if g.user['username'] == 'admin':

        if request.method == 'POST':
            country1 = request.form['country1']
            country2 = request.form['country2']
            date = request.form['date']
            
            error = None

            if not country1 and not country2 and not date:
                error = 'Wpisanie krajów i daty jest wymagane.'

            if error is not None:
                flash(error)
            else:
                db = get_db()
                db.execute(
                    'INSERT INTO matches (country1, country2, date)'
                    ' VALUES (?, ?, ?)',
                    (country1, country2, date)
                )
                db.commit()
                return redirect(url_for('page.index'))

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
@login_required

def longterm():

    db = get_db()
#    current_hour = int(current_date2.strftime("%H"))
#    current_hour = current_hour+1
    longterm_bets = db.execute(
        ' SELECT user_id, top_scorer, winner'
        ' FROM long_term'
        ' ORDER BY winner'
    ).fetchall()
    if request.method == 'POST':
        top_scorer  = (request.form['top_scorer'])
        winner = (request.form['winner'])
        error = None

        if not top_scorer and not winner:
            error = 'Musisz wpisać swoje typy!'

        db = get_db()
        

        if error is not None:
            flash(error)
        
        db = get_db()

#        db.row_factory = sqlite3.Row
#        cur = db.cursor()
#        cur.execute('SELECT * FROM long_term')
#        check = cur.fetchall()

        db.execute(
            'INSERT INTO long_term (user_id, top_scorer, winner)'
            'VALUES (?, ?, ?)', (g.user['id'], top_scorer, winner)
        )
        db.commit()


#        else:
#           db.execute(
#                'UPDATE long_term SET top_scorer = ?, winner = ?'
#                'WHERE user_id = ?', (top_scorer, winner, g.user['id'])
#            )
#            db.commit()

        return redirect(url_for('page.longterm'))

    return render_template('page/longterm.html', longterm_bets=longterm_bets)

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    match = get_post(id)

    if request.method == 'POST':
        country1 = request.form['country1']
        country2 = request.form['country2']
        result1 = request.form['result1']
        result2 = request.form['result2']
        error = None

        if not country1 and not country2:
            error = 'Countries are required.'

        db = get_db()
        bet = db.execute(
            ' SELECT result1, result2'
            ' FROM matches'
            ' WHERE id = ?',
            (id,)
        ).fetchone()
        print("LALALALA", bet[0])

        if bet[0] != None and bet[1] != None:
            error = 'Match is over'

        if error is not None:
            flash(error)
        elif result2 is not None and result1 is not None:
            db = get_db()
            db.execute(
                'UPDATE matches SET result1 = ?, result2 = ?'
                ' WHERE id = ?',
                (result1, result2, id)
            )
            db.commit()

            points_update(id)

            return redirect(url_for('page.index'))
        else:
            db = get_db()
            db.execute(
                'UPDATE matches SET country1 = ?, country2 = ?'
                ' WHERE id = ?',
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
    current_date2 = datetime.now()
    current_date = current_date.strftime("%Y-%m-%d")
    current_hour = int(current_date2.strftime("%H"))
    db = get_db()
    hour = db.execute(
            ' SELECT result1, result2, date3'
            ' FROM matches'
            ' WHERE id = ?',
            (id,)
        ).fetchone()

    if request.method == 'POST':
        result1 = int(request.form['result1'])
        result2 = int(request.form['result2'])
        error = None

#        if not result1 and not result2:
#            error = 'Musisz wpisać swoje typy!'

        if type(result1) != int or type(result2) != int:
            error = 'Musisz wpisać liczby.'

#        db = get_db()
        bet = db.execute(
            ' SELECT result1, result2, date3'
            ' FROM matches'
            ' WHERE id = ?',
            (id,)
        ).fetchone()

        if bet[0] != None and bet[1] != None:
            error = 'Mecz jest skończony'

        if error is not None:
            flash(error)
        else:
            db = get_db()

            db.row_factory = sqlite3.Row
            cur = db.cursor()
            cur.execute('SELECT * FROM bets')
            check = cur.fetchall()

            match_ids = []
            for x in check:
                if x[0] == g.user['id']:
                    match_ids.append(x[1])
            
            if match['id'] not in match_ids:
                db.execute(
                    'INSERT INTO bets (user_id, match_id, result1, result2)'
                    ' VALUES (?, ?, ?, ?)', (g.user['id'], match['id'], result1, result2)
                )
                db.commit()
            else:
                db.execute(
                    'UPDATE bets SET result1 = ?, result2 = ?'
                    ' WHERE user_id = ? AND match_id = ?', (result1, result2, g.user['id'], match['id'])
                )
                db.commit()

            return redirect(url_for('page.bets'))

    return render_template('page/bet.html', hour=hour, match=match, current_hour=current_hour)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM matches WHERE id = ?', (id,))
    db.execute('DELETE FROM bets WHERE match_id = ?', (id,))
    db.commit()
    return redirect(url_for('page.index'))




