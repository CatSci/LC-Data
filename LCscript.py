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
    pivot_df = df.pivot(index='Sample Name', columns='RT (mins)', values='Area')

    #Filling NaN values with zero
    pivot_df.fillna(0, inplace=True)

    merged_df = pd.DataFrame(index=pivot_df.index)
    # Iterate through each pair of columns and check for merging condition
    for rt1 in pivot_df.columns:
        for rt2 in pivot_df.columns:
            if rt1 != rt2 and abs(float(rt1) - float(rt2)) <= 0.2:
                # Check if at least one value in each row across these columns is 0
                condition = (pivot_df[rt1] == 0) | (pivot_df[rt2] == 0)
                if condition.all():  # If the condition is true for all rows
                    # Sum the columns and use the higher RT value as the column name
                    new_col_name = max(rt1, rt2, key=lambda x: float(x))
                    merged_df[new_col_name] = pivot_df[[rt1, rt2]].sum(axis=1)
                    # Once columns are merged, they should not be considered again
                    pivot_df.drop([rt1, rt2], axis=1, inplace=True)
                    break  # Break to avoid re-checking the same columns

# Add the remaining columns that were not merged to the merged_df
    for col in pivot_df.columns:
        if col not in merged_df:
            merged_df[col] = pivot_df[col]

# Sort the columns as they might be out of order after merging
    merged_df = merged_df.sort_index(axis=1)

    merged_df.reset_index(inplace=True)

    # Display the final DataFrame in the app
    st.dataframe(merged_df)

    st.download_button(
        label="Download Excel file",
        data=convert_df_to_excel(merged_df),
        file_name="processed_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
