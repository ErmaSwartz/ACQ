import pandas as pd

def mark_matches(joined_data.csv):
    df = pd.read_csv(joined_data.csv)
    # Find duplicates in the 'Email' column
    duplicates = df[df['Email'].duplicated(keep=False)]
    # Create a new column 'Match' and initialize it with 'No Match'
    df['Match'] = 'No Match'
    # Mark rows where the email has a match as 'Match'
    df.loc[duplicates.index, 'Match'] = 'Match'
    return df

# Usage:
result = mark_matches("joined_data.csv")
# Save the result back to CSV
result.to_csv("matched_data.csv", index=False)
print(result)