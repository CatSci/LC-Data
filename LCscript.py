import streamlit as st
import pandas as pd
from io import BytesIO

# Streamlit app title
st.title('exportPeaks post-processing')

# File uploader
uploaded_file = st.file_uploader("Choose a file")

# Function to convert DataFrame to Excel file in memory
@st.cache
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True)
        writer.book.close()  # Save the workbook
    return output.getvalue()  # Get the binary content

if uploaded_file is not None:
    # Read the uploaded file
    df = pd.read_csv(uploaded_file, sep='\t')
    # Rounding the 'RT (mins)' column to the nearest hundredth
    df['RT (mins)'] = df['RT (mins)'].round(2)

    # Pivoting the DataFrame
    # Each unique rounded 'RT (mins)' value becomes a column
    pivot_df = df.pivot_table(index='Sample Name', 
                          columns='RT (mins)', 
                          values='Area')

    #Filling NaN values with zero
    pivot_df.fillna(0, inplace=True)

    df=pivot_df
    merged_df = pd.DataFrame(index=df.index)
    columns_to_drop = set()  # Store columns that should be dropped after merging

    # Iterate through each pair of columns and check for merging condition
    for rt1 in df.columns:
        for rt2 in df.columns:
            if rt1 != rt2 and rt1 not in columns_to_drop and rt2 not in columns_to_drop:
                try:
                    # Check the difference between rt1 and rt2 is within the specified range
                    if abs(float(rt1) - float(rt2)) <= 0.02:
                        # Check if at least one value in each row across these columns is 0
                        condition = (df[rt1] == 0.0) | (df[rt2] == 0.0)
                        if condition.any():  # If the condition is true for any row
                            # Sum the columns and use the higher RT value as the column name
                            new_col_name = max(rt1, rt2, key=lambda x: float(x))
                            merged_df[new_col_name] = df[[rt1, rt2]].sum(axis=1)
                            # Mark columns for dropping
                            columns_to_drop.update([rt1, rt2])
                except ValueError:
                    # Handle cases where rt1 or rt2 cannot be converted to float
                    continue

    # Drop the processed columns from df
    df.drop(columns=list(columns_to_drop), axis=1, inplace=True)

    # Add the remaining columns that were not merged to merged_df
    for col in df.columns:
        if col not in merged_df:
            merged_df[col] = df[col]

    # Sort the columns as they might be out of order after merging
    merged_df = merged_df.sort_index(axis=1)

    # Display the final DataFrame in the app
    st.dataframe(merged_df)

    st.download_button(
        label="Download Excel file",
        data=convert_df_to_excel(merged_df),
        file_name="processed_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
