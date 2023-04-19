#!/bin/bash
set -e

f="$(cat "$1")"
cmd=""
IFS=$'\n'; for line in $f
do
    if test -n "$cmd"
    then
        cmd="$cmd"$'\n'"$line"
        if grep -q '\\$' <<< "$line"
        then
            continue
        fi
    elif grep -q ^RUN <<< "$line"
    then
        cmd="$(echo $line | sed -e 's/^RUN //')"
        if grep -q '\\$' <<< "$line"
        then
            continue
        fi
    else
        continue
    fi

    echo "---- $cmd"
    eval "$cmd"
    cmd=""
done
