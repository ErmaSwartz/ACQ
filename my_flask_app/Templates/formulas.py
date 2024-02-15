import pandas as pd

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

# Usage:
result = mark_matches_and_count_donations("joined_data.csv")
print(result)