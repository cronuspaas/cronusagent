#!/bin/bash

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
fi
echo "${ARCH}_${OS}_${PYTHON}_${OPENSSL}"
#echo "python_package-1.0.0.${ARCH}_${OS}_${OPENSSL}.cronus"
