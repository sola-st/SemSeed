# Install

Install **Node.js** and the required packages:

````shell
# You may install Node.js using nvm : https://github.com/nvm-sh/nvm
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
source ~/.bashrc

# Install Node.js 14
nvm install 14.17.0
# Install the required Node.js packages
npm install
````

Create a virtual environment for **Python** and install the required packages:

````shell
sudo apt install -y python3-dev # required for the 'fasttext' package
sudo apt install -y python3-venv

# Create a virtual environment
python3 -m venv semseed_venv
# Activate the virtual environment
source semseed_venv/bin/activate
# Install the required Python packages
pip install -r requirements.txt
````

We provide pre-trained token embeddings trained using fastText (https://fasttext.cc). The training has been performed
using JavaScript files obtained from https://www.sri.inf.ethz.ch/js150.

Install **MongoDB**

````shell
# Install MongoDB Community Edition on Ubuntu 20.04
# Documentation -> https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu

wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list
sudo apt-get update
sudo apt-get install -y mongodb-org

# Once installation has finished start MongoDB
sudo systemctl start mongod
````
