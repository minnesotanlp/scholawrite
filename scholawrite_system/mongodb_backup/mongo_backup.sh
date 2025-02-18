# To run, make sure set your GFOLDER_ID and CONTAINER_NAME in ~/.bashrc or crontab or this file

FORMAT="$(date +'%m-%d-%Y')-Dump"
ORIGIN=/media/$FORMAT/
DEST=./
ZIPNAME=$FORMAT.zip

check_removal() {
    if [ $? -eq 0 ]; then
        echo "$1 was removed successfully."
    else
        echo "Failed to remove $1."
    fi
}

cd "$(dirname "$0")"

docker exec -t $CONTAINER_NAME mongodump --out=$ORIGIN
docker cp $CONTAINER_NAME:$ORIGIN $DEST
docker exec -t $CONTAINER_NAME rm -rf $ORIGIN

check_removal "$ORIGIN in $CONTAINER_NAME"

zip -r $ZIPNAME $FORMAT

rm -rf $FORMAT

check_removal "$FORMAT folder"

source backup_venv/bin/activate

python3 upload_zip.py $GFOLDER_ID $ZIPNAME application/zip

deactivate

rm $ZIPNAME

check_removal $ZIPNAME