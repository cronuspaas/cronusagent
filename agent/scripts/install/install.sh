#!/bin/bash

usage() { echo "Usage: $0 [-v <agent_version>] [-h] target_dir" 1>&2; exit 1; }

EXPECTED_ARGS=1

#check the number of args
if [[ $# -ne $EXPECTED_ARGS ]]
then
  usage
fi

while getopts ":v:h:" o; do
    case "${o}" in
        v)
            agent_ver=${OPTARG}
            ;;
        h)
            usage
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

abspath=$(cd ${0%/*} && echo $PWD/${0##*/})
script_dir=`dirname "$abspath"`
echo "script_dir $script_dir"
cd $script_dir

cmd="cat install_agent | sudo target_dir=$1"
if [ ! -z "${agent_ver}" ]; then
   cmd="$cmd pkg_ver=$agent_ver"
fi
cmd="$cmd bash"

echo "agent_ver=$agent_ver, target_dir=$target_dir"
echo "install cmd $cmd"

eval "$cmd"
#cat install_agent | sudo pkg_ver=$agent_ver pypkg_ver="$py_ver.$os_type" target_dir=$target_dir bash
