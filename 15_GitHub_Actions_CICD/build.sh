#!/bin/bash
set -e
echo "================================="
echo "Starting Application Build"
echo "================================="
rm -rf build
mkdir -p build
cp -r app build/
rm -rf build/app/__pycache__
cat > build/build-info.txt <<INFO
Application: Session 16 Calculator
Build Status: SUCCESS
Commit: ${GITHUB_SHA:-local}
Built by: ${GITHUB_ACTOR:-$(whoami)} on ${RUNNER_OS:-$(uname -s)}
Build Date: $(date -u)
INFO
echo ""
echo "Build files:"
find build -type f | sort
echo ""
echo "Build completed successfully."
