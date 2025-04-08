#!/bin/bash

branch=$(git rev-parse --abbrev-ref HEAD)

if [ "$branch" = "main" ]; then
      echo "Running flake8 on main branch..."
        exec flake8 "$@"
    else
          echo "Skipping flake8 (not on main branch: $branch)"
            exit 0
fi

