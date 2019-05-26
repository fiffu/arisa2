## arisa2

arisa2 is a rewrite of [Arisa][1.1], a Discord bot created using [`discord.py`][1.2] in early 2018. Since then, various workarounds have been added to the original codebase to support features that were never considered in the initial design.

This rewrite effort is mainly motivated by the major [changes][1.3] that come with upgrading to discord.py v1.x, which made large parts of the original code obsolete. At the same time, this is a good occasion for the bot's source code to be made public.

[1.1]:https://arisa-chan.herokuapp.com
[1.2]:https://discordpy.readthedocs.io/
[1.3]:https://discordpy.readthedocs.io/en/latest/migrating.html


## Setup

**Clone the repo**

    git clone https://github.com/fiffu/arisa2.git
    cd arisa2

**Basic configuration**

The bot's main configuration file is found in the `appconfig` folder. Individual cogs generally have their own `config.py` file within their own directories.

To ensure the bot runs correctly (or at all), ensure that you configure it properly.

1. Go to the `/appconfig` directory and make a copy of the `config.conf.DEFAULT`.
2. Rename the copy to `config.conf`. Only make edits to this copy (they will override the default settings).
3. All the blank fields should be filled in, unless otherwise indicated.
4. Detailed instructions are in `appconfig/README`.

**Runtime environment**

Set up Python. Check that you have Python 3.6 or later, and install pipenv ([step-by-step guide][3.1]).

    python --version
    pip install --user --upgrade pipenv

Initialize a new pipenv shell, then install dependencies.

    pipenv shell
    pipenv install

[3.1]:https://docs.pipenv.org/en/latest/install/


## Usage

You have to activate the pipenv shell before you start the app:

    pipenv shell
    python3 main.py

