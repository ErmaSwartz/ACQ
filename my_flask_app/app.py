from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os

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
@app.route('/results', methods=['POST'])
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

    # Find matches between donor emails and emails
    matches = []
    for email in data['Email']:
        if email in data['Donor Email'].values:
            matches.append('Match')
        else:
            matches.append('No Match')
    data['Matches'] = matches

    
    # Compare 'Date' with 'Date Created' and create a new column for the result
    is_date_after = []
    for index, row in data.iterrows():
        donor_email = row['Donor Email']
        matching_row = data[data['Email'] == donor_email].iloc[0] if donor_email in data['Email'].values else None
        if matching_row is not None:
            is_after = row['Date'] > matching_row['Date Created']  # Compare 'Date' with 'Date Created'
        else:
            is_after = False  # Set to False if no matching row is found
        is_date_after.append(is_after)
    
    data['is_date_after'] = is_date_after



    # Define the path for saving the processed data as a CSV file
    output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv')
    # Save the processed data to a CSV file
    data.to_csv(output_file_path, index=False)
    return render_template('upload_success.html', output_file=output_file_path)

@app.route('/download_processed_data', methods=['GET'])
def download_processed_data():
    # Get the path of the processed data file
    processed_data_path = request.args.get('processed_data_path')
    # Return the processed data file for download
    return redirect(url_for('static', filename=processed_data_path), code=301)

if __name__ == '__main__':
    app.run(debug=True)

