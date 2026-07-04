#!/usr/bin/env bash

set -o errexit
set -o xtrace

moin cache-destroy
moin index-destroy
moin index-create
moin cache-create
moin index-build
moin cache-populate
