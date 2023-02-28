from tts_tools.libtts import get_fs_path
from tts_tools.libtts import IllegalSavegameException
from tts_tools.libtts import urls_from_save
from tts_tools.util import print_err
from tts_tools.util import ZipFile

import os
import re
import sys
import json
import hashlib

def hash_file(filename):
   # make a hash object
   h = hashlib.sha256()

   # open file for reading in binary mode
   with open(filename,'rb') as file:

       # loop till the end of the file
       chunk = 0
       while chunk != b'':
           # read only 1024 bytes at a time
           chunk = file.read(1024)
           h.update(chunk)

   # return the hex representation of digest
   return h.hexdigest()

def readTTSBackupDB(dbFilePath):
    if os.path.exists(dbFilePath):
        with open(dbFilePath, 'r') as f:
            data = json.load(f)
            return data
    else:
        data = {}
        return data

def backup_json(args):
    if args.singlefile:
        original_backup_json(args)
        return

    ttsbackupFile = "F:\\Tabletop Simulator\\db-ttsbackup.json"
    ttsbackupJson = readTTSBackupDB(ttsbackupFile)

    directory = "F:\\Tabletop Simulator\\Mods\\Workshop"
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                filePath = os.path.join(root, file)

                fileKey = file.replace(".json", "")
                curFileJson = {}
                if fileKey in ttsbackupJson:
                    curFileJson = ttsbackupJson[fileKey]

                oldFileHash = "";                   
                if "backuphash" in curFileJson:
                    oldFileHash = curFileJson["backuphash"]
                    
                curFileDate = os.path.getmtime(filePath)

                oldFileDate = 0;                   
                if "backupFileDate" in curFileJson:
                    oldFileDate = curFileJson["backupFileDate"]

                if oldFileDate == curFileDate:
                    print("No file change. Skipping " + file)
                    continue

                curHash = hash_file(filePath)
                if oldFileHash == curHash:
                    print("No change. Skipping " + file)

                    curFileJson["backupFileDate"] = curFileDate
                    ttsbackupJson[fileKey] = curFileJson
                    with open(ttsbackupFile, 'w') as f:
                        json.dump(ttsbackupJson, f)
                    continue

                success = backup_json_helper(filePath, args.gamedata_dir)

                if success:
                    curFileJson["backupFileDate"] = curFileDate
                    curFileJson["backuphash"] = curHash
                    ttsbackupJson[fileKey] = curFileJson
                
                    with open(ttsbackupFile, 'w') as f:
                        json.dump(ttsbackupJson, f)


def original_backup_json(args):
    backup_json_helper(args.infile_name, args.gamedata_dir)    

def backup_json_helper(infile_name, gamedata_dir):
    try:
        urls = urls_from_save(infile_name)
    except (FileNotFoundError, IllegalSavegameException) as error:
        errmsg = "Could not read URLs from '{file}': {error}".format(
            file=infile_name, error=error
        )
        print_err(errmsg)
        return False

    # Change working dir, since get_fs_path gives us a relative path.
    orig_path = os.getcwd()
    try:
        os.chdir(gamedata_dir)
    except FileNotFoundError as error:
        errmsg = "Could not open gamedata directory '{dir}': {error}".format(
            dir=gamedata_dir, error=error
        )
        print_err(errmsg)
        return False

    # We also need to correct the the destination path now.
    outfile_basename = re.sub(
        r"\.json$", "", os.path.basename(infile_name)
    )
    outfile_name = os.path.join("F:\\Tabletop Simulator\\Backups", outfile_basename) + ".zip"

    try:
        zipfile = ZipFile(
            outfile_name,
            "w",
            dry_run=False,
            ignore_missing=False,
        )
    except FileNotFoundError as error:
        errmsg = "Could not write to Zip archive '{outfile}': {error}".format(
            outfile=outfile_name, error=error
        )
        print_err(errmsg)
        return False

    with zipfile as outfile:

        for path, url in urls:

            filename = get_fs_path(path, url)
            try:
                outfile.write(filename)

            except FileNotFoundError as error:
                errmsg = "Could not write {filename} to Zip ({error}).".format(
                    filename=filename, error=error
                )
                print_err(errmsg, "Aborting.", sep="\n", end=" ")
                print_err("Zip file is incomplete.")
                return False

        # Finally, include the save file itself.
        orig_json = os.path.join(orig_path, infile_name)
        outfile.write(orig_json, os.path.basename(infile_name))

        # Store some metadata.
        outfile.put_metadata(comment="")

    print(
        "Backed-up contents for {file} found in {outfile}.".format(
            file=infile_name, outfile=outfile_name
        )
    )
    return True
