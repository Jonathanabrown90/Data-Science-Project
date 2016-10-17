from flask import Flask, render_template, request, url_for, Markup
import simplejson, urllib, json
import pandas as pd
import csv
import time
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.tools as tls
from pandas import compat
from datetime import datetime
from pytimeparse.timeparse import timeparse
from array import array
import operator
import gpxpy
import gpxpy.gpx
import folium
import branca.element
import jinja2
from jinja2 import Environment, PackageLoader

########################################################################################################
##LOAD TEMPLATE FOR VISUALISATION

env = Environment(loader=PackageLoader('folium', 'templates'))

########################################################################################################
##DECODING SCRIPT FOR GOOGLE POLYLINE

def decode_line(encoded):

    encoded_len = len(encoded)
    index = 0
    array = []
    lat = 0
    lng = 0

    while index < encoded_len:

        b = 0
        shift = 0
        result = 0

        while True:
            b = ord(encoded[index]) - 63
            index = index + 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break

        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat

        shift = 0
        result = 0

        while True:
            b = ord(encoded[index]) - 63
            index = index + 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break

        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng

        array.append((lat * 1e-5, lng * 1e-5))

    return array

########################################################################################################
##FLASK LIBRARY CREATING LOCAL SERVER PAGES

app = Flask(__name__)

@app.route('/')
def form():
	return render_template('form_submit.html')

@app.route('/map/')
def map(): 
	return render_template('map2.html')

@app.route('/result/')
def result():
	return render_template('index.html')

@app.route('/hello/', methods=['POST'])
def hello():

########################################################################################################
##START AND END LOCATION

	Starting_Location=request.form['start_location']
	Ending_Location=request.form['destination']

########################################################################################################
##GOOGLE DIRECTIONS API DATA EXTRACTION

	##current travel time
	current_url = 'https://maps.googleapis.com/maps/api/directions/json?origin={0},+UK&destination={1},+UK&departure_time=now&mode=transit&traffic_model=best_guess&units=imperial&key=AIzaSyCQuNCI4HZoiujfymwcOoABg7H8HzhxvgE'.format(Starting_Location,Ending_Location)
	current_url_json = simplejson.load(urllib.urlopen(current_url))
	current_url_duration = timeparse(current_url_json['routes'][0]['legs'][0]['duration']['text'])/60
	current_url_polyline = current_url_json['routes'][0]['legs'][0]['steps'][0]['polyline']['points']

	##starting location to Bham station
	url_to_Bham = 'https://maps.googleapis.com/maps/api/directions/json?origin={0},+UK&destination=Curzon+Street+Station+UK&departure_time=now&mode=transit&traffic_model=best_guess&units=imperial&key=AIzaSyCQuNCI4HZoiujfymwcOoABg7H8HzhxvgE'.format(Starting_Location)
	url_to_Bham_json = simplejson.load(urllib.urlopen(url_to_Bham))
	url_to_Bham_duration = timeparse(url_to_Bham_json['routes'][0]['legs'][0]['duration']['text'])/60
	url_to_Bham_polyline = url_to_Bham_json['routes'][0]['legs'][0]['steps'][0]['polyline']['points']

	##starting location to Euston station
	url_to_Euston = 'https://maps.googleapis.com/maps/api/directions/json?origin={0},+UK&destination=London+Euston+UK&departure_time=now&mode=transit&traffic_model=best_guess&units=imperial&key=AIzaSyCQuNCI4HZoiujfymwcOoABg7H8HzhxvgE'.format(Starting_Location)
	url_to_Euston_json = simplejson.load(urllib.urlopen(url_to_Euston))
	url_to_Euston_duration = timeparse(url_to_Euston_json['routes'][0]['legs'][0]['duration']['text'])/60
	url_to_Euston_polyline = url_to_Euston_json['routes'][0]['legs'][0]['steps'][0]['polyline']['points']

########################################################################################################
##IF STATEMENTS TO CALCULATE LEGS OF JOURNEY

	##LEG ONE duration
	if url_to_Bham_duration < url_to_Euston_duration:
		LEG_ONE_duration = url_to_Bham_duration
	else:
		LEG_ONE_duration = url_to_Euston_duration

	##LEG ONE polyline
	if url_to_Bham_duration < url_to_Euston_duration:
		LEG_ONE_polyline = url_to_Bham_polyline
	else:
		LEG_ONE_polyline = url_to_Euston_polyline

	##LEG ONE json
	if url_to_Bham_duration < url_to_Euston_duration:
		LEG_ONE_json = url_to_Bham_json
	else:
		LEG_ONE_json = url_to_Euston_json
	#print (simplejson.dumps(LEG_ONE_json, sort_keys=True, indent=4 * ' '))

	##LEG THREE polyline 
	if LEG_ONE_polyline == url_to_Bham_polyline:
		LEG_THREE_polyline = url_to_Euston_polyline
	else:
		LEG_THREE_polyline = url_to_Bham_polyline

	##start location for leg three (to be inputted into URL)
	if url_to_Bham_duration < url_to_Euston_duration:
		start_of_leg_three = 'London+Euston'
	else:
		start_of_leg_three = 'Curzon+Street+Station'

########################################################################################################
##LEG THREE AND CALCULATIONS

	##LEG THREE
	url_LEG_THREE = 'https://maps.googleapis.com/maps/api/directions/json?origin={0},+UK&destination={1},+UK&departure_time=now&mode=transit&traffic_model=best_guess&units=imperial&key=AIzaSyCQuNCI4HZoiujfymwcOoABg7H8HzhxvgE'.format(start_of_leg_three,Ending_Location)
	url_LEG_THREE_json = simplejson.load(urllib.urlopen(url_LEG_THREE))
	url_LEG_THREE_duration = timeparse(url_LEG_THREE_json['routes'][0]['legs'][0]['duration']['text'])/60
	LEG_THREE_polyline = url_LEG_THREE_json['routes'][0]['legs'][0]['steps'][0]['polyline']['points']
	#print (simplejson.dumps(url_LEG_THREE_json, sort_keys=True, indent=4 * ' '))

	##Total duration with HS2. '103' minutes worked out by adding 49 min travel time and ~7 min transfer time each way
	Total_duration_with_HS2 = LEG_ONE_duration + url_LEG_THREE_duration + 59
	print current_url_duration
	print Total_duration_with_HS2
	##Time difference between duration with and without HS2 route
	Time_saved = current_url_duration - Total_duration_with_HS2
	print Time_saved


########################################################################################################
##SIDEBAR TEXT WHEN RESULTS ARE SHOWN ON WEBAPP
	
	result = "<h4>You are traveling from <strong>{0}</strong> to <strong>{1}</strong></h4>". format(Starting_Location, Ending_Location)
	result += "<ul><li>Travel time without HS2: {0} minutes </li><li>Travel time with HS2: {1} minutes</li></ul>". format(current_url_duration, Total_duration_with_HS2)
	if Time_saved < 0: 
		result += '<h4>Using HS2 would take <span style="color: red"> {0} </span> minutes longer.</h4>'.format(Time_saved)
	else: 
		result += '<h4>Using HS2 would save you <span style="color: green"> {0} </span> minutes!</h4>'.format(Time_saved)
		


########################################################################################################
##DECODE AND APPEND ALL LEGS OF POLYLINE TOGETHER

	c = []
	for i in range (0,len (current_url_json['routes'][0]['legs'][0]['steps'])):
	    b = current_url_json['routes'][0]['legs'][0]['steps'][i]['polyline']['points']
	    c = c+decode_line(b)
	
	g = []
	for i in range (0,len (LEG_ONE_json['routes'][0]['legs'][0]['steps'])):
	    f = LEG_ONE_json['routes'][0]['legs'][0]['steps'][i]['polyline']['points']
	    g = g+decode_line(f)

	k = []
	for i in range (0,len (url_LEG_THREE_json['routes'][0]['legs'][0]['steps'])):
	    j = url_LEG_THREE_json['routes'][0]['legs'][0]['steps'][i]['polyline']['points']
	    k = k+decode_line(j)

########################################################################################################
##SPLIT OUT LAT LONGS AND APPEND TO DATA FRAME

	current_route_list_lat = []
	current_route_list_long = []

	leg_one_list_lat = []
	leg_one_list_long = []

	leg_three_list_lat = []
	leg_three_list_long = []

	##Whole polyline without HS2
	#if __name__ == "__main__":
	current_latlngs = c
	for latlng in current_latlngs:
	    latitude = str(latlng[0])
	    current_route_list_lat.append(latitude)

	#if __name__ == "__main__":
	current_latlngs = c
	for latlng in current_latlngs:
	    longitude = str(latlng[1])
	    current_route_list_long.append(longitude)

	#Leg 1 polyline from starting location to nearest HS2 station
	#if __name__ == "__main__":
	leg_one_latlngs = g
	for latlng in leg_one_latlngs:
	    latitude = str(latlng[0])
	    leg_one_list_lat.append(latitude)

	#if __name__ == "__main__":
	leg_one_latlngs = g
	for latlng in leg_one_latlngs:
	    longitude = str(latlng[1])
	    leg_one_list_long.append(longitude)

	#Leg 3 polyline from furthest HS2 station to end location
	#if __name__ == "__main__":
	leg_three_latlngs = k
	for latlng in leg_three_latlngs:
	    latitude = str(latlng[0])
	    leg_three_list_lat.append(latitude)

	#if __name__ == "__main__":
	leg_three_latlngs = k
	for latlng in leg_three_latlngs:
	    longitude = str(latlng[1])
	    leg_three_list_long.append(longitude)


	data_frame_current = pd.DataFrame({'latitude': [current_route_list_lat][0], 'longitude': [current_route_list_long][0]})
	data_frame_current[['latitude','longitude']] = data_frame_current[['latitude','longitude']].apply(pd.to_numeric)
	data_frame_leg_one = pd.DataFrame({'latitude': [leg_one_list_lat][0], 'longitude': [leg_one_list_long][0]})
	data_frame_leg_one[['latitude','longitude']] = data_frame_leg_one[['latitude','longitude']].apply(pd.to_numeric)
	data_frame_leg_three = pd.DataFrame({'latitude': [leg_three_list_lat][0], 'longitude': [leg_three_list_long][0]})
	data_frame_leg_three[['latitude','longitude']] = data_frame_leg_three[['latitude','longitude']].apply(pd.to_numeric)


	subset_current = data_frame_current[['latitude','longitude']]
	tuples_current = [tuple(x) for x in subset_current.values]
	subset_leg_one = data_frame_leg_one[['latitude','longitude']]
	tuples_leg_one = [tuple(x) for x in subset_leg_one.values]
	subset_leg_three = data_frame_leg_three[['latitude','longitude']]
	tuples_leg_three = [tuple(x) for x in subset_leg_three.values]
	HS2_Line_Draft = [(52.4816, -1.8863), (51.5290, -0.1347)]

########################################################################################################
##READ HS2 GPX FILE

	gpx_file = open('/home/pi/JBProjectPi/hs2_tracks.gpx')
	gpx = gpxpy.parse(gpx_file)
	tracks = []
	for track in gpx.tracks:
	    
	    track_points = []

	    for segment in track.segments:        
	        for point in segment.points:
	            track_points.append(tuple([point.latitude, point.longitude]))

	    tracks.append(track_points)


########################################################################################################
##PLOT DATA FRAME ON FOLIUM MAP

	coordinates = (51.8, -1.8)
	m = folium.Map(location=coordinates, zoom_start=7, tiles='cartodbpositron')
	folium.PolyLine(tuples_leg_one, color='blue', opacity=1).add_to(m)
	folium.PolyLine(tuples_leg_three, color='blue', opacity=1).add_to(m)
	folium.PolyLine(tuples_current, color='red', opacity=0.6).add_to(m)
	

	folium.Marker(location=[tuples_current[0][0], tuples_current[0][1]]).add_to(m)
	folium.Marker(location=[tuples_current[-1][0], tuples_current[-1][1]]).add_to(m)


	iTrack = 1

	for track in tracks: 

		if iTrack < 20: 
		    folium.PolyLine(track, color='green', opacity=1).add_to(m)
		else:
			folium.PolyLine(track, color='green', opacity=0.2).add_to(m)
			

		iTrack = iTrack + 1

	#folium.PolyLine(HS2_Line_Draft, color='black').add_to(m)
	m.save('./templates/map2.html')

########################################################################################################
##PLOTLY CODING FOR BAR CHART. NOT CURRENTLY WORKING

	tls.set_credentials_file(username='Jonathanabrown', api_key='1rjs7l2upf')

	trace1 = go.Bar(
	    x=['Before HS2', 'After HS2'],
	    y=[current_url_duration, LEG_ONE_duration],
	    name='Leg One'
	)
	trace2 = go.Bar(
	    x=['Before HS2', 'After HS2'],
	    y=[0, 59],
	    name='HS2 Leg'
	)
	trace3 = go.Bar(
	    x=['Before HS2', 'After HS2'],
	    y=[0, url_LEG_THREE_duration],
	    name='Leg Three' 
	)

	data = [trace1, trace2, trace3]
	layout = go.Layout(
	    barmode='stack'
	)

	fig = go.Figure(data=data, layout=layout)
	#py.iplot(fig, filename='stacked-bar')

	return render_template('index.html', a=Markup(result))

########################################################################################################
##RUN FILE

if __name__ == '__main__':
	app.run(host='127.0.0.1',port=9019,debug=True)
