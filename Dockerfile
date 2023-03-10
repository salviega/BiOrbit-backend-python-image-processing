FROM ubuntu:18.04
 
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
 
# Install tools
RUN apt-get update \
        && apt-get --yes install \
        wget \
        && apt-get install -y curl \
        && apt-get install -y unzip \
        && apt-get install -y gnupg2 \
        && rm -rf /var/lib/apt/lists/*
 
# Install miniconda
RUN wget --progress=dot:mega https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh \
        && chmod +x miniconda.sh && ./miniconda.sh -b -p /usr/local/conda3 \
        && rm -f miniconda.sh
 
# Set environment PATH
ENV PATH /usr/local/conda3/bin:$PATH
 
# Update configure files
RUN echo 'export PATH=/usr/local/conda3/bin:$PATH' >> /etc/profile.d/pynn.sh \
        && ln -sf /usr/local/conda3/etc/profile.d/conda.sh /etc/profile.d/


# Install Chrome WebDriver
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
    mkdir -p /opt/chromedriver-$CHROMEDRIVER_VERSION && \
    curl -sS -o /tmp/chromedriver_linux64.zip http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip -qq /tmp/chromedriver_linux64.zip -d /opt/chromedriver-$CHROMEDRIVER_VERSION && \
    rm /tmp/chromedriver_linux64.zip && \
    chmod +x /opt/chromedriver-$CHROMEDRIVER_VERSION/chromedriver && \
    ln -fs /opt/chromedriver-$CHROMEDRIVER_VERSION/chromedriver /usr/local/bin/chromedriver

# Install Google Chrome
RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get -yqq update && \
    apt-get -yqq install google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*
 

RUN conda config --add channels conda-forge

WORKDIR /src

ADD downloading-images /src
ADD processing-images /src



