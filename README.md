# Decode_FIT

Repository for script to decode Strava FIT files to coordinates and store them in a file and generate a map with the coordinates

## Requirements
 - Python 3
 - Python libraries: fitdecode, folium, argparse

## What is FIT

"FIT" is a commonly used acronym in the context of fitness apps and trackers, where it stands for "Flexible and Interoperable Data Transfer".

The FIT format in the context of fitness apps is a binary file format used to store health and fitness data such as workout information, heart rate data, and GPS data. It was developed by Garmin and is used by a variety of fitness trackers and apps, including Garmin devices, Strava, and many others.

The FIT format is designed to be flexible and interoperable, which means that it can be easily used and shared across different devices and platforms. It is also designed to be efficient and lightweight, so that it can be quickly processed and transmitted even on low-power devices like smartwatches.

Overall, the FIT format has become a popular standard for fitness data interchange, and is widely used by fitness enthusiasts, athletes, and trainers to track and analyze their performance and progress over time.

## Parameters
    - f, --file: FIT file
    - t, --type: Type of output file. Options: html, kml
## Usage

```bash
python3 decode.py -f <file> -t <type>
```

## Important
This script was done to decode the FIT files from the fitness application Strava, we cannot say for certain how it will handle other applications.

## Output

The script will create a file called coordinates.txt with the coordinates, a general.txt file with additional data found related to the activity and a map called map.html or a Google Earth file called map.kml.

## License

This code is under the GNU General Public License v3.0. See the LICENSE file for more information.
