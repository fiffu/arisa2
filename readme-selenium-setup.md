# Deploying Selenium bindings for Python on Heroku

### Requirements:
- Chrome (or your browser of choice) executable
- Chrome (or your browser of choice) driver
- Selenium bindings for Python

### Installation for Heroku

    $ heroku buildpacks:add heroku/google-chrome -a myapp
    $ heroku buildpacks:add heroku/chromedriver -a myapp

Change `myapp` to your app's name. Repeat this on the [staging](https://devcenter.heroku.com/articles/multiple-environments#creating-a-staging-environment) app, if you have one configured.

### Installation for dev environment
  * Download and install the driver for whatever browser you've got installed (e.g. [ChromeDriver](https://sites.google.com/a/chromium.org/chromedriver/downloads))
  * Ensure the installed binary is in your PATH
  >Alternatively, in your environment variables, define `GOOGLE_CHROME_BIN` (or whatever variable the Heroku buildpack exports from the previous step).

  >If you get an error about permissions, check that you have included the filename and the`.exe` at the end.

### Install Selenium bindings
    $ pipenv shell
    $ pipenv install selenium

### Usage

```py
import os
from selenium import webdriver

# Heroku's buildpacks will provision env vars for the binary
# Example: https://github.com/heroku/heroku-buildpack-google-chrome
driverpath = os.environ.get('GOOGLE_CHROME_BIN')

driver = webdriver.Chrome(executable_path=driverpath)
driver.get('https://httpbin.org/')
```
