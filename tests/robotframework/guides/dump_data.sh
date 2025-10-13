#!/bin/bash

# Check if an argument is passed
if [ -z "$1" ]; then
  echo "Usage: $0 <dump_directory>"
  exit 1
fi

# Check the dir does not exist
if [ -d "$1" ]; then
  echo "Error: Directory '$1' already exists. Please provide a new directory."
  exit 1
fi

# Variables
DUMP_DIR="$1"
VAR_LIB_DIR="/var/lib/sosse"
DUMP_DOC="${DUMP_DIR}/dump_doc.json"
DUMP_MODEL="${DUMP_DIR}/dump_model.json"
DUMP_FILE="${DUMP_DIR}/dump.json"

# Create the directory for data if necessary
mkdir -p "${DUMP_DIR}"

# Generate the Django data dump
echo "Generating Django data dump..."
sosse-admin dumpdata_sosse --indent 2 \
  se.collection \
  se.favicon \
  se.link \
  se.tag \
  se.document \
  se.webhook >"${DUMP_MODEL}"
#se.htmlasset \

#sosse-admin shell -c "$(cat dump_documents.py)" >"$DUMP_DOC"
#cat "$DUMP_MODEL" "$DUMP_DOC" | jq -s 'reduce .[] as $x ([]; . + $x)' >"$DUMP_FILE"

# Copy the screenshots and html files
#echo "Copying screenshots and html files..."
mkdir -p "${DUMP_DIR}/html" "${DUMP_DIR}/screenshots"
#cp -r "${VAR_LIB_DIR}/html" "${DUMP_DIR}/html"
cp -r "${VAR_LIB_DIR}/screenshots" "${DUMP_DIR}/screenshots"
#
echo "Data dump and file copy completed."
