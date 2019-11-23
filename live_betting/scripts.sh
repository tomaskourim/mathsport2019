#!/usr/bin/env bash
rm -r  screens/server/
scp -r do-tk:~/mathsport2019/live_betting/screens/ screens/server/
scp do-tk:~/mathsport2019/live_betting/*.log screens/server/
