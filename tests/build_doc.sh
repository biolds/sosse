#!/usr/bin/bash
cd "$(dirname "$0")/.."
rm -rf doc/build
./sosse-admin extract_doc cli > doc/source/cli_generated.rst
./sosse-admin extract_doc conf > doc/source/config_file_generated.rst
./sosse-admin extract_doc se > doc/source/user/shortcut_list_generated.rst
make -C doc html 
