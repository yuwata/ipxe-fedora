#!/bin/bash

BRANCH=master

CMD=${0##*/}
SOURCE_DIR=$(cd $(dirname $0) && pwd)
REPO_NAME=${SOURCE_DIR##*/}
REPO_DIR=${HOME}/git/${REPO_NAME}

HASH_OLD=$(grep -e '^[%#]global gitcommit' ${SOURCE_DIR}/${REPO_NAME}.spec | awk '{ print $3 }')
if [[ -z $HASH_OLD ]]; then
    echo 'error: cannot obtain commit hash.' >&2
    exit 1
fi
HASH_OLD_SHORT=${HASH_OLD:0:7}

if ! git -C $REPO_DIR fetch upstream master; then
    echo "error: `git fetch upstream master` failed." >&2
    exit 11
fi

if ! HASH_NEW=$(git -C $REPO_DIR show-ref --hash refs/remotes/upstream/master); then
    echo "error: `git show-ref` failed." >&2
    exit 12
fi
HASH_NEW_SHORT=${HASH_NEW:0:7}

if [[ "$HASH_NEW" != "$HASH_OLD" ]]; then

    HASH_DATE=$(git -C $REPO_DIR log -1 --format='%cd' --date=short | tr -d -)

    WEEKDAY=$(date "+%a")
    MONTH=$(date "+%b")
    DAY=$(date "+%d")
    YEAR=$(date "+%Y")

    sed -e '/^%global gitcommit/ { s/^#/%/; s/'${HASH_OLD}'/'${HASH_NEW}'/ }' \
        -e '/^%global date/ { s/[0-9]*$/'${HASH_DATE}'/ }' \
        -e "/^%changelog/ a\
* ${WEEKDAY} ${MONTH} ${DAY} ${YEAR} Yu Watanabe <watanabe.yu@gmail.com> - ${HASH_DATE}-1.git${HASH_NEW_SHORT}\\
- Update to latest git snapshot ${HASH_NEW}\\
" \
        -i ${SOURCE_DIR}/${REPO_NAME}.spec

    git -C $SOURCE_DIR commit -a -m 'Update to latest git snapshot'
fi
