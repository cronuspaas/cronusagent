#!/bin/bash

usage() { 
    echo "Install agent from locally built agent and python packages" 1>&2
    echo "Usage: "
    echo "  $0 agent_version pypkg_version install_root [server_pem] [agent_pwd]" 1>&2
    echo "  $0 agent_version pypkg_version install_root" 1>&2
    exit 1 
}

# OS checking function
checkos() {

    OS=$(awk '/DISTRIB_ID=/' /etc/*-release | sed 's/DISTRIB_ID=//' | tr '[:upper:]' '[:lower:]')

    ARCH=$(uname -m | sed 's/x86_//;s/i[3-6]86/32/')

    case $(uname -m) in
    x86_64)
        ARCH=x64  # or AMD64 or Intel64 or whatever
        ;;
    i*86)
        ARCH=x86  # or IA32 or Intel32 or whatever
        ;;
    *)
        # leave ARCH as-is
        ;;
    esac

    if [ -z "$OS" ] && [ hash zypper 2>/dev/null ]; then
        OS=$(awk '/^ID=/' /etc/os-release | sed 's/ID=//' | tr '[:upper:]' '[:lower:]')
    fi

    if [ -z "$OS" ] && [ hash apt 2>/dev/null ]; then
        OS=$(lsb_release -i | awk '{print $3}' | tr '[:upper:]' '[:lower:]')
    fi

    if [ -z "$OS" ]; then
        OS="generic"
    fi

    OPENSSL=$(openssl version | tr '[:upper:]' '[:lower:]' | awk '{print $1,$2}' | sed 's/ //;s/[.]//;s/[.].*//')

    PYTHON="py27"
    if command -v python2.7 2>&1>/dev/null; then
        PYTHON="py27"
    elif command -v python2.6 2>&1>/dev/null; then
        PYTHON="py26"
    else
        echo "Need python2.7 or 2.6 runtime"
        exit -1
    fi

    echo "${ARCH}_${OS}_${PYTHON}_${OPENSSL}"

}

EXPECTED_ARGS=3

#check the number of args
if [[ $# -lt $EXPECTED_ARGS ]]; then
  usage
elif [[ $# -eq $EXPECTED_ARGS ]]; then
  read -p "install with default cert (publicly accessible) and no password [y|N]?" ans
  if [[ $ans != "y" ]]; then
    usage
  fi
fi

abspath=$(cd ${0%/*} && echo $PWD/${0##*/})
script_dir=`dirname "$abspath"`
echo "script_dir $script_dir"

cd $script_dir
echo copy agent package to current dir
[ -f "$script_dir/../../target/dist/agent-$1.unix.cronus" ] || {
  echo "agent package $script_dir/../../target/dist/agent-$1.unix.cronus not exist, build agent first"
  exit -1
}
cp $script_dir/../../target/dist/agent-$1.unix.cronus .

echo copy and rename python package to current dir
os_type=$( checkos )
[ -f "$script_dir/../../../python-package/target/dist/python_package-$2.unix.cronus" ] || {
  echo "pypkg $script_dir/../../../python-package/target/dist/python_package-$2.unix.cronus not exist, build pypkg first"
  exit -1
}
cp $script_dir/../../../python-package/target/dist/python_package-$2.unix.cronus ./python_package-$2.$os_type.cronus

echo now install agent
if [[ $# -eq $EXPECTED_ARGS ]]; then
  cat install_agent | sudo pkg_ver=$1 pypkg_ver="$2.$os_type" target_dir=$3 dev=true bash
else
  cat install_agent | sudo pkg_ver=$1 pypkg_ver="$2.$os_type" target_dir=$3 server_pem=$4 agent_pwd=$5 bash
fi
#./install.sh -v $1 -d $3 -p $2

echo "removing temp files"
rm -f agent-$1.unix.cronus python_package-$2.$os_type.cronus
echo "done"
