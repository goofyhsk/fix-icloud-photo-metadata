# Original script - https://github.com/dayowe/fix-icloud-photo-metadata
Some facets didn't quite suit my preference and system (ran on windows in powershell)

## Changes to dayowe version
 - Remove need for Photos directory (personal preference)
 - Change Cloud directory name (English, remove spaces)
 - Media files timestamps set to `originalCreationDate` - forced GMT, Day/Month/Year (old script only seemed to ignore Month and Day (again, ran on windows)) 


## My Directory Structure
```
fix_photo_metadata.py
iCloudPhotosPartXofY/
│   ├── Photo Details.csv
│   ├── Photo Details-1.csv
│   ├── Photo Details-2.csv
│   ├── IMG_001.HEIC
│   ├── IMG_002.JPG
│   └── ...
```
