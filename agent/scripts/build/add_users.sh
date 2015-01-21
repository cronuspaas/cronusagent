#!/bin/bash

# check root permissions
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit -1
fi

echo "Create user cronus and cronusapp"
egrep -i "^app\W" /etc/group > /dev/null 2>&1 || groupadd -r app
id -u cronus > /dev/null 2>&1 || useradd -r cronus -g app
id -u cronusapp > /dev/null 2>&1 || useradd -r cronusapp -g app
echo "Add sudo permission for user cronus"
sed -i '/cronus/d' /etc/sudoers
echo "Add ALL NOPASSWD: ALL with cronus /etc/sudoers, disable requiretty"
echo 'cronus  ALL = (ALL) NOPASSWD: ALL' >>/etc/sudoers
sed -ri 's/^([^#].*requiretty).*/#\1/g' /etc/sudoers
echo "Done"
