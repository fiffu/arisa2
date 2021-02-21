FROM python:3.6

ENV CHROMEDRIVER_VERSION `curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`
ENV GOOGLE_CHROME_BIN /usr/bin/chromedriver

RUN echo ${CHROMEDRIVER_VERSION} ${GOOGLE_CHROME_BIN}

# Install chromedriver and google-chrome
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` \
    && GOOGLE_CHROME_DIR=/usr/bin/ \
    && wget https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip -d ${GOOGLE_CHROME_DIR} \
    && chmod +x ${GOOGLE_CHROME_BIN} \
    && rm chromedriver_linux64.zip

RUN CHROME_SETUP=google-chrome.deb \
    && wget -O $CHROME_SETUP "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" \
    && dpkg -i $CHROME_SETUP \
    & apt-get install -y -f \
    && rm $CHROME_SETUP


ADD . /arisa2
WORKDIR /arisa2

# Install pip stuff
# --deploy forces build failure if Pipfile and Pipfile.lock are out of sync
# --system installs to the system, rather than to a venv
# --ignore-pipfile makes pipenv reference Pipfile.lock instead of Pipfile
RUN pip install pipenv \
    && pipenv install --deploy --system --ignore-pipfile

RUN ["python3", "main.py"]
