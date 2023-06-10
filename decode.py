#!/usr/bin/python
import argparse
import sys
import warnings
from datetime import datetime
import os
import sqlite3

import fitdecode
import folium
import xlsxwriter
from geopy.geocoders import Nominatim
import pyfiglet


# Author: Fabian Nunes
# Script to decode a FIT file to a set coordinates and show the route in a HTML map or convert them to a KML file
# Requires the fitdecode module (Install with pip install fitdecode) and folium (also PIP)
# Example: python decode.py file.txt -t html|kml

def suppress_fitdecode_warnings(message, category, filename, lineno, file=None, line=None):
    if category == UserWarning and 'fitdecode' in message.args[0]:
        return
    else:
        return message, category, filename, lineno, file, line


# Set the filter function as the default warning filter
warnings.showwarning = suppress_fitdecode_warnings


class Bcolors:
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


parser = argparse.ArgumentParser(description='Decode a FIT file to a set of coordinates and generate a map')
parser.add_argument('-f', '--file', help='File with the encoded polyline', required=True)
parser.add_argument('-t', '--type', help='Type of output', required=True, choices=["html", "kml"])
parser.add_argument('-e', '--excel', help='Generate an Excel file with the coordinates', action='store_true')

args = parser.parse_args()

FILE = args.file
TYPE = args.type
EXCEL = args.excel

conn = sqlite3.connect('coordinates.db')
c = conn.cursor()


def get_raw_fields(latitude, longitude):
    geolocator = Nominatim(user_agent="address-retrieval")
    location = geolocator.reverse(f"{latitude}, {longitude}")
    if location:
        raw_data = location.raw
        # check if raw_data["address"]["road"] exists
        not_present = False
        if "road" in raw_data["address"]:
            road = raw_data["address"]["road"]
        elif "hamlet" in raw_data["address"]:
            road = raw_data["address"]["hamlet"]
        else:
            road = 'Not Present'
            not_present = True

        if "city" in raw_data["address"]:
            city = raw_data["address"]["city"]
        elif "town" in raw_data["address"]:
            city = raw_data["address"]["town"]
        else:
            city = 'Not present'
            not_present = True

        if not not_present:
            store_raw_fields(latitude, longitude, road, city,
                             raw_data["address"]["postcode"], raw_data["address"]["country"])
        # create a dict
        obtained_data = {"road": road, "city": city, "postcode": raw_data["address"]["postcode"],
                         "country": raw_data["address"]["country"]}
        return obtained_data
    else:
        print("Location not found.")


# Function to store the raw fields in a sqlite database if not already present, and create the database if not present
def store_raw_fields(latitude_value, longitude_value, road_value, city_value, postcode_value, country_value):
    print(Bcolors.OKBLUE + "[Info ] Storing raw fields in database" + Bcolors.ENDC)
    # Check if the entry is already present
    c.execute('''SELECT * FROM raw_fields WHERE latitude=? AND longitude=?''', (latitude_value, longitude_value))
    if c.fetchone() is None:
        # Insert a row of data
        c.execute('''INSERT INTO raw_fields (latitude, longitude, road, city, postcode, country) 
                      VALUES (?, ?, ?, ?, ?, ?)''',
                  (latitude_value, longitude_value, road_value, city_value, postcode_value, country_value))

        # Save (commit) the changes
        conn.commit()


# Function to check if the raw fields are already present in the database and return them if present or return None
def check_raw_fields(latitude, longitude):
    # Check if the entry is already present
    print(Bcolors.OKBLUE + "[Info ] Checking if raw fields are already present in database" + Bcolors.ENDC)
    c.execute('''SELECT * FROM raw_fields WHERE latitude=? AND longitude=?''', (latitude, longitude))
    data = c.fetchone()
    # convert to dict
    return data


if __name__ == '__main__':
    ascii_banner = pyfiglet.figlet_format("FIT2GPS")
    if os.path.isfile(FILE):
        print(Bcolors.OKBLUE + "[Info ] Reading file: " + FILE)
    else:
        print(Bcolors.FAIL + "File not found" + Bcolors.ENDC)
        sys.exit(1)

    # check if the file is a FIT file
    if not FILE.endswith('.fit'):
        print(Bcolors.FAIL + "File is not a FIT file" + Bcolors.ENDC)
        sys.exit(1)

    if EXCEL:
        print(Bcolors.OKBLUE + "[Info ] Geopy Features activated" + Bcolors.ENDC)
        # Create table if not present
        print(Bcolors.OKBLUE + "[Info ] Creating database if needed" + Bcolors.ENDC)
        c.execute(
            '''CREATE TABLE IF NOT EXISTS raw_fields (id INTEGER PRIMARY KEY AUTOINCREMENT, stored_time TIMESTAMP DATETIME DEFAULT CURRENT_TIMESTAMP, latitude text, longitude text, road text, city text, postcode text, country text)''')
    else:
        print(Bcolors.OKBLUE + "[Info ] Geopy Features not activated" + Bcolors.ENDC)

    print(Bcolors.OKBLUE + "[Info ] Decoding the FIT file")
    coordinates = []
    if EXCEL:
        coordinatesE = []
    with fitdecode.FitReader(FILE) as fit:
        print(Bcolors.OKBLUE + "[Info ] FIT file valied!")
        for frame in fit:
            if frame.frame_type == fitdecode.FIT_FRAME_DATAMESG:
                if frame.name == 'record':
                    # Check if the record message contains the position_lat
                    # and position_long fields.
                    if frame.has_field('position_lat') and frame.has_field('position_long'):
                        lat = frame.get_value('position_lat')
                        lon = frame.get_value('position_long')
                        if EXCEL:
                            timestamp = frame.get_value('timestamp')
                            timestamp = timestamp.timestamp()
                            # convert from UNIX timestamp to UTC
                            timestamp = datetime.utcfromtimestamp(timestamp)
                            timestamp = str(timestamp)
                            # convert from semicircles to degrees
                        lat = lat * (180.0 / 2 ** 31)
                        lon = lon * (180.0 / 2 ** 31)
                        # round to 5 decimal places
                        lat = round(lat, 5)
                        lon = round(lon, 5)
                        coordinates.append([lat, lon])
                        if EXCEL:
                            coordinatesE.append([lat, lon, timestamp])
                elif frame.name == 'session':
                    if frame.has_field('total_elapsed_time'):
                        total_elapsed_time = frame.get_value('total_elapsed_time')
                        # convert to minutes
                        total_elapsed_time_m = total_elapsed_time / 60
                        total_elapsed_time_m = int(total_elapsed_time_m)
                    if frame.has_field('start_time'):
                        start_time = frame.get_value('start_time')
                        # convert from FIT timestamp to UNIX timestamp
                        start_time_u = start_time.timestamp()
                        # add seconds to the UNIX timestamp
                        end_time = start_time_u + total_elapsed_time
                        # convert from UNIX timestamp to UTC
                        start_time = datetime.utcfromtimestamp(start_time_u)
                        end_time = datetime.utcfromtimestamp(end_time)
                    if frame.has_field('sport'):
                        sport = frame.get_value('sport')
                    if frame.has_field('total_distance'):
                        total_distance = frame.get_value('total_distance')
                        # convert from m to km
                        total_distance = total_distance / 1000
                        total_distance = round(total_distance, 2)

    # save general inforamtion to a file
    print(Bcolors.OKBLUE + "[Info ] Saving general information to file")
    f = open("general_information.txt", "w")
    f.write("Start time: " + str(start_time) + "\n")
    f.write("End time: " + str(end_time) + "\n")
    f.write("Total distance: " + str(total_distance) + " km\n")
    f.write("Total elapsed time: " + str(total_elapsed_time_m) + " minutes\n")
    f.write("Sport: " + str(sport) + "\n")
    f.close()

    # save the coordinates to excel file
    if EXCEL:
        print(Bcolors.OKBLUE + "[Info ] Creating excel file with coordinates" + Bcolors.ENDC)
        f = open('coordinates.xlsx', 'w')
        workbook = xlsxwriter.Workbook('coordinates.xlsx')
        worksheet = workbook.add_worksheet()
        col = 0
        rowE = 0
        worksheet.write(rowE, col, "Timestamp")
        worksheet.write(rowE, col + 1, "Latitude")
        worksheet.write(rowE, col + 2, "Longitude")
        worksheet.write(rowE, col + 3, "Road")
        worksheet.write(rowE, col + 4, "City")
        worksheet.write(rowE, col + 5, "Postcode")
        worksheet.write(rowE, col + 6, "Country")
        rowE += 1

        for coordinate in coordinatesE:
            # coordinate = str(coordinate)
            # round to 5 decimal cases
            lat = round(coordinate[0], 3)
            lon = round(coordinate[1], 3)
            worksheet.write(rowE, col, coordinate[2])
            worksheet.write(rowE, col + 1, lat)
            worksheet.write(rowE, col + 2, lon)
            location = check_raw_fields(lat, lon)
            if location is None:
                print(Bcolors.OKBLUE + "[Info ] Location not found in database, querying Nominatim" + Bcolors.ENDC)
                location = get_raw_fields(lat, lon)
                for key, value in location.items():
                    if key == "road":
                        worksheet.write(rowE, col + 3, value)
                    elif key == "city":
                        worksheet.write(rowE, col + 4, value)
                    elif key == "postcode":
                        worksheet.write(rowE, col + 5, value)
                    elif key == "country":
                        worksheet.write(rowE, col + 6, value)
            else:
                print(Bcolors.OKBLUE + "[Info ] Location found in database" + Bcolors.ENDC)
                worksheet.write(rowE, col + 3, location[4])
                worksheet.write(rowE, col + 4, location[5])
                worksheet.write(rowE, col + 5, location[6])
                worksheet.write(rowE, col + 6, location[7])
            rowE += 1
        workbook.close()

    if TYPE == "html":
        # Generate HTML file with the map and the route using Folium
        place_lat = []
        place_lon = []
        print(Bcolors.OKBLUE + "[Info ] Generating HTML file with the map and the route")
        m = folium.Map(location=[coordinates[0][0], coordinates[0][1]], zoom_start=10, max_zoom=19)

        for coordinate in coordinates:
            # if points are to close, skip
            if len(place_lat) > 0 and abs(place_lat[-1] - coordinate[0]) < 0.0001 and abs(
                    place_lon[-1] - coordinate[1]) < 0.0001:
                continue
            else:
                place_lat.append(coordinate[0])
                place_lon.append(coordinate[1])

        points = []
        for i in range(len(place_lat)):
            points.append([place_lat[i], place_lon[i]])

        # Add points to map
        for index, lat in enumerate(place_lat):
            # Start point
            if index == 0:
                folium.Marker([lat, place_lon[index]],
                              popup=('Start Location\n'.format(index)),
                              icon=folium.Icon(color='blue', icon='flag', prefix='fa')).add_to(m)
            # last point
            elif index == len(place_lat) - 1:
                folium.Marker([lat, place_lon[index]],
                              popup=(('End Location\n').format(index)),
                              icon=folium.Icon(color='red', icon='flag', prefix='fa')).add_to(m)
            # middle points

        # Create polyline
        folium.PolyLine(points, color="red", weight=2.5, opacity=1).add_to(m)
        # Save the map to an HTML file
        title = 'Garmin_Polyline_Map'
        m.save(title + '.html')
        print(Bcolors.OKGREEN + "[Done ] Generated HTML file with the coordinates" + Bcolors.ENDC)
    elif TYPE == "kml":
        # Generate KML file with the coordinates
        print(Bcolors.OKBLUE + "[Info ] Generating KML file with the coordinates")
        kml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://www.opengis.net/kml/2.2">
        <Document>
        <name>Coordinates</name>
        <description>Coordinates</description>
        <Style id="yellowLineGreenPoly">
            <LineStyle>
                <color>7f00ffff</color>
                <width>4</width>
            </LineStyle>
            <PolyStyle>
                <color>7f00ff00</color>
            </PolyStyle>
        </Style>
        <Placemark>
            <name>Absolute Extruded</name>
            <description>Transparent green wall with yellow outlines</description>
            <styleUrl>#yellowLineGreenPoly</styleUrl>
            <LineString>
                <extrude>1</extrude>
                <tessellate>1</tessellate>
                <altitudeMode>clampedToGround</altitudeMode>
                <coordinates>
                """
        for coordinate in coordinates:
            kml += str(coordinate[1]) + "," + str(coordinate[0]) + ",0 \n"
        kml = kml[:-1]
        kml += """
                </coordinates>
            </LineString>
        </Placemark>
        </Document>
        </kml>
        """
        # remove the first space
        kml = kml[1:]
        # remove last line
        kml = kml[:-1]
        # remove extra indentation
        kml = kml.replace("    ", "")
        f = open("map.kml", "w")
        f.write(kml)
        f.close()
        print(Bcolors.OKGREEN + "[Done ] Generated KML file with the coordinates" + Bcolors.ENDC)
