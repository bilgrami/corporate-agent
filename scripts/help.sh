#!/bin/sh
# Parse Makefile for ## comments and display as help

MAKEFILE="${1:-Makefile}"
echo "Available targets:"
echo ""
grep -E '^[a-zA-Z_-]+:.*##' "$MAKEFILE" | awk -F ':.*## ' '{printf "  %-15s %s\n", $1, $2}'
