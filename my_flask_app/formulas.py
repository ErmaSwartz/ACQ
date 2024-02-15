from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os

# Create the Flask application instance with the specified template folder
app = Flask(__name__, template_folder='Templates')

# Update the UPLOAD_FOLDER path in your Flask application
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    print(request.files)
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file_list = []
    for file_name in request.files:
        file_list.append(pd.read_csv(request.files[file_name]))

    emails_ngp_df = file_list[0]
    activist_code_df = file_list[1]

    if emails_ngp_df.empty and activist_code_df.empty:
        return 'Please select Email data and Activist data'
    if emails_ngp_df.empty:
        return 'Please select Email data'
    if activist_code_df.empty:
        return 'Please select Activist data'

    # Perform the join operation
    joined_data = pd.merge(emails_ngp_df, activist_code_df, on="VANID", how="outer")

    # Save the joined data to a new CSV file
    output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'joined_data.csv')
    joined_data.to_csv(output_file_path, index=False)

    # Execute the provided Python script
    result = mark_matches_and_count_donations(output_file_path)
    print(result)
    
    # Redirect to the next page after executing the script
    return redirect(url_for('next_page'))

# Route for the next page after running the script
@app.route('/next_page')
def next_page():
    return render_template('results.html', output_file=output_file_path)

def mark_matches_and_count_donations(data_file):
    df = pd.read_csv(data_file)
    
    # Find duplicates in the 'Email' column
    duplicates = df[df['Email'].duplicated(keep=False)]
    # Create a new column 'Match' and initialize it with 'No Match'
    df['Match'] = 'No Match'
    # Mark rows where the email has a match as 'Match'
    df.loc[duplicates.index, 'Match'] = 'Match'
    
    # Find rows where there is a match
    matches = df[df['Match'] == 'Match']
    
    # Create a dictionary to store total donation amounts for each 'Donor_Email'
    total_donations = {}
    
    # Iterate through matches
    for index, row in matches.iterrows():
        donor_email = row['Donor_Email']
        donation_amount = row['Amount']
        donation_date = row['Date']
        acquisition_date = row['Date Created']
        
        # Check if donation occurred after acquisition
        if pd.to_datetime(donation_date) > pd.to_datetime(acquisition_date):
            # Add donation_amount to the total for donor_email
            if donor_email in total_donations:
                total_donations[donor_email] += donation_amount
            else:
                total_donations[donor_email] = donation_amount
    
    # Create a new column to store the total donation amounts
    df['Total_Donation'] = df['Donor_Email'].map(total_donations).fillna(0)
    
    # Save the result back to CSV
    df.to_csv(data_file, index=False)
    
    return df

if __name__ == '__main__':
    app.run(debug=True)