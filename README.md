## arisa2

Arisa is a [Discord](https://discordapp.com/) bot built on Python with [discord.py](https://pypi.org/project/discord.py/).

arisa2 is a major rewrite of the original [Arisa](https://arisa-chan.herokuapp.com) bot, after major breaking changes came in as discord.py graduated to v1.0.


## Design

Arisa is designed to run for free on [Heroku](https://heroku.com/), with the PostgreSQL addon. We use [aiopg](https://pypi.org/project/aiopg/) database bindings, essentially an async wrapper over [psycopg2](https://pypi.org/project/psycopg2/).

Arisa's business logic is implemented with modular [cogs](https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html), which are loaded selectively at startup. As the use-case is for a guild playing multiple flavour-of-the-month games, cogs allow us to write features targeting a specific game, which can be left unloaded later on.

We have some cog mixins that implement 'middleware' services, for example DatabaseCog providing idiomatic database access. These should be inherited along with `discord.ext.commands.Cog` when such services are required. Some mixins provide interfaces with web-scraping engines, forming the backbone for the website update tracker. We use [aiohttp](https://pypi.org/project/aiohttp/) for static pages and [Selenium](https://pypi.org/project/selenium/) for dynamic/JS-rendered sites. See the separate readme for setting up the browser drivers and bindings for Selenium.

All required schemas are maintained in the `database` module. Arisa expects to connect to an initialized database, so feed the schema to your database before spinning up.

App-level configuration, such as secrets and tokens, are defined and exported by the `appconfig` module. The configs are declared with ini-style files, which can be overwritten by environment variables. Cog-specific settings are maintained in their own modules.


## Setup

**Clone the repo**

    git clone https://github.com/fiffu/arisa2.git
    cd arisa2


**Basic configuration**

Arisa's main configuration file is found in the `appconfig` folder. To ensure things run correctly (or at all), ensure that you configure stuff properly.

1. Go to the `/appconfig` directory and make a copy of the `config.conf.DEFAULT`.
2. Rename the copy to `config.conf`. Only make edits to this copy (they will override the default settings).
3. All the blank fields should be filled in, unless otherwise indicated.
4. Detailed instructions are in README for the `appconfig` module.

**Runtime environment**

Set up Python. Check that you have Python 3.6 or later, and install [pipenv](https://pypi.org/project/pipenv/) ([step-by-step guide](https://docs.pipenv.org/en/latest/install/)).

    python --version
    pip install --user --upgrade pipenv

Initialize a new pipenv shell, then install dependencies.

    pipenv shell
    pipenv install


## Deploying

You have to activate the pipenv shell first if you are deploying locally:

    pipenv shell
    python3 main.py

Otherwise, after setting up a Heroku app and linking the app's git deployment endpoint, push:

    heroku git:remote -a myApp
    git push heroku master

If you are using Heroku, consider setting up a separate [staging app](https://devcenter.heroku.com/articles/multiple-environments), then adding it as an alternate remote in your main repo. To deploy non-master branches to staging, you can use:

    git push staging myBranch:master
