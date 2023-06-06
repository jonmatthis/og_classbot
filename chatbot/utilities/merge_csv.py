from pathlib import Path

import pandas as pd

base_folder = Path(r"D:\Dropbox\Northeastern\Courses\neural_control_of_real_world_human_movement\course_data\student_info")

# load the CSV files
df1 = pd.read_csv( base_folder / "student_info_official.csv")
df2 = pd.read_csv( base_folder / "Neural Control of Real-World Human Movement - Intro and prep! (Responses) - Form Responses 1.csv")

# Select only the columns you need
columns_needed_df1 = ['email', 'full_name', 'sortable_name', 'sis_id']
columns_needed_df2 = ['email', 'discord_username', 'github_username']
df1 = df1[columns_needed_df1]
df2 = df2[columns_needed_df2]

# make sure the email column is treated as a string (important for merging)
df1['Email'] = df1['email'].astype(str)
df2['Email'] = df2['email'].astype(str)

# merge the two dataframes on the email column
combined_df = pd.merge(df1, df2, on='email', how='outer')

# save the combined dataframe to a new CSV file
combined_df.to_csv(base_folder/'student_info_combined.csv', index=True)
