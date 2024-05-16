#!/bin/bash

host=$(grep 'local_host' config.toml | cut -d'=' -f2 | tr -d ' "') || echo -e "wat"

echo -e "$host"
