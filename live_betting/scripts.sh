#!/usr/bin/env bash
rm -r  screens/server/
scp -r bettor:~/mathsport2019/live_betting/screens/ screens/server/
scp bettor:~/mathsport2019/live_betting/*.log screens/server/
