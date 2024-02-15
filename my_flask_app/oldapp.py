from flask import Flask, render_template, request
import pandas as pd
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    print(request.files)
    if 'file1' not in request.files or 'file2' not in request.files:
        return 'Please select two files'

    file1 = request.files['file1']
    file2 = request.files['file2']
    
    print(file1, file2)

    if file1.filename == '' or file2.filename == '':
        return 'Please select two files'

    # Save the uploaded files to a specific location
    file1_path = os.path.join('uploads', file1.filename)
    file2_path = os.path.join('uploads', file2.filename)
    file1.save(file1_path)
    file2.save(file2_path)
    
    print(f"Saved files to: {file1_path}, {file2_path}")

    # Rest of the code remains the same

    file1 = request.files['file1']
    file2 = request.files['file2']

    if file1.filename == '' or file2.filename == '':
        return 'Please select two files'

    # Save the uploaded files to a specific location
    file1_path = os.path.join('uploads', file1.filename)
    file2_path = os.path.join('uploads', file2.filename)
    file1.save(file1_path)
    file2.save(file2_path)

    # Read the uploaded CSV files into pandas DataFrames
    heck_acq_data = pd.read_csv(file1_path)
    activist_code_data = pd.read_csv(file2_path)

    # Perform the join operation on the common column "VANID"
    joined_data = pd.merge(heck_acq_data, activist_code_data, on="VANID", how="outer")

    # Write the joined data to a new CSV file
    output_file = os.path.join('uploads', 'Heck_joined_ngp_data.csv')
    joined_data.to_csv(output_file, index=False)

    return 'Join operation completed and data written to Heck_joined_ngp_data.csv'

if __name__ == '__main__':
    app.run(debug=True)