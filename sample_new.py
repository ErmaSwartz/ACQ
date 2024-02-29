import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Generate random data
np.random.seed(0)
donor_emails = ['donor{}@example.com'.format(i) for i in range(50)]  # Generate 50 unique emails
emails = np.random.choice(donor_emails, size=100)  # Randomly select 100 emails from the 50 unique emails
dates_created = [datetime(2022, 3, 12) for _ in range(100) ]  # Generate random 'Date Created'
dates = [date_created + timedelta(days=np.random.randint(1, 365)) for date_created in dates_created]  # Generate random 'Date'

# Create DataFrame
df = pd.DataFrame({
    'Date': dates,
    'Date Created': dates_created,
    'Donor Email': emails,
    'Email': emails  # Using the same emails for 'Donor Email' and 'Email' columns
})

# Add 'Matches' and 'is_date_after' columns
df['Matches'] = 'Match'
df['is_date_after'] = True

# Shuffle the DataFrame
df = df.sample(frac=1).reset_index(drop=True)

# Save to CSV
df.to_csv('sample_new.csv', index=False)