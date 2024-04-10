#!/bin/sh

# Configure here
VERSION_FILE=./immersionlyceens/__init__.py
# End of configuration

VERSION=$(git describe --abbrev=0 --tags || echo "0.0.0")

VNUM1=$(echo "$VERSION" | cut -d"." -f1)
VNUM2=$(echo "$VERSION" | cut -d"." -f2)
VNUM3=$(echo "$VERSION" | cut -d"." -f3)
VNUM1=$(echo $VNUM1 | sed 's/v//')

# Check for #major or #minor in commit message and increment the relevant version number
MAJOR=$(git log --format=%B -n 1 HEAD | grep '#major')
MINOR=$(git log --format=%B -n 1 HEAD | grep '#minor')

if [ "$MAJOR" ]; then
    echo "Update major version X.0.0"
    VNUM1=$((VNUM1 + 1))
    VNUM2=0
    VNUM3=0
elif [ "$MINOR" ]; then
    echo "Update minor version 0.X.0"
    VNUM2=$((VNUM2 + 1))
    VNUM3=0
else
    echo "Update patch version O.0.X"
    VNUM3=$((VNUM3 + 1))
fi

#create new tag
NEW_TAG="v$VNUM1.$VNUM2.$VNUM3"

echo "Updating $VERSION to $NEW_TAG"

#get current hash and see if it already has a tag
GIT_COMMIT=$(git rev-parse HEAD)
NEEDS_TAG=$(git describe --contains $GIT_COMMIT 2>/dev/null)

if [ -z "$NEEDS_TAG" ]; then
    echo "Tagged with $NEW_TAG (Ignoring fatal:cannot describe - this means commit is untagged) "
    sed -i "s/\([0-9]\+, [0-9]\+, [0-9]\+\)/$VNUM1, $VNUM2, $VNUM3/g" $VERSION_FILE
    git tag $NEW_TAG
    git push --tags
else
    echo "Already a tag on this commit"
fi
