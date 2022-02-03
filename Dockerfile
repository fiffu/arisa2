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

# Chrome
ENV CHROME_SETUP=./google-chrome.deb
RUN wget -O ${CHROME_SETUP} "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"

# Chrome deps
RUN apt-get update \
    && apt-get -y install \
        gconf-service libappindicator1 libasound2 \
        libatk1.0-0 libatk-bridge2.0-0 libcairo-gobject2 \
        libdrm2 libgbm1 libgconf-2-4 libgtk-3-0 libnspr4 libnss3 \
        libx11-xcb1 libxcb-dri3-0 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 \
        libxi6 libxinerama1 libxrandr2 libxss1 libxtst6 \
        fonts-liberation \
    && apt-get install -y -f ${CHROME_SETUP} \
    && rm -rf /var/lib/apt/lists/* \
    && rm ${CHROME_SETUP}

RUN mkdir /arisa2
WORKDIR /arisa2
ADD ./Pipfile /arisa2
ADD ./Pipfile.lock /arisa2

# Install pip stuff
# --deploy forces build failure if Pipfile and Pipfile.lock are out of sync
# --system installs to the system, rather than to a venv
# --ignore-pipfile makes pipenv reference Pipfile.lock instead of Pipfile
RUN pip install pipenv \
    && pipenv install --deploy --system --ignore-pipfile

ADD . /arisa2

CMD ["python3", "main.py"]
