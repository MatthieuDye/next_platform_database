#!/bin/bash
echo Recovering previous changes
git pull
echo Adding new changes to the commit
git add *
echo please, write the commit title
read title
echo Establishing the commit
git commit -m $title
echo Pushing the commit
git push
