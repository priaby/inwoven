#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd "$(dirname "$0")" && pwd -P)"
cp -R "$case_dir/../../tests/eval/fixture/acme-notes/." .
git init -b main
git add .
git -c user.name=Acme -c user.email=acme@example.invalid commit -m fixture
