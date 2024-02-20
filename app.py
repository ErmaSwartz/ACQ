import matplotlib
matplotlib.use('agg')  # Set the backend to 'agg' (non-interactive)

from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import folium
from folium.plugins import HeatMap
import os
from collections import Counter
from flask import jsonify
import numpy as np 
import plotly.express as px
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import geopy
from geopy.exc import GeocoderUnavailable
from geopy.geocoders import Nominatim
import time


# Create a Flask app instance
app = Flask(__name__, template_folder='Templates')

# Define the upload folder for storing uploaded files
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Route for the main page where users can upload files
@app.route('/')
def index():
    # Print the files received through the request (for debugging)
    print(request.files)
    # Render the HTML template for the main page
    return render_template('index.html')

# Route for handling file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    # Initialize an empty list to store the uploaded files
    file_list = []
    # Loop through the files in the request
    for file_name in request.files:
        # Read each CSV file into a DataFrame and append it to the file list
        file_list.append(pd.read_csv(request.files[file_name]))

    # Extract the DataFrames from the file list
    Email_ngp_df = file_list[0]
    activist_code_df = file_list[1]

    # Check if both DataFrames are empty
    if Email_ngp_df.empty and activist_code_df.empty:
        return 'Please select Email data and Activist data'
    # Check if either DataFrame is empty
    if Email_ngp_df.empty:
        return 'Please select Email data'
    if activist_code_df.empty:
        return 'Please select Activist data'

    # Merge the two DataFrames based on a common column 'VANID'
    joined_data = pd.merge(Email_ngp_df, activist_code_df, on="VANID", how="outer")

    # Define the path for saving the joined data as a CSV file
    output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'joined_data.csv')
    # Save the joined data to a CSV file
    joined_data.to_csv(output_file_path, index=False)

    # Check the list of templates for 'results.html'
    template_files = os.listdir(app.template_folder)
    for file_name in template_files:
        if file_name == 'results.html':
            # Render the 'results.html' template with the path of the output file
            return render_template(file_name, output_file=output_file_path)

    # Return an error message if 'results.html' is not found
    return f'Something went wrong- check data'

    # Route for displaying results from the joined data
@app.route('/results', methods=['GET','POST'])
def display_results():
    # Read the processed data from the joined CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'joined_data.csv'))
    # Render the 'results.html' template with the processed data
    return render_template('results.html', processed_data=processed_data)

@app.route('/uploads', methods=['POST'])
def uploads():
    # Read the uploaded file into a DataFrame
    uploaded_file = request.files['file']
    
    # Check if the uploaded file is empty
    if uploaded_file.filename == '':
        return 'Please select a file to upload.'
    
    # Attempt to read the CSV file
    try:
        data = pd.read_csv(uploaded_file)
    except pd.errors.EmptyDataError:
        return 'The uploaded file is empty or has no valid data.'
    
    # Reset the index to default integer-based index
    data.reset_index(drop=True, inplace=True)

    # Check if the DataFrame is empty
    if data.empty:
        return 'Please upload a valid CSV file.'
    
    # Ensure each row has a unique index
    data['unique_index'] = range(1, len(data) + 1)
    data.set_index('unique_index', inplace=True)

    # Drop the unnamed columns
    unnamed_columns = [col for col in data.columns if col.startswith('Unnamed')]
    data.drop(columns=unnamed_columns, inplace=True)
   
    # Process uploaded file and count name occurrences
    name_counts = data['Donor Email'].value_counts()
    
    # Calculate total_donated: sum of 'Amount' for each donor email
    total_donated = data.groupby('Donor Email')['Amount'].sum()

    # Calculate average_donation: mean of 'Amount' for each donor email
    average_donation = data.groupby('Donor Email')['Amount'].mean()

    # Create new columns 'name_counts', 'total_donated', and 'average_donation' in the DataFrame
    data['name_counts'] = data['Donor Email'].map(name_counts)
    data['total_donated'] = data['Donor Email'].map(total_donated)
    data['average_donation'] = data['Donor Email'].map(average_donation)

    # Find Matches between donor emails and emails
    Matches = []
    for email in data['Email']:
        if email in data['Donor Email'].values:
            Matches.append('Match')
        else:
            Matches.append('No Match')
    data['Matches'] = Matches

    
    # Compare 'Date' with 'Date Created' and create a new column for the result
    is_date_after = []
    for index, row in data.iterrows():
        donor_email = row['Donor Email']
        Matching_row = data[data['Email'] == donor_email].iloc[0] if donor_email in data['Email'].values else None
        if Matching_row is not None:
            is_after = row['Date'] > Matching_row['Date Created']  # Compare 'Date' with 'Date Created'
        else:
            is_after = False  # Set to False if no Matching row is found
        is_date_after.append(is_after)
    
    data['is_date_after'] = is_date_after

    # Define the path for saving the processed data as a CSV file
    output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv')
    # Save the processed data to a CSV file
    data.to_csv(output_file_path, index=False)
    return render_template('upload_success.html', output_file=output_file_path)

@app.route('/calculate_top_zip_codes_and_city', methods=['GET'])
def calculate_top_zip_codes_and_city():
    # Read the processed data from the CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    
    # Filter the DataFrame to include only rows where 'Matches' column has value 'Match'
    Matched_data = processed_data[processed_data['Matches'] == 'Match']
    
    # Get the most frequent zip codes from the 'Donor ZIP' column
    top_zip_codes = Matched_data['Donor ZIP'].value_counts().head(10).index.tolist()
    
    # Get the most frequent city from the 'Donor State' column
    most_frequent_city = Matched_data['Donor City'].mode()[0]
    
    return jsonify({'top_zip_codes': top_zip_codes, 'most_frequent_city': most_frequent_city})

# Route to calculate the total Amount donated from Matching donors
@app.route('/total_donated', methods=['GET'])
def calculate_total_donated():
    # Read the processed data from the CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    
    # Filter the DataFrame to include only rows where 'Matches' column has value 'Match'
    Matched_data = processed_data[processed_data['Matches'] == 'Match']
    
    # Calculate the total Amount donated by summing the 'Amount' column
    total_donated = Matched_data['Amount'].sum()
    
    # Return the total donated Amount as a JSON response
    return jsonify({'total_donated': total_donated})

# Route to calculate the median donation Amount from Matching donors
@app.route('/median_donation', methods=['GET'])
def calculate_median_donation():
    # Read the processed data from the CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    
    # Filter the DataFrame to include only rows where 'Matches' column has value 'Match'
    Matched_data = processed_data[processed_data['Matches'] == 'Match']
    
    # Calculate the median donation Amount from the 'Amount' column
    median_donation = Matched_data['Amount'].median()
    
    # Return the median donation Amount as a JSON response
    return jsonify({'median_donation': median_donation})

# Route to calculate the average donation Amount per donor from Matching donors
@app.route('/average_donation', methods=['GET'])
def calculate_average_donation():
    # Read the processed data from the CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    
    # Filter the DataFrame to include only rows where 'Matches' column has value 'Match'
    Matched_data = processed_data[processed_data['Matches'] == 'Match']
    
    # Calculate the average donation Amount per donor from the 'Amount' column
    average_donation = Matched_data['Amount'].mean()
    
    # Return the average donation Amount per donor as a JSON response
    return jsonify({'average_donation': average_donation})

# Route to count the number of unique donors from Matching donors
@app.route('/count_donors', methods=['GET'])
def count_donors():
    # Read the processed data from the CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    
    # Filter the DataFrame to include only rows where 'Matches' column has value 'Match'
    Matched_data = processed_data[processed_data['Matches'] == 'Match']
    
    # Count the number of unique donors from the 'Donor Email' column
    Matched_data_count = Matched_data['Donor Email'].nunique()
    
    # Return the count of unique donors as a JSON response
    return jsonify({'Matched_data_count': Matched_data_count})

# Route to calculate the average times donated
@app.route('/average_times_donated', methods=['GET'])
def calculate_average_times_donated():
    # Read the processed data CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    # Filter the data to include only matches
    Matched_data = processed_data[processed_data['Matches'] == 'Match']
    # Calculate the mean of the number of times each donor has donated
    average_times_donated = Matched_data['Donor Email'].value_counts().mean()
    # Return the result as JSON
    return jsonify({'average_times_donated': average_times_donated})

# Route to calculate the median times donated
@app.route('/median_times_donated', methods=['GET'])
def calculate_median_times_donated():
    # Read the processed data CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    # Filter the data to include only matches
    Matched_data = processed_data[processed_data['Matches'] == 'Match']
    # Calculate the median of the number of times each donor has donated
    median_times_donated = Matched_data['Donor Email'].value_counts().median()
    # Return the result as JSON
    return jsonify({'median_times_donated': median_times_donated})

# Route to count the number of recurring donations
@app.route('/recurring_donations_count', methods=['GET'])
def recurring_donations_count():
    # Read the processed data CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    # Filter the data to include only matches with non-zero recurring total months
    recurring_donors_count = processed_data[(processed_data['Matches'] == 'Match') & 
                                            (processed_data['Recurring Total Months'] != 0)].shape[0]
    # Return the result as JSON
    return jsonify({'recurring_donors_count': recurring_donors_count})

# Route to calculate the amount raised from recurring donations
@app.route('/Amount_raised_recurring', methods=['GET'])
def Amount_raised_recurring():
    # Read the processed data CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    # Filter the data to include only matches with 'is_date_after' as True and non-zero recurring total months
    Amount_raised_recurring = processed_data[(processed_data['Matches'] == 'Match') & 
                                             (processed_data['is_date_after'] == True) & 
                                             (processed_data['Recurring Total Months'] != 0)]['Amount'].sum()
    # Return the result as JSON
    return jsonify({'Amount_raised_recurring': Amount_raised_recurring})

# Route to count the number of donors with ongoing recurring donations
@app.route('/recurring_still_count', methods=['GET'])
def recurring_still_count():
    # Read the processed data CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    # Filter the data to include only matches with 'Recurring Total Months' as 'unlimited'
    recurring_still_count = processed_data[(processed_data['Matches'] == 'Match') & 
                                           (processed_data['Recurring Total Months'] == 'unlimited')].shape[0]
    # Return the result as JSON
    return jsonify({'recurring_still_count': recurring_still_count})

# Function to preprocess the data and calculate the median and average time people sign up for recurring donations
def preprocess_and_calculate_median_average_time():
    # Read the raw data CSV file
    raw_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))

    # Replace 'unlimited' in 'Recurring Total Months' with the value from 'Recurrence Number'
    raw_data.loc[raw_data['Recurring Total Months'] == 'unlimited', 'Recurring Total Months'] = raw_data.loc[raw_data['Recurring Total Months'] == 'unlimited', 'Recurrence Number']

    # Convert the 'Recurring Total Months' column to numeric, ignoring errors
    raw_data['Recurring Total Months'] = pd.to_numeric(raw_data['Recurring Total Months'], errors='coerce')

    # Filter rows where 'Recurring Total Months' is not NaN or empty
    valid_recurring_months = raw_data['Recurring Total Months'].dropna()

    # Calculate median and average
    median_time = valid_recurring_months.median()
    average_time = valid_recurring_months.mean()

    return median_time, average_time

from flask import render_template

app = Flask(__name__)

@app.route('/render_maps')
def render_maps():
    # Load data 
    UPLOAD_FOLDER = 'uploads/'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    
    # Create a map centered at a specific location in Oregon
    donation_map = folium.Map(location=[44.05, -123.09], zoom_start=7)
    # Drop rows with missing ZIP code data
    data.dropna(subset=['Donor ZIP'], inplace=True)
    # Initialize a geocoder
    geolocator = Nominatim(user_agent="my_geocoder")

    # Function to geocode ZIP codes and return latitude and longitude
    def geocode_zip(zip_code):
        location = geolocator.geocode(zip_code)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None

    # Iterate through the DataFrame and add markers for each donor location
    for index, row in data.iterrows():
        # Check if ZIP code is available
        if pd.notnull(row['Donor ZIP']):
            # Use ZIP code to get approximate location
            latitude, longitude = geocode_zip(row['Donor ZIP'])
            if latitude is not None and longitude is not None:
                folium.Marker([latitude, longitude], popup=row['Donor ZIP']).add_to(donation_map)
            else:
                print(f"Geocoding failed for ZIP code: {row['Donor ZIP']}")
    
    # Save the map as an HTML file
    map_path = "static/maps.html"
    donation_map.save(map_path)

    # Render the maps.html template
    return render_template('maps.html')


# Route to preprocess data, calculate median and average time, and return results
@app.route('/calculate_median_average_time', methods=['GET'])
def calculate_median_average_time_route():
    median_time, average_time = preprocess_and_calculate_median_average_time()
    return jsonify({'median_time_sign_up': median_time, 'average_time_sign_up': average_time})

if __name__ == '__main__':
    app.run(debug=True)

