## arisa2

arisa2 is a rewrite of [Arisa][1.1], a Discord bot created using [`discord.py`][1.2] in early 2018. Since then, various workarounds have been added to the original codebase to support features that were never considered in the initial design.

This rewrite effort is mainly motivated by the major [changes][1.3] that come with upgrading to discord.py v1.x, which made large parts of the original code obsolete. At the same time, this is a good occasion for the bot's source code to be made public.

[1.1]:https://arisa-chan.herokuapp.com
[1.2]:https://discordpy.readthedocs.io/
[1.3]:https://discordpy.readthedocs.io/en/latest/migrating.html

## Setup

**Basic Configuration**

Firstly, you should fill in the configuration needed for the bot to run. 

1. Go to the `/appconfig` directory and make a copy of the `config.conf.DEFAULT`. 
2. Rename the copy to `config.conf`. Only make edits to this copy (they will override the default settings).
3. Make sure none of the fields are left blank.

*To acquire a bot token from Discord:*

1. Go to the [Discord developer portal][2.1] and **create a new application**.
2. Inside the **settings** for the new app, select the **Bot** section and click
**Add bot**. This will convert the app to a "bot user" so that can join servers.
3. Click the button to **copy** the bot token, then paste into the config file.

*To acquire a personal access token from GitHub:*

1. Go to your [GitHub settings][2.2].
2. Click **Developer settings**, then select **Personal access tokens**.
3. Click **Generate new token**. You will probably have to enter your password to continue.
4. Write a useful note to help remind yourself of the purpose for the new token (for example, "arisa").
5. Click **Generate token** at the bottom. Don't select any of the scopes, we don't need those.
3. Click the button to **copy** the newly-generated token, then paste into the config file.


[2.1]:https://discordapp.com/developers
[2.2]:https://github.com/settings/


**Runtime Environment**

Install pipenv ([step-by-step guide][3.1]).

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

[3.1]:https://docs.pipenv.org/en/latest/install/
