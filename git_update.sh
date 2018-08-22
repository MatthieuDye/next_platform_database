#!/bin/bash
echo Recovering previous changes
git pull
echo Adding new changes to the commit
git add *
echo Write the commit title. Use _ instead of any space.
read title
echo Establishing the commit
git commit -m $title
echo Pushing the commit
git push
