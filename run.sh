#!/usr/bin/env bash

ROOT="/home/twilight/dev/nazareth"
ENV_DIR="lenv"

if [ -d "$ROOT/$ENV_DIR" ]; then
	    source "$ROOT/$ENV_DIR/bin/activate"
fi

pushd "$ROOT/src" > /dev/null || exit 1
python "$ROOT/src/nazareth.py"
popd > /dev/null
