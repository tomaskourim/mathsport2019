# Math Sport 2019 Conference paper

This repository contains all source code necessary to perform operations described in a paper submitted to a Math Sport 2019 international scientific conference.

The paper itself, **Random Walks with Memory Applied in Grand Slam Tennis Matches Modeling**, is located in the folder /paper.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)

## Deploy on Ubuntu
### Deploy database server

    sudo apt update
    sudo apt install postgresql postgresql-contrib

Create new user bettor (can be anything, has to be set up in database.ini)

    sudo -u postgres createuser --interactive

(Follow instructions)

Create DB (same name as user)

    sudo -u postgres createdb bettor

Create new system user bettor (or whatever username you chose)
    
    sudo adduser bettor

(Follow instructions, remember password)

Change password for the new Postgres user
    
    sudo -u bettor psql
    \password bettor
    \quit

(Follow instructions, pass is the same as system user)

Clone repo and go to folder

    git clone https://github.com/tomaskourim/mathsport2019.git --depth 1
    cd mathsport2019

Load SQL schema from folder live_betting/db_migrations

    cd live_betting/db_migrations
    psql -U bettor -h localhost -f V1_schema.sql bettor
    ...    

### Deploy betting server

Clone repo and go to folder

    git clone https://github.com/tomaskourim/mathsport2019.git
    cd mathsport2019
    
#### Necessary packages
Install pip and other necessary prerequisites

    sudo apt update
    sudo apt install python3-pip python-psycopg2 libpq-dev
    
Install required packages

    python3 -m pip install -r requirements.txt

#### Install chrome & selenium
Install prerequisites (including Java)

    sudo apt update
    sudo apt install -y unzip xvfb libxi6 libgconf-2-4 default-jdk 
    
Install Chrome (for some reason, you have to do it as root, not only sudo)

    sudo curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add
    sudo echo "deb [arch=amd64]  http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
    sudo apt -y update
    sudo apt -y install google-chrome-stable

Install ChromeDriver (go to https://sites.google.com/a/chromium.org/chromedriver/downloads to get the proper version)

    wget https://chromedriver.storage.googleapis.com/89.0.4389.23/chromedriver_linux64.zip
    unzip chromedriver_linux64.zip
    sudo mv chromedriver /usr/bin/chromedriver
    sudo chown root:root /usr/bin/chromedriver
    sudo chmod +x /usr/bin/chromedriver

#### Set up project files
Fill the files 
`config_betting.py`, `database.ini` and `credentials.json`. Use examples and your information. 

Add to Pyton path

    export PYTHONPATH=/path/to/folder
  
Preferably add to .bashrc so that it loads automatically.
    
Run form `tmux` or similar
   
    cd live_betting
    python3 betting.py
