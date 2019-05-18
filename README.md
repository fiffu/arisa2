## arisa2

arisa2 is a rewrite of [Arisa][1], a Discord bot created using [`discord.py`][2] in early 2018. Since then, various workarounds have been added to the original codebase to support features that were never considered in the initial design.

This rewrite effort is mainly motivated by the major [changes][3] that come with upgrading to discord.py v1.x, which made large parts of the original code obsolete. At the same time, this is a good occasion for the bot's source code to be made public.

[1]:https://arisa-chan.herokuapp.com
[2]:https://discordpy.readthedocs.io/
[3]:https://discordpy.readthedocs.io/en/latest/migrating.html

## Setup and usage

**Basic Configuration**

Firstly, you should fill in the configuration needed for the bot to run. 

Go to the `/config` directory and make a copy of the `config.conf.DEFAULT`. Fill in the blank fields.

*Steps for acquiring a `BOT_TOKEN` (as required in the `[DISCORD]` section):*

1. Create a new application at the [Discord developer portal][4].
2. Inside the **settings** for the new app, select the **Bot** section and click
**Add bot**. This will convert the app to a "bot user" so that can join servers.
3. Click the button to **copy** the bot token, then paste into the config file.

**Runtime Environment**

Install pipenv ([step-by-step guide][4]).

    pip install --user --upgrade pipenv

Clone this repo, then `cd` into the created directory.

    git clone https://github.com/fiffu/arisa2.git
    cd arisa2

Initialize a new pipenv shell, then install dependencies.

    pipenv shell
    pipenv install

## Usage

You have to activate the pipenv shell before you start the app:

    pipenv shell
    python3 main.py

[4]:https://docs.pipenv.org/en/latest/install/
