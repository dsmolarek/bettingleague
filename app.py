import os, sys
from flask import Flask
#sys.path.append(os.getcwd())


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='euro2021typowanie',
        DATABASE=os.path.join(app.instance_path, 'BettingLeague.sqlite'),
    )

    from public.db import init_app
    init_app(app)

    import public.auth as auth
    app.register_blueprint(auth.bp)

    import public.page as page
    app.register_blueprint(page.bp)
    app.add_url_rule('/', endpoint='index')

    return app

app = create_app()
