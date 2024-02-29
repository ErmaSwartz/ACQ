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
import plotly.graph_objs as go
import requests
from datetime import datetime
from collections import defaultdict
from io import BytesIO 
import base64 

# Create a Flask app instance
app = Flask(__name__, template_folder='Templates')

# Define the upload folder for storing uploaded files
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define the coordinates variable globally
coordinates = []

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

    # # Drop the unnamed columns
    # unnamed_columns = [col for col in data.columns if col.startswith('Unnamed')]
    # data.drop(columns=unnamed_columns, inplace=True)
   
    # Process uploaded file and count name occurrences
    name_counts = data.groupby('Donor Email').size()
    
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
    for email in data['Donor Email']:
        if email in data['Email'].values:
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
            is_after = True  # Set to False if no Matching row is found
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

    # Filter the DataFrame to include only rows where 'Matches' column has value 'Match' and 'Amount' column is not NaN
    matched_data = processed_data[(processed_data['Matches'] == 'Match') & (~processed_data['Amount'].isna())]
    
    # Group by 'Donor Email' and 'Amount' and sum the unique amounts for each donor
    grouped_data = matched_data.groupby(['Donor Email', 'Amount']).size().reset_index(name='counts')
    total_donated = grouped_data['Amount'].sum()
    
    print(total_donated)
    
    # Return the total donated Amount as a JSON response
    return jsonify({'total_donated': total_donated})
# Route to calculate the median donation Amount from Matching donors
@app.route('/median_donation', methods=['GET'])
def calculate_median_donation():
    # Read the processed data from the CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    
    # Filter the DataFrame to include only rows where 'Matches' column has value 'Match' and 'Amount' column is not NaN
    Matched_data = processed_data[(processed_data['Matches'] == 'Match') & (~processed_data['Amount'].isna())]
    
    # Calculate the median donation Amount from the 'Amount' column
    median_donation = Matched_data['Amount'].median()
    
    # Return the median donation Amount as a JSON response
    return jsonify({'median_donation': median_donation})

# Route to calculate the average donation Amount per donor from Matching donors
@app.route('/average_donation', methods=['GET'])
def calculate_average_donation():
    # Read the processed data from the CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    
    # Filter the DataFrame to include only rows where 'Matches' column has value 'Match' and 'Amount' column is not NaN
    Matched_data = processed_data[(processed_data['Matches'] == 'Match') & (~processed_data['Amount'].isna())]
    
    # Calculate the average donation Amount per donor from the 'Amount' column
    average_donation = Matched_data['Amount'].mean()
    
    # Return the average donation Amount per donor as a JSON response
    return jsonify({'average_donation': average_donation})

# Route to count the number of unique donors from Matching donors
@app.route('/count_donors', methods=['GET'])
def count_donors():
    # Read the processed data from the CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    
    # Filter the DataFrame to include only rows where 'Matches' column has value 'Match' and 'Donor Email' column is not NaN
    matched_data = processed_data[(processed_data['Matches'] == 'Match') & (~processed_data['Donor Email'].isna())]
    
    # Group by 'Donor Email' and count the number of unique donors
    matched_data_count = matched_data.groupby('Donor Email').size().count()
    
    # Print the count
    print('Number of unique donors:', matched_data_count)
    
    # Return the count of unique donors as a JSON response
    return jsonify({'matched_data_count': matched_data_count})

# Route to calculate the average times donated
@app.route('/average_times_donated', methods=['GET'])
def calculate_average_times_donated():
    # Read the processed data CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    # Filter the data to include only matches and where 'Donor Email' is not NaN
    Matched_data = processed_data[(processed_data['Matches'] == 'Match') & (~processed_data['Donor Email'].isna())]
    # Calculate the mean of the number of times each donor has donated
    average_times_donated = Matched_data['Donor Email'].value_counts().mean()
    # Return the result as JSON
    return jsonify({'average_times_donated': average_times_donated})

# Route to calculate the median times donated
@app.route('/median_times_donated', methods=['GET'])
def calculate_median_times_donated():
    # Read the processed data CSV file
    processed_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    # Filter the data to include only matches and where 'Donor Email' is not NaN
    Matched_data = processed_data[(processed_data['Matches'] == 'Match') & (~processed_data['Donor Email'].isna())]
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
def preprocess():
    # Read the raw data CSV file
    raw_data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    # Convert 'Recurrence Number' to numeric, ignoring errors
    raw_data['Recurrence Number'] = pd.to_numeric(raw_data['Recurrence Number'], errors='coerce')

    # Replace 'unlimited' in 'Recurring Total Months' with the value from 'Recurrence Number'
    raw_data.loc[raw_data['Recurring Total Months'] == 'unlimited', 'Recurring Total Months'] = raw_data.loc[raw_data['Recurring Total Months'] == 'unlimited', 'Recurrence Number']

    # Convert the 'Recurring Total Months' column to numeric, ignoring errors
    raw_data['Recurring Total Months'] = pd.to_numeric(raw_data['Recurring Total Months'], errors='coerce')

    # Filter rows where 'Recurring Total Months' is not NaN or empty
    valid_recurring_months = raw_data['Recurring Total Months'].dropna()

    return valid_recurring_months
@app.route('/calculate_median_average_time', methods=['GET'])
def get_median_average_time():
    # Call the function to preprocess data and calculate median and average time
    valid_recurring_months = preprocess()
    median_time = valid_recurring_months.median()
    average_time = valid_recurring_months.mean()
    print(median_time, average_time)
    # Log median and average times to a file
    app.logger.info(f"Median time: {median_time}, Average time: {average_time}")
    
    # Return the calculated values as JSON response
    return jsonify({'median_time': median_time, 'average_time': average_time})

@app.route('/render_maps')
def render_maps():
    coordinates = []  # Initialize coordinates
    if not coordinates:  
        data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
        for index, row in data.iterrows():
            address = f"{row['Donor City']}, {row['Donor State']} {row['Donor ZIP']}"
            coordinates.append(geocode_address(address))

    # Define state map center and zoom level
    state_map_center = [40.7128, -74.0060]  # Example center coordinates (New York City)
    state_map_zoom = 10  # Example zoom level

    # Prepare data for the country heat map
    country_heatmap_data = []  # You need to define this data based on your requirements

    return render_template('map.html', coordinates=coordinates, state_map={'center': state_map_center, 'zoom': state_map_zoom}, country_heatmap_data=country_heatmap_data)

def geocode_address(address):
    api_key = ""  
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            print(f"Geocoding failed for address: {address}")
            return None
    else:
        print("Failed to retrieve data from the API")
        return None
    

@app.route('/timechart')
def timechart():
    # Read the CSV file
    data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv'))
    # Print out the column names to check for the correct name
    print(data.columns)

    # Convert 'Date' and 'Date Created' columns to datetime with flexible format
    data['Date'] = pd.to_datetime(data['Date'], errors='coerce', infer_datetime_format=True)
    data['Date Created'] = pd.to_datetime(data['Date Created'], errors='coerce', infer_datetime_format=True)

    # Create a dictionary where donor emails are keys and dates are values
    donors = dict(zip(data['Donor Email'], data['Date']))
    print('donor', donors)

    # Create a dictionary where emails are keys and date created are values
    acquisition = dict(zip(data['Email'], data['Date Created']))
    print('acq', acquisition)

    # Create a dictionary to store the earliest date for each email
    earliest_dates = {}

    # Iterate through the donors dictionary
    for email, date in donors.items():
        # If the email is already in the earliest_dates dictionary
        if email in earliest_dates:
            # Check if the current date is earlier than the stored date
            if date < earliest_dates[email]:
                # Update the earliest date for this email
                earliest_dates[email] = date
        else:
            # If the email is not yet in the earliest_dates dictionary, add it
            earliest_dates[email] = date
    print('earliest dates', earliest_dates)

    # Calculate the amount of days between adding and donating
    days_between = []
    for email, donor_date in donors.items():
        if email in acquisition:
            if pd.notna(donor_date) and pd.notna(acquisition[email]):
                # Check if both dates are valid
                days = (donor_date - acquisition[email]).days
                days_between.append(days)
                print(f"Found corresponding acquisition date for email: {email}")
            else:
                print(f"Error: Invalid date for email: {email}")
        else:
            print(f"No corresponding acquisition date found for email: {email}")
    # Filter out negative values
    positive_days_between = [days for days in days_between if days >= 0]

    # Group the filtered list by days
    grouped_data = pd.Series(positive_days_between).value_counts().sort_index()
    # Prepare data for rendering the template
    x_values = grouped_data.index.tolist()
    y_values = grouped_data.values.tolist()
    print(x_values)
    print(y_values)
    print(days_between)

    return render_template('timechart.html', x_values=x_values, y_values=y_values)
if __name__ == '__main__':
    app.run(debug=True)

    #Route to /timechart 
    #Read the csv 
        #data = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], 'sample_data.csv'))
    #filter all the following data for the 'Matches' Column = Match 
    #also filter for the 'is_date_after' column for TRUE 
    #convert the string in 'Date' and 'Date Created' into date time 
        #ensure that the format for intaking the value is flexible and able to process different mm/dd/yy combinations 
        #convert to epoch time 
    #pull donor emails and date --> create a dictionary where donor emails= key date = value [dictionary named Donors]
    #pull emails and date created --> make a dictionary where emails = key and date created = value [dictionary name acquisition]
    #loop through donors and find any keys with duplicate values 
    #take the earliest date from date 
    #drop other values 
    #create a list to hold the values for the amount of days between adding and donating 
    #Grab each key from Donors dictionary and find matching key in Acquisition, where there is no matching key, those keys can be dropped 
    #where there is a matching key, subtract the corresponding value in Donors from the value (date created) in Aquisiton
    #convert epoch time of new element (time between aquisition and donors) back to days 
    #group the new list by days being the same value 
    #create a bar chart where the x axis is days since Acquisition and y is how many donors donated after that many days 
    #render the template to timechart.html 