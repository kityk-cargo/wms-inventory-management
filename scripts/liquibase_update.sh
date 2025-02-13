#!/bin/bash
# Usage: liquibase_update.sh <JDBC_URL> <USERNAME> <PASSWORD> <CHANGELOG_FILE>
JDBC_URL="$1"
USERNAME="$2"
PASSWORD="$3"
CHANGELOG_FILE="$4"

liquibase \
  --url="$JDBC_URL" \
  --username="$USERNAME" \
  --password="$PASSWORD" \
  --changeLogFile="$CHANGELOG_FILE" \
  update
