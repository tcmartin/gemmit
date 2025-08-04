#!/usr/bin/env bash
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)       echo linux      ;;
  Darwin-arm64)       echo mac-arm64 ;;
  Darwin-*)           echo mac-x64   ;;
  MINGW*|MSYS*|CYGWIN*) echo win      ;;
  *) echo unsupported && exit 1 ;;
esac

