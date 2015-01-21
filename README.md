
## Cronus Agent - a RESTful agent automation framework
==========
###Install
**Install from stable build**
    
Prerequisites:
* linux (Ubuntu, Cent, Redhat, Fedora etc.)
* sudo permission
* python2.7 or 2.6
* openssl 0.9.8 or above
* wget
* system management daemon systemd or upstart

```bash
# Install agent in /var/cronus with default ssl cert and no password
 wget -qO- 'http://cronuspaas.github.io/downloads/install_agent' | sudo dev=true bash
# custom ssl cert and user:password for basic auth
 wget -qO- 'http://cronuspaas.github.io/downloads/install_agent' \
 | sudo server_pem=path_to_ssl_cert agent_pwd=user:password bash
```

Verify successful installation

```sh
# Check agent validate internal page
 curl -k https://localhost:19000/agent/ValidateInternals
```


###Package application for cronus deployment
Prepare your application for cronus deployment

**Bootstrap cronus package structures**

If your application stack is not already supported in git repo cronuspackage, bootstrap it with command
```bash
 wget -qO- 'http://cronuspaas.github.io/downloads/bootstrap_cronus' | DIR=. bash
```

**Cronus packaging**

Change <myapp_root_dir>/package.sh to fill in right value for appname, version
```bash
./package.sh .
```
Result cronus package files with .cronus and .cronus.prop extension in cronus_target folder


###Build from source
**Build from source if prebuild package does not work for you**

**build python package**
```bash
 cd ~/proj/python-package
 ant package -Ddeploylocal=true
 ant -Dbuildnum=1 ... (build version 0.1.1)
```
python package is in /target/dist as a cronus package

**build agent package**
```bash
cd ~/proj/agent
ant package
ant -Dbuildnum=1 -Dnotest=true package (build version 0.1.1)
#agent and agent config package are in /target/dist as cronus packages
```

**install from local build**
```bash
# first build agent and pypkg as above
cd agent/scripts/install
./install_localbuild.sh 0.1.1 0.1.1 /var path_to_ssl_cert user:password
```

###Development

**Users and permissions**
```bash
cd agent/scripts/build
sudo ./add_users.sh
sudo echo '_your_local_user  ALL = (ALL) NOPASSWD: ALL' >>/etc/sudoers
```

**On Ubuntu**
```bash
sudo apt-get install ant git

#for pyopenssl dependency
sudo apt-get install gcc build-essential libssl-dev libffi-dev python-dev

#ubuntu with python2.7 need the following fix
sudo ln -s /usr/lib/python2.7/plat-*/_sysconfigdata_nd.py /usr/lib/python2.7/
```

**On Redhat**
```bash
sudo yum install ant git

#for pyopenssl dependency
sudo yum install gcc libffi-devel python-devel openssl-devel
```
